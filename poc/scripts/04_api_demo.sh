#!/usr/bin/env bash
# Demo 4: FastAPI /health + /analyze (clean and eavesdropper).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "4. FastAPI adaptive security pipeline (/health, /analyze)"

cd "$IMPL_DIR"

# Tear down any leftovers
pkill -f "uvicorn api:app" 2>/dev/null || true
sleep 1

API_PORT=8765
"$UVICORN" api:app --port "$API_PORT" --log-level warning > "$EVIDENCE_DIR/api_server.log" 2>&1 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT

if ! wait_for_http "http://127.0.0.1:$API_PORT/health" 30; then
  cat "$EVIDENCE_DIR/api_server.log"
  fail "FastAPI service failed to start"
fi

curl -sf "http://127.0.0.1:$API_PORT/health" > "$EVIDENCE_DIR/health.json"
loaded=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/health.json'))['models_loaded'])")
echo "  /health models_loaded = $loaded"
[[ "$loaded" == "5/5" ]] || fail "/health did not report 5/5 models loaded (got $loaded)"
ok "Criterion 7 — /health reports 5/5 models loaded"

# Clean analyze
curl -sf -X POST "http://127.0.0.1:$API_PORT/analyze" \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 2048, "error_rate": 0.01, "eavesdrop": false, "backend": "classical"}' \
  > "$EVIDENCE_DIR/analyze_clean.json"

# Eavesdrop analyze
curl -sf -X POST "http://127.0.0.1:$API_PORT/analyze" \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 2048, "error_rate": 0.01, "eavesdrop": true,  "backend": "classical"}' \
  > "$EVIDENCE_DIR/analyze_eavesdrop.json"

verdict_clean=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/analyze_clean.json'))['verdict'])")
verdict_eav=$("$PY"   -c "import json; print(json.load(open('$EVIDENCE_DIR/analyze_eavesdrop.json'))['verdict'])")

echo "  /analyze (clean):       verdict=$verdict_clean"
echo "  /analyze (eavesdropper): verdict=$verdict_eav"

[[ "$verdict_clean" == "SECURE" ]] || fail "/analyze (clean) returned $verdict_clean (expected SECURE)"
[[ "$verdict_eav"   == "ABORT"  ]] || fail "/analyze (eavesdropper) returned $verdict_eav (expected ABORT)"
ok "Criterion 8 — /analyze SECURE on clean, ABORT on eavesdropper"

kill $API_PID 2>/dev/null || true
trap - EXIT
sleep 1

cd - > /dev/null
