"""
Dual-KME ETSI GS QKD 014 Key Management Entity

Extends kme_server.py for a realistic two-KME deployment where Alice and
Bob each run their own KME instance. Key material is generated on the
master KME and pushed to the peer KME via an internal sync endpoint,
mirroring the architecture of real QKD deployments (Toshiba, IDQ Cerberis).

Deployment:
  python kme_dual.py --role alice   # port 5001, peers with port 5002
  python kme_dual.py --role bob     # port 5002, peers with port 5001

Flow:
  1. Alice's app  → GET /enc_keys   on kme-alice (5001)
                    KME-Alice generates key via BB84, stores locally,
                    AND pushes (key_ID, key_bytes) to kme-bob/peer/sync_keys
  2. Bob's app    → POST /dec_keys  on kme-bob (5002) with key_ID
                    KME-Bob finds the pre-synced key and returns it

  Both KMEs support all ETSI endpoints. Either side can be master or slave.
  Peer sync is best-effort: if the peer is offline, the local operation
  still succeeds (graceful degradation to single-KME mode).

Endpoints (ETSI GS QKD 014 §5):
  GET  /api/v1/keys/{slave_SAE_ID}/status
  GET  /api/v1/keys/{slave_SAE_ID}/enc_keys?number=N&size=S
  POST /api/v1/keys/{slave_SAE_ID}/enc_keys
  POST /api/v1/keys/{slave_SAE_ID}/dec_keys

Internal sync endpoint:
  POST /peer/sync_keys   (called by peer KME only)
"""

import argparse
import base64
import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass

import requests
from flask import Flask, abort, jsonify, request

from bb84_simulator import BB84Protocol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Role configuration ─────────────────────────────────────────────────────────
# parse_known_args() so pytest can import this module without consuming pytest's
# own CLI flags.

_parser = argparse.ArgumentParser(add_help=False)
_parser.add_argument("--role", choices=["alice", "bob"], default="alice")
_args, _ = _parser.parse_known_args()

if _args.role == "alice":
    KME_ID       = "kme-alice"
    PARTNER_KME_ID = "kme-bob"
    PORT         = 5001
    PEER_KME_URL: str | None = "http://127.0.0.1:5002"
else:
    KME_ID       = "kme-bob"
    PARTNER_KME_ID = "kme-alice"
    PORT         = 5002
    PEER_KME_URL = "http://127.0.0.1:5001"

# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_KEY_SIZE     = 256
MIN_KEY_SIZE         = 64
MAX_KEY_SIZE         = 1024
MAX_KEYS_PER_REQUEST = 20
POOL_TARGET          = 50
POOL_REFILL_TRIGGER  = 10
SYNC_TIMEOUT_S       = 2   # peer sync HTTP timeout

# ── Key storage ────────────────────────────────────────────────────────────────

@dataclass
class StoredKey:
    key_id:    str
    key_bytes: bytes
    size_bits: int


# ── DualKeyPool ────────────────────────────────────────────────────────────────

class DualKeyPool:
    """
    Thread-safe key pool that syncs issued keys to the peer KME.

    After enc_keys moves keys from _available to _pending, a background
    daemon thread pushes those same keys to PEER_KME_URL/peer/sync_keys
    so the peer's slave SAE can retrieve them by key_ID via dec_keys.

    If PEER_KME_URL is None, sync is skipped (test / standalone mode).
    """

    def __init__(self, peer_url: str | None = PEER_KME_URL) -> None:
        self._available: dict[str, StoredKey] = {}
        self._available_order: deque[str] = deque()
        self._pending: dict[str, StoredKey] = {}
        self._lock = threading.Lock()
        self._proto = BB84Protocol(error_rate=0.01)
        self._peer_url = peer_url

        log.info("Initialising key pool for %s (target: %d keys)...", KME_ID, POOL_TARGET)
        self._fill_to_target()
        log.info("Key pool ready: %d keys available", len(self._available))

    # ── Key generation ─────────────────────────────────────────────────────────

    def _generate(self, size_bits: int = DEFAULT_KEY_SIZE) -> StoredKey:
        n_raw  = max(4096, size_bits * 25)
        result = self._proto.run(n_bits=n_raw)
        if not result.secure:
            raise RuntimeError("BB84 failed — QBER exceeded threshold")

        import hashlib
        needed = size_bits // 8
        key    = result.final_key
        while len(key) < needed:
            key += hashlib.blake2b(key, digest_size=32).digest()
        key = key[:needed]

        return StoredKey(key_id=str(uuid.uuid4()), key_bytes=key, size_bits=size_bits)

    def _fill_to_target(self) -> None:
        while len(self._available) < POOL_TARGET:
            k = self._generate()
            self._available[k.key_id] = k
            self._available_order.append(k.key_id)

    def _maybe_refill(self) -> None:
        if len(self._available) < POOL_REFILL_TRIGGER:
            threading.Thread(target=self._fill_to_target, daemon=True).start()

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_keys(self, count: int, size_bits: int = DEFAULT_KEY_SIZE) -> list[StoredKey]:
        """Issue keys to the master SAE and sync them to the peer KME."""
        with self._lock:
            matching_ids = [
                kid for kid in self._available_order
                if self._available[kid].size_bits == size_bits
            ]
            while len(matching_ids) < count:
                k = self._generate(size_bits)
                self._available[k.key_id] = k
                self._available_order.append(k.key_id)
                matching_ids.append(k.key_id)

            selected_ids = matching_ids[:count]
            keys: list[StoredKey] = []
            for kid in selected_ids:
                k = self._available.pop(kid)
                self._available_order.remove(kid)
                self._pending[kid] = k
                keys.append(k)

        self._maybe_refill()

        # Push to peer KME in a background thread (best-effort)
        if self._peer_url:
            threading.Thread(
                target=self._sync_to_peer,
                args=(list(keys),),
                daemon=True,
            ).start()

        return keys

    def get_by_ids(self, key_ids: list[str]) -> list[StoredKey]:
        """Retrieve pre-synced keys by key_ID for the slave SAE."""
        with self._lock:
            found: list[StoredKey] = []
            for kid in key_ids:
                if kid in self._pending:
                    found.append(self._pending.pop(kid))
        return found

    def inject_synced_keys(self, keys_data: list[dict]) -> int:
        """
        Accept key material pushed by the peer KME via /peer/sync_keys.
        Stores keys in _pending so dec_keys can retrieve them by key_ID.
        """
        count = 0
        with self._lock:
            for item in keys_data:
                kid    = item["key_ID"]
                kbytes = base64.b64decode(item["key"])
                self._pending[kid] = StoredKey(
                    key_id=kid,
                    key_bytes=kbytes,
                    size_bits=len(kbytes) * 8,
                )
                count += 1
        return count

    @property
    def available_count(self) -> int:
        return len(self._available)

    # ── Peer sync ──────────────────────────────────────────────────────────────

    def _sync_to_peer(self, keys: list[StoredKey]) -> None:
        """POST key material to the peer KME. Called in a background thread."""
        payload = {
            "keys": [
                {"key_ID": k.key_id, "key": base64.b64encode(k.key_bytes).decode()}
                for k in keys
            ]
        }
        try:
            resp = requests.post(
                f"{self._peer_url}/peer/sync_keys",
                json=payload,
                timeout=SYNC_TIMEOUT_S,
            )
            resp.raise_for_status()
            log.info("Synced %d key(s) to peer KME at %s", len(keys), self._peer_url)
        except Exception as exc:
            log.warning("Peer sync failed (non-fatal): %s", exc)


# ── Flask app ──────────────────────────────────────────────────────────────────

app  = Flask(__name__)
pool = DualKeyPool()


def _key_to_dict(k: StoredKey) -> dict:
    return {"key_ID": k.key_id, "key": base64.b64encode(k.key_bytes).decode()}


def _int_param(name: str, default: int, lo: int, hi: int) -> int:
    raw = request.args.get(name, str(default))
    try:
        val = int(raw)
    except ValueError:
        abort(400, description=f"'{name}' must be an integer")
    if not lo <= val <= hi:
        abort(400, description=f"'{name}' must be between {lo} and {hi}")
    return val


# ── ETSI QKD 014 routes ────────────────────────────────────────────────────────

@app.get("/api/v1/keys/<slave_sae_id>/status")
def route_status(slave_sae_id: str):
    return jsonify({
        "source_KME_ID":      KME_ID,
        "target_KME_ID":      PARTNER_KME_ID,
        "master_SAE_ID":      "sae-master",
        "slave_SAE_ID":       slave_sae_id,
        "key_size":           DEFAULT_KEY_SIZE,
        "stored_key_count":   pool.available_count,
        "max_key_count":      POOL_TARGET,
        "max_key_per_request": MAX_KEYS_PER_REQUEST,
        "max_key_size":       MAX_KEY_SIZE,
        "min_key_size":       MIN_KEY_SIZE,
        "max_SAE_ID_count":   0,
        "peer_kme_url":       PEER_KME_URL,
    })


@app.get("/api/v1/keys/<slave_sae_id>/enc_keys")
def route_enc_keys_get(slave_sae_id: str):
    number = _int_param("number", 1, 1, MAX_KEYS_PER_REQUEST)
    size   = _int_param("size", DEFAULT_KEY_SIZE, MIN_KEY_SIZE, MAX_KEY_SIZE)
    if size % 8 != 0:
        abort(400, description="Key size must be a multiple of 8 bits")
    keys = pool.get_keys(number, size)
    log.info("enc_keys  slave=%s  n=%d  size=%d  (will sync to peer)", slave_sae_id, len(keys), size)
    return jsonify({"keys": [_key_to_dict(k) for k in keys]})


@app.post("/api/v1/keys/<slave_sae_id>/enc_keys")
def route_enc_keys_post(slave_sae_id: str):
    body   = request.get_json(silent=True) or {}
    number = min(int(body.get("number", 1)), MAX_KEYS_PER_REQUEST)
    size   = int(body.get("size", DEFAULT_KEY_SIZE))
    if size % 8 != 0:
        abort(400, description="Key size must be a multiple of 8 bits")
    keys = pool.get_keys(number, size)
    log.info("enc_keys POST  slave=%s  n=%d  size=%d", slave_sae_id, len(keys), size)
    return jsonify({"keys": [_key_to_dict(k) for k in keys]})


@app.post("/api/v1/keys/<slave_sae_id>/dec_keys")
def route_dec_keys(slave_sae_id: str):
    body    = request.get_json(silent=True) or {}
    raw_ids = body.get("key_IDs", [])
    if not raw_ids:
        abort(400, description="Request body must include 'key_IDs'")
    if len(raw_ids) > MAX_KEYS_PER_REQUEST:
        abort(400, description=f"Too many key IDs (max {MAX_KEYS_PER_REQUEST})")

    key_ids = [
        item.get("key_ID")
        for item in raw_ids
        if isinstance(item, dict) and "key_ID" in item
    ]
    keys = pool.get_by_ids(key_ids)
    if not keys:
        abort(404, description="No matching keys found — key may not exist or already retrieved")
    log.info("dec_keys  slave=%s  requested=%d  found=%d", slave_sae_id, len(key_ids), len(keys))
    return jsonify({"keys": [_key_to_dict(k) for k in keys]})


# ── Peer sync route ────────────────────────────────────────────────────────────

@app.post("/peer/sync_keys")
def route_peer_sync():
    """
    Internal endpoint — called by the peer KME to push synchronized key material.

    Accepts the same key format as enc_keys responses so the payload can be
    logged and inspected consistently.
    """
    body      = request.get_json(silent=True) or {}
    keys_data = body.get("keys", [])
    if not keys_data:
        abort(400, description="Request body must include 'keys'")

    count = pool.inject_synced_keys(keys_data)
    log.info("peer/sync_keys  injected=%d keys into pending pool", count)
    return jsonify({"synced": count}), 200


# ── Error handlers ─────────────────────────────────────────────────────────────

@app.errorhandler(400)
@app.errorhandler(404)
def handle_error(e):
    return jsonify({"message": str(e.description)}), e.code


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Dual-KME Server — role: {_args.role}")
    print("=" * 55)
    print(f"  KME ID   : {KME_ID}")
    print(f"  Port     : {PORT}")
    print(f"  Peer KME : {PEER_KME_URL}")
    print(f"  API      : http://127.0.0.1:{PORT}/api/v1/keys/")
    print()
    print("  Example (run peer first, then this):")
    print(f"    curl http://127.0.0.1:{PORT}/api/v1/keys/sae-test/status")
    print(f"    curl http://127.0.0.1:{PORT}/api/v1/keys/sae-test/enc_keys")
    print()
    app.run(host="127.0.0.1", port=PORT, debug=False)
