#!/usr/bin/env bash
# Set up the venv, install dependencies, train models if needed.
# Idempotent: re-running is cheap if everything is already in place.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "0. Environment setup"

# In Docker the image already has every dep installed system-wide and there is
# no point creating a venv. Skip both the venv and the pip install.
if [[ "${POC_SKIP_VENV:-0}" == "1" ]]; then
  PY="$(command -v python3)"
  PIP="$(command -v pip3 || command -v pip)"
  ok "Skipping venv (POC_SKIP_VENV=1) — using system $PY"
else
  if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
    PY="$VENV_DIR/bin/python"
    PIP="$VENV_DIR/bin/pip"
  fi

  # Always make sure deps match requirements (cheap if already satisfied).
  echo "Installing requirements..."
  "$PIP" install --quiet --upgrade pip
  "$PIP" install --quiet -r "$IMPL_DIR/requirements.txt"
  "$PIP" install --quiet "fastapi>=0.115" "uvicorn>=0.34" "httpx>=0.27" "deap>=1.4" "qiskit>=2.0" "qiskit-aer>=0.17" "flask>=3.0" "requests>=2.31" "cryptography>=41" || true

  ok "Dependencies installed"
fi

step "0b. Train ML models (skipped if pickles exist)"

cd "$IMPL_DIR"
need_train=0
for f in eavesdrop_model.pkl attack_model.pkl param_tuner_model.pkl; do
  if [[ ! -f "data/$f" ]]; then
    need_train=1
    break
  fi
done

if (( need_train == 1 )); then
  echo "Training models — one-time cost..."
  "$PY" train_all_models.py
  ok "Models trained"
else
  ok "Models already present in data/"
fi

cd - > /dev/null
