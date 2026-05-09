#!/usr/bin/env bash
# Demo 1: Run BB84 clean and with eavesdropper, capture both results.

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "1. BB84 protocol — clean vs eavesdropper"

cd "$IMPL_DIR"

"$PY" - <<'PY' > "$EVIDENCE_DIR/bb84_clean.json"
import json
from bb84_simulator import BB84Protocol
r = BB84Protocol(backend="classical").run(n_bits=4096)
print(json.dumps({
    "raw_bits": r.raw_bits,
    "sifted_bits": r.sifted_bits,
    "qber": round(r.qber, 4),
    "secure": r.secure,
    "eavesdropper_detected": r.eavesdropper_detected,
    "key_length_bits": r.key_length_bits,
    "final_key_hex_prefix": (r.final_key.hex()[:32] + "...") if r.final_key else None,
    "backend_used": r.backend_used,
}, indent=2))
PY

"$PY" - <<'PY' > "$EVIDENCE_DIR/bb84_eavesdrop.json"
import json
from bb84_simulator import BB84Protocol
r = BB84Protocol(backend="classical", eavesdrop=True).run(n_bits=4096)
print(json.dumps({
    "raw_bits": r.raw_bits,
    "sifted_bits": r.sifted_bits,
    "qber": round(r.qber, 4),
    "secure": r.secure,
    "eavesdropper_detected": r.eavesdropper_detected,
    "key_length_bits": r.key_length_bits,
    "final_key_hex_prefix": (r.final_key.hex()[:32] + "...") if r.final_key else None,
    "backend_used": r.backend_used,
}, indent=2))
PY

# Assertions against MVP exit criteria
qber_clean=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/bb84_clean.json'))['qber'])")
secure_clean=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/bb84_clean.json'))['secure'])")
qber_eav=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/bb84_eavesdrop.json'))['qber'])")
secure_eav=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/bb84_eavesdrop.json'))['secure'])")

echo "  clean: QBER=$qber_clean secure=$secure_clean"
echo "  eav:   QBER=$qber_eav   secure=$secure_eav"

[[ "$secure_clean" == "True" ]] || fail "Clean BB84 run was not marked secure"
[[ "$secure_eav"   == "False" ]] || fail "Eavesdropper BB84 run was not marked aborted"
ok "Criterion 1 — BB84 clean returns secure=true"
ok "Criterion 2 — BB84 with eavesdropper returns secure=false"

cd - > /dev/null
