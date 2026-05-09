#!/usr/bin/env bash
# Shared environment for all POC demo scripts.
# Sourced by every other script in this folder.

set -euo pipefail

# Resolve repo root relative to this file (regardless of cwd).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$POC_DIR")"
IMPL_DIR="$REPO_ROOT/implementation"
EVIDENCE_DIR="$POC_DIR/evidence"
VENV_DIR="$IMPL_DIR/.venv"

mkdir -p "$EVIDENCE_DIR"

# Picks python3 from venv if present, otherwise from PATH.
if [[ -x "$VENV_DIR/bin/python" ]] && [[ "${POC_SKIP_VENV:-0}" != "1" ]]; then
  PY="$VENV_DIR/bin/python"
  PIP="$VENV_DIR/bin/pip"
  UVICORN="$VENV_DIR/bin/uvicorn"
else
  PY="$(command -v python3 || true)"
  PIP="$(command -v pip3 || true)"
  UVICORN="$(command -v uvicorn || true)"
fi

# Pretty colors (skip if not a tty)
if [[ -t 1 ]]; then
  C_OK="$(printf '\033[32m')"
  C_FAIL="$(printf '\033[31m')"
  C_HEAD="$(printf '\033[1;36m')"
  C_OFF="$(printf '\033[0m')"
else
  C_OK=""; C_FAIL=""; C_HEAD=""; C_OFF=""
fi

step()  { printf "\n%s== %s ==%s\n" "$C_HEAD" "$*" "$C_OFF"; }
ok()    { printf "%sPASS%s  %s\n" "$C_OK" "$C_OFF" "$*"; }
fail()  { printf "%sFAIL%s  %s\n" "$C_FAIL" "$C_OFF" "$*"; exit 1; }

# Wait until a URL returns HTTP 2xx, or fail after `tries` attempts (1s each).
wait_for_http() {
  local url="$1" tries="${2:-30}"
  local i=0
  while (( i < tries )); do
    if curl -sf -o /dev/null "$url"; then return 0; fi
    sleep 1
    i=$((i+1))
  done
  return 1
}
