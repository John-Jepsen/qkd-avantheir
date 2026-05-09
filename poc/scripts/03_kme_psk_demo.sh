#!/usr/bin/env bash
# Demo 3: Stand up the KME, fetch a key with the same key_ID from both
# Alice and Bob, run the AES-256-GCM PSK exchange.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "3. KME (ETSI GS QKD 014) + TLS PSK end-to-end"

cd "$IMPL_DIR"

# Tear down any leftovers from a previous run.
pkill -f "kme_server.py" 2>/dev/null || true
pkill -f "tls_psk_demo.py server" 2>/dev/null || true
sleep 1

# Start KME (port 5000 by convention)
"$PY" kme_server.py > "$EVIDENCE_DIR/kme_server.log" 2>&1 &
KME_PID=$!
trap 'kill $KME_PID 2>/dev/null || true; pkill -f "tls_psk_demo.py server" 2>/dev/null || true' EXIT

# KME pre-fills 50 keys via BB84 — and on import the pool initializes once,
# then again when the CLI re-creates it. ~30s on classical backend.
if ! wait_for_http "http://127.0.0.1:5000/api/v1/keys/sae-bob/status" 90; then
  cat "$EVIDENCE_DIR/kme_server.log"
  fail "KME server failed to start"
fi

curl -sf "http://127.0.0.1:5000/api/v1/keys/sae-bob/status" > "$EVIDENCE_DIR/kme_status.json"
echo "  KME status:"
cat "$EVIDENCE_DIR/kme_status.json" | "$PY" -m json.tool | sed 's/^/    /'

# Manual key-ID round-trip first: confirms /enc_keys and /dec_keys produce the
# same bytes for the same ID.
"$PY" - <<'PY' > "$EVIDENCE_DIR/kme_round_trip.json"
import json, requests
base = "http://127.0.0.1:5000/api/v1/keys/sae-bob"
enc = requests.get(f"{base}/enc_keys").json()
key_id = enc["keys"][0]["key_ID"]
key_alice = enc["keys"][0]["key"]
dec = requests.post(f"{base}/dec_keys", json={"key_IDs": [{"key_ID": key_id}]}).json()
key_bob = dec["keys"][0]["key"]
print(json.dumps({
    "key_ID": key_id,
    "alice_key_b64_prefix": key_alice[:24] + "...",
    "bob_key_b64_prefix":   key_bob[:24]   + "...",
    "match": key_alice == key_bob,
}, indent=2))
PY

match=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/kme_round_trip.json'))['match'])")
[[ "$match" == "True" ]] || fail "KME enc_keys/dec_keys did not return matching keys for the same key_ID"
ok "Criterion 5 — KME enc_keys/dec_keys round-trip matches"

# Run the actual PSK demo: Bob server in background, Alice client in foreground.
"$PY" tls_psk_demo.py server > "$EVIDENCE_DIR/psk_server.log" 2>&1 &
SERVER_PID=$!
sleep 2

if "$PY" tls_psk_demo.py client > "$EVIDENCE_DIR/psk_demo.log" 2>&1; then
  echo "  PSK demo output:"
  sed 's/^/    /' < "$EVIDENCE_DIR/psk_demo.log"
  if grep -q "ACK from Bob" "$EVIDENCE_DIR/psk_demo.log"; then
    ok "Criterion 6 — Alice and Bob exchanged AES-256-GCM payload using only KME-derived keys"
  else
    fail "PSK demo did not produce expected ACK"
  fi
else
  cat "$EVIDENCE_DIR/psk_demo.log"
  fail "tls_psk_demo client failed"
fi

# Cleanup — handled by trap, but be explicit.
kill $SERVER_PID 2>/dev/null || true
kill $KME_PID 2>/dev/null || true
trap - EXIT
sleep 1

cd - > /dev/null
