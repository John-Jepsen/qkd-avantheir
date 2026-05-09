#!/usr/bin/env bash
# Demo 2: Run the eavesdrop classifier and attack classifier directly
# against fresh BB84 output (no API in the loop).

source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"

step "2. ML pipeline — eavesdrop classifier + attack classifier"

cd "$IMPL_DIR"

"$PY" - <<'PY' > "$EVIDENCE_DIR/ml_pipeline.json"
import json
import joblib
import numpy as np
from bb84_simulator import BB84Protocol
from features import extract_features

clean = BB84Protocol(backend="classical").run(n_bits=4096)
eaved = BB84Protocol(backend="classical", eavesdrop=True).run(n_bits=4096)

eav_clf = joblib.load("data/eavesdrop_model.pkl")
atk_clf = joblib.load("data/attack_model.pkl")

def predict(model, result):
    feats = np.array([extract_features(result)])
    label = model.predict(feats)[0]
    proba = model.predict_proba(feats)[0]
    classes = list(model.classes_)
    return {
        "label": label,
        "confidence": round(float(max(proba)), 4),
        "probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
    }

out = {
    "clean_run": {
        "qber": round(clean.qber, 4),
        "eavesdrop_classifier": predict(eav_clf, clean),
        "attack_classifier": predict(atk_clf, clean),
    },
    "eavesdropper_run": {
        "qber": round(eaved.qber, 4),
        "eavesdrop_classifier": predict(eav_clf, eaved),
        "attack_classifier": predict(atk_clf, eaved),
    },
}
print(json.dumps(out, indent=2))
PY

clean_eav=$("$PY" -c "import json; print(json.load(open('$EVIDENCE_DIR/ml_pipeline.json'))['clean_run']['eavesdrop_classifier']['label'])")
eav_eav=$("$PY"  -c "import json; print(json.load(open('$EVIDENCE_DIR/ml_pipeline.json'))['eavesdropper_run']['eavesdrop_classifier']['label'])")
eav_atk=$("$PY"  -c "import json; print(json.load(open('$EVIDENCE_DIR/ml_pipeline.json'))['eavesdropper_run']['attack_classifier']['label'])")

echo "  clean run → eavesdrop_classifier=$clean_eav"
echo "  eav   run → eavesdrop_classifier=$eav_eav, attack_classifier=$eav_atk"

[[ "$clean_eav" == "clean" ]] || fail "Eavesdrop classifier mis-labeled clean run as $clean_eav"
[[ "$eav_eav"   != "clean" ]] || fail "Eavesdrop classifier missed the eavesdropper"
[[ "$eav_atk"   == "intercept_resend" ]] || fail "Attack classifier did not identify intercept_resend (got $eav_atk)"
ok "Criterion 3 — Eavesdrop classifier separates clean vs eavesdrop"
ok "Criterion 4 — Attack classifier identifies intercept_resend"

cd - > /dev/null
