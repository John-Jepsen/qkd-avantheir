#!/usr/bin/env bash
# Container entrypoint. Routes the first arg to the right command.
#
#   mvp         — Run the full MVP demo (poc/scripts/run_mvp.sh).
#   api         — Start FastAPI on $API_PORT (default 8765).
#   kme         — Start the ETSI KME server on $KME_PORT (default 5000).
#   psk-server  — Start tls_psk_demo.py server (Bob).
#   psk-client  — Run tls_psk_demo.py client (Alice). Requires KME reachable.
#   bash        — Drop into an interactive shell.
#
# Anything else is passed through to the shell unchanged.

set -euo pipefail

cmd="${1:-mvp}"
shift || true

API_PORT="${API_PORT:-8765}"
KME_PORT="${KME_PORT:-5000}"
KME_URL="${KME_URL:-http://127.0.0.1:5000}"

cd /app/implementation

case "$cmd" in
  mvp)
    exec /app/poc/scripts/run_mvp.sh
    ;;
  api)
    exec uvicorn api:app --host 0.0.0.0 --port "$API_PORT" "$@"
    ;;
  kme)
    # Bind to all interfaces so other containers / hosts can reach it.
    exec python kme_server.py --host 0.0.0.0 --port "$KME_PORT" "$@"
    ;;
  psk-server)
    exec python tls_psk_demo.py server "$@"
    ;;
  psk-client)
    # tls_psk_demo.py reads KME_URL as a module constant — override it before
    # calling run_client() so it can talk to a KME at the compose-network host.
    exec python -c "
import tls_psk_demo
tls_psk_demo.KME_URL = '${KME_URL}'
tls_psk_demo.run_client()
"
    ;;
  bash|sh)
    exec bash "$@"
    ;;
  *)
    # Unknown command — exec it directly so users can do
    # `docker run qkd-poc python -c "..."` etc.
    exec "$cmd" "$@"
    ;;
esac
