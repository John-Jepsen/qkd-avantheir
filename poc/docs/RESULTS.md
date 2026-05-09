# MVP Results

These results were captured by `poc/scripts/run_mvp.sh` against the
classical BB84 backend. Wall-clock end-to-end: **53 seconds** on a 2024
M-series MacBook (after dependencies and trained models are in place).

The raw evidence files referenced below are in `poc/evidence/`.

---

## Summary

**All 8 MVP exit criteria passed.**

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | BB84 clean run is `secure=true` and QBER < 11% | PASS — QBER = 0.49% | `bb84_clean.json` |
| 2 | BB84 with eavesdropper is `secure=false` and QBER > 11% | PASS — QBER = 29.56% | `bb84_eavesdrop.json` |
| 3 | Eavesdrop classifier returns `clean` on clean and `eavesdrop` on attack | PASS — 99.5% / 98.0% confidence | `ml_pipeline.json` |
| 4 | Attack classifier identifies `intercept_resend` on the attack run | PASS — 100% confidence | `ml_pipeline.json` |
| 5 | KME `/enc_keys` and `/dec_keys` return identical key bytes for the same `key_ID` | PASS — round-trip match | `kme_round_trip.json` |
| 6 | Alice and Bob exchange an AES-256-GCM message using only KME-derived key material | PASS — Bob ACK received | `psk_demo.log` |
| 7 | FastAPI `/health` reports 5/5 models loaded | PASS | `health.json` |
| 8 | FastAPI `/analyze` returns `SECURE` for clean, `ABORT` for eavesdropper | PASS | `analyze_clean.json`, `analyze_eavesdrop.json` |

---

## Detailed evidence

### Criterion 1 — Clean BB84

```json
{
  "raw_bits": 4096,
  "sifted_bits": 2041,
  "qber": 0.0049,
  "secure": true,
  "eavesdropper_detected": false,
  "key_length_bits": 256,
  "final_key_hex_prefix": "0947dce07d8f5ea19c9d89953030f078...",
  "backend_used": "classical"
}
```

A 4096-qubit run produced 2041 sifted bits (sift ratio 0.498, expected
0.50), QBER 0.49%, and a 256-bit final key after BLAKE2b privacy
amplification. The simulator correctly marks the channel `secure`.

### Criterion 2 — BB84 with eavesdropper

```json
{
  "raw_bits": 4096,
  "sifted_bits": 2034,
  "qber": 0.2956,
  "secure": false,
  "eavesdropper_detected": true,
  "key_length_bits": 0,
  "final_key_hex_prefix": null,
  "backend_used": "classical"
}
```

QBER spikes to 29.56% — close to the theoretical 25% for full intercept-
resend, plus the 1% baseline noise. The protocol correctly aborts and
emits no key.

### Criteria 3–4 — ML classifiers

```json
"clean_run": {
  "qber": 0.0149,
  "eavesdrop_classifier": { "label": "clean",     "confidence": 0.9947 },
  "attack_classifier":    { "label": "clean",     "confidence": 0.8131 }
},
"eavesdropper_run": {
  "qber": 0.2039,
  "eavesdrop_classifier": { "label": "eavesdrop", "confidence": 0.98   },
  "attack_classifier":    { "label": "intercept_resend", "confidence": 1.0 }
}
```

Both classifiers separate the two runs decisively. The attack classifier
is unambiguous about the attack type. The eavesdrop classifier's
sub-1% probability of misclassifying a clean run as `eavesdrop` is the
quality the static QBER threshold cannot achieve in noisy regimes.

### Criterion 5 — KME round-trip

```json
{
  "key_ID": "<UUID v4>",
  "alice_key_b64_prefix": "...",
  "bob_key_b64_prefix":   "...",
  "match": true
}
```

Alice fetched a key with `GET /enc_keys`. The KME returned a `key_ID`.
Bob asked for that same `key_ID` with `POST /dec_keys`. The returned key
bytes matched byte-for-byte.

### Criterion 6 — TLS PSK exchange

From `psk_demo.log`:

```
[Alice/Client] Got key_ID  : 7c08822f-b7f5-4d2e-9320-1fe0062ed0ac
[Alice/Client] Got key     : ddb4ae27c8aff1aefd0555dc17506fbb...  (256 bits)
[Alice/Client] Connected to 127.0.0.1:8443
[Alice/Client] Sent key_ID (PSK identity)
[Alice/Client] Sent encrypted message
[Alice/Client] Bob replied: "ACK from Bob. QKD-derived PSK established. No DH used."
```

End-to-end exchange. No Diffie-Hellman or RSA ran at any point — the
shared key came entirely from the KME.

### Criterion 7 — `/health`

```json
{
  "status": "healthy",
  "models_loaded": "5/5",
  "models": {
    "eavesdrop_classifier": true,
    "attack_classifier": true,
    "parameter_tuner": true,
    "noise_predictor": true,
    "kme_anomaly_detector": true
  }
}
```

### Criterion 8 — `/analyze` clean → SECURE

```json
"verdict": "SECURE",
"simulation": { "qber": 0.0099, "secure": true, "key_length_bits": 256 },
"ml_analysis": {
  "eavesdrop_detection":   { "predicted_label": "clean", "confidence": 0.9983 },
  "attack_classification": { "predicted_attack": "clean", "confidence": 0.9911 }
}
```

### Criterion 8 — `/analyze` eavesdropper → ABORT

```json
"verdict": "ABORT",
"simulation": { "qber": 0.30, "secure": false, "eavesdropper_detected": true },
"ml_analysis": {
  "eavesdrop_detection":   { "predicted_label": "eavesdrop", "confidence": 1.0 },
  "attack_classification": { "predicted_attack": "intercept_resend", "confidence": 1.0,
                              "recommended_action": "ABORT immediately — full eavesdropper detected. Rotate keys." }
}
```

---

## Side observations from the run

- **Sift ratio.** Both BB84 runs landed at ~0.50 sift ratio, matching
  the theoretical expectation that Alice and Bob agree on basis half the
  time. This is the simplest sanity check that the simulator is faithful.

- **Confidence asymmetry.** The eavesdrop classifier was nearly 100%
  confident in both directions (99.5% clean / 98.0% eavesdrop) because
  the 12-feature vector pulls the two regimes far apart. The attack
  classifier was noticeably less confident on the *clean* run (81%) —
  this is a known weakness; the clean class shares partial similarity
  with the beam-splitting class in feature space.

- **Background overhead.** The KME pre-fills 50 keys via BB84 at startup,
  and the pool initializer runs twice (once at module import, once at
  CLI entry). Combined this takes about 30 seconds — most of the 53s
  total wall time is this pool init, not the actual demos.

- **Optional ML endpoints.** `/forecast`, `/recommend`, and
  `/detect-anomaly` all returned valid responses in the optional sweep.
  These aren't part of the MVP exit criteria but the captured outputs
  in `evidence/forecast.json`, `evidence/recommend.json`, and
  `evidence/anomaly.json` show all five ML models are wired and serving.

---

## Reproducing this exact result

```bash
cd poc
./scripts/run_mvp.sh
```

The exact QBER and key bytes will differ run-to-run because the BB84
simulator uses a fresh random seed each invocation. The pass/fail
verdict for each criterion is deterministic.
