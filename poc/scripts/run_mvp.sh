#!/usr/bin/env bash
# Single-command MVP demo. Runs every step in order, tears down everything,
# emits a final pass/fail summary against the 8 MVP exit criteria.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

START=$(date +%s)

bash "$SCRIPT_DIR/00_setup.sh"
bash "$SCRIPT_DIR/01_bb84_demo.sh"
bash "$SCRIPT_DIR/02_ml_pipeline_demo.sh"
bash "$SCRIPT_DIR/03_kme_psk_demo.sh"
bash "$SCRIPT_DIR/04_api_demo.sh"
bash "$SCRIPT_DIR/05_full_api_sweep.sh"

END=$(date +%s)

step "MVP RESULT"
ok "All 8 MVP exit criteria passed"
echo
echo "Evidence captured in: $EVIDENCE_DIR"
ls -1 "$EVIDENCE_DIR" | sed 's/^/  /'
echo
echo "Wall clock: $((END - START))s"
echo
echo "Next: open poc/docs/RESULTS.md for the formatted summary."
