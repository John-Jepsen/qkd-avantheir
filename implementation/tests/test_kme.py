"""
Tests for the ETSI GS QKD 014 KME endpoints (kme_server and kme_dual).

Covers: status, enc_keys (GET + POST), dec_keys, error cases,
and dual-KME peer sync injection.
"""

import base64
import pytest


# ── kme_server (single KME) ────────────────────────────────────────────────────

class TestKMEStatus:
    def test_status_200(self, kme_client):
        resp = kme_client.get("/api/v1/keys/sae-test/status")
        assert resp.status_code == 200

    def test_status_fields(self, kme_client):
        data = kme_client.get("/api/v1/keys/sae-test/status").get_json()
        for field in ("source_KME_ID", "stored_key_count", "key_size",
                      "max_key_per_request", "max_key_size", "min_key_size"):
            assert field in data, f"Missing field: {field}"

    def test_stored_key_count_positive(self, kme_client):
        data = kme_client.get("/api/v1/keys/sae-test/status").get_json()
        assert data["stored_key_count"] >= 0


class TestEncKeys:
    def test_enc_keys_get_default(self, kme_client):
        resp = kme_client.get("/api/v1/keys/sae-test/enc_keys")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "keys" in data
        assert len(data["keys"]) == 1

    def test_enc_keys_response_shape(self, kme_client):
        data = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
        key  = data["keys"][0]
        assert "key_ID" in key
        assert "key" in key
        # key is base64-encoded 256-bit value → 32 bytes → 44-char base64
        assert len(base64.b64decode(key["key"])) == 32

    def test_enc_keys_get_multiple(self, kme_client):
        resp = kme_client.get("/api/v1/keys/sae-test/enc_keys?number=3")
        data = resp.get_json()
        assert len(data["keys"]) == 3

    def test_enc_keys_get_custom_size(self, kme_client):
        resp = kme_client.get("/api/v1/keys/sae-test/enc_keys?size=128")
        assert resp.status_code == 200
        key = resp.get_json()["keys"][0]
        assert len(base64.b64decode(key["key"])) == 16   # 128 bits = 16 bytes

    def test_enc_keys_bad_size_not_multiple_of_8(self, kme_client):
        resp = kme_client.get("/api/v1/keys/sae-test/enc_keys?size=100")
        assert resp.status_code == 400

    def test_enc_keys_post(self, kme_client):
        resp = kme_client.post(
            "/api/v1/keys/sae-test/enc_keys",
            json={"number": 2, "size": 256},
        )
        assert resp.status_code == 200
        assert len(resp.get_json()["keys"]) == 2

    def test_enc_keys_unique_ids(self, kme_client):
        d1 = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
        d2 = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
        id1 = d1["keys"][0]["key_ID"]
        id2 = d2["keys"][0]["key_ID"]
        assert id1 != id2


class TestDecKeys:
    def test_dec_keys_retrieves_issued_key(self, kme_client):
        enc  = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
        kid  = enc["keys"][0]["key_ID"]
        orig = enc["keys"][0]["key"]

        resp = kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": kid}]},
        )
        assert resp.status_code == 200
        retrieved = resp.get_json()["keys"][0]["key"]
        assert retrieved == orig

    def test_dec_keys_unknown_id_returns_404(self, kme_client):
        resp = kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": "nonexistent-uuid"}]},
        )
        assert resp.status_code == 404

    def test_dec_keys_missing_body_returns_400(self, kme_client):
        resp = kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={},
        )
        assert resp.status_code == 400

    def test_dec_keys_key_consumed_after_retrieval(self, kme_client):
        """A key retrieved via dec_keys cannot be retrieved a second time."""
        enc = kme_client.get("/api/v1/keys/sae-test/enc_keys").get_json()
        kid = enc["keys"][0]["key_ID"]

        kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": kid}]},
        )
        # Second retrieval of the same key_ID must fail
        resp2 = kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": kid}]},
        )
        assert resp2.status_code == 404


# ── kme_dual (dual-KME with peer sync) ────────────────────────────────────────

class TestDualKMEStatus:
    def test_status_includes_peer_url(self, dual_kme_client):
        data = dual_kme_client.get("/api/v1/keys/sae-test/status").get_json()
        assert "peer_kme_url" in data


class TestPeerSync:
    def test_peer_sync_injects_key(self, dual_kme_client):
        """Simulate the peer KME pushing a key; verify dec_keys retrieves it."""
        import uuid, os

        kid    = str(uuid.uuid4())
        key_b  = os.urandom(32)
        key_b64 = base64.b64encode(key_b).decode()

        sync_resp = dual_kme_client.post(
            "/peer/sync_keys",
            json={"keys": [{"key_ID": kid, "key": key_b64}]},
        )
        assert sync_resp.status_code == 200
        assert sync_resp.get_json()["synced"] == 1

        dec_resp = dual_kme_client.post(
            "/api/v1/keys/sae-test/dec_keys",
            json={"key_IDs": [{"key_ID": kid}]},
        )
        assert dec_resp.status_code == 200
        retrieved = base64.b64decode(dec_resp.get_json()["keys"][0]["key"])
        assert retrieved == key_b

    def test_peer_sync_empty_keys_returns_400(self, dual_kme_client):
        resp = dual_kme_client.post("/peer/sync_keys", json={})
        assert resp.status_code == 400
