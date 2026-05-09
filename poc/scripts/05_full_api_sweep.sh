#!/usr/bin/env bash
# Optional: hit the rest of the API surface (forecast, recommend, anomaly).
# Not part of the MVP exit criteria — exists to show the other 3 ML models
# are wired up and respond.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "5. Full API surface sweep (optional, not MVP-blocking)"

cd "$IMPL_DIR"

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

# Forecast (ARIMA noise predictor)
curl -sf -X POST "http://127.0.0.1:$API_PORT/forecast" \
  -H "Content-Type: application/json" -d '{"steps": 10}' \
  > "$EVIDENCE_DIR/forecast.json" || true

# Parameter recommendation (GB regressor)
curl -sf -X POST "http://127.0.0.1:$API_PORT/recommend" \
  -H "Content-Type: application/json" -d '{"observed_noise": 0.03}' \
  > "$EVIDENCE_DIR/recommend.json" || true

# KME anomaly detection (Isolation Forest) — burst attack pattern
curl -sf -X POST "http://127.0.0.1:$API_PORT/detect-anomaly" \
  -H "Content-Type: application/json" \
  -d '{"request_rate_1min": 45.0, "mean_keys_requested": 15.0,
       "mean_key_size": 1024, "inter_request_std": 1.2,
       "enc_dec_ratio": 10.0, "unique_sae_count": 1,
       "max_burst_rate": 20, "failed_ratio": 0.0}' \
  > "$EVIDENCE_DIR/anomaly.json" || true

# Loaded models metadata
curl -sf "http://127.0.0.1:$API_PORT/models" > "$EVIDENCE_DIR/models.json" || true

for f in forecast.json recommend.json anomaly.json models.json; do
  if [[ -s "$EVIDENCE_DIR/$f" ]]; then
    ok "$f captured"
  else
    fail "$f was empty (endpoint failed)"
  fi
done

kill $API_PID 2>/dev/null || true
trap - EXIT
sleep 1

cd - > /dev/null
