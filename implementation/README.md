# QKD Implementation

A runnable Python stack that emulates the QKD key delivery pipeline described
in the project documentation. The BB84 protocol runs on IBM Qiskit quantum
circuits (Aer simulator) by default, with a classical fallback available.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                bb84_simulator.py (Qiskit Aer)               │
│   Alice ──quantum circuit──► Bob   (sifting, QBER, PA)      │
│          (X/H gates, depolarizing noise model)              │
│                        │                                     │
│                  256-bit key out                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      kme_server.py                          │
│   ETSI GS QKD 014 REST API  (Flask)                         │
│   GET  /enc_keys  →  key_ID + key_bytes  →  master SAE      │
│   POST /dec_keys  →  key_bytes (by ID)   →  slave SAE       │
└──────────┬──────────────────────────────────────┬───────────┘
           │ key_ID + key_bytes                   │ key_bytes (by ID)
           ▼                                      ▼
┌──────────────────┐                   ┌──────────────────────┐
│  Alice (client)  │── key_ID ────────►│  Bob (server)        │
│  tls_psk_demo.py │                   │  tls_psk_demo.py     │
│  AES-256-GCM enc │◄── encrypted ────►│  AES-256-GCM dec     │
└──────────────────┘                   └──────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `bb84_simulator.py` | BB84 protocol on Qiskit Aer: quantum circuit preparation (X/H gates), depolarizing noise channel, basis sifting, QBER, error correction, privacy amplification. Dual-backend: `qiskit` (default) or `classical` fallback. |
| `kme_server.py` | ETSI GS QKD 014 REST API backed by BB84 simulator |
| `tls_psk_demo.py` | End-to-end PSK demo: Alice and Bob fetch the same key, encrypt a message |
| `ikev2_ppk_config.md` | strongSwan IKEv2 configuration guide for RFC 8784 PPK |
| `ml_eavesdrop_classifier.py` | Random Forest eavesdropper detection (replaces hard QBER threshold) |
| `ml_parameter_tuner.py` | Gradient Boosted regression for adaptive protocol parameter optimization |
| `ml_noise_predictor.py` | ARIMA time-series forecasting for channel noise prediction |
| `ml_kme_anomaly.py` | Isolation Forest anomaly detection on KME key management traffic |
| `ml_attack_classifier.py` | Multi-class Gradient Boosted classifier for 5 QKD attack types |
| `api.py` | FastAPI REST API — unified pipeline endpoint for all ML models |
| `train_all_models.py` | Training pipeline: generates datasets and saves models to `data/` |

## Requirements

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ required. The BB84 simulator requires `qiskit` and `qiskit-aer` (IBM Quantum).
The ML modules require scikit-learn, numpy, and statsmodels.
The API requires `fastapi` and `uvicorn`.

## Quick start

### 1 — Run the BB84 simulator standalone

```bash
python bb84_simulator.py
```

Output runs all three scenarios (normal, noisy, eavesdropper) on both the
Qiskit Aer backend and the classical fallback, side by side.

To run with only the classical backend (no Qiskit required):

```python
from bb84_simulator import BB84Protocol
result = BB84Protocol(backend="classical").run(n_bits=4096)
```

### 2 — Run the KME server

```bash
python kme_server.py
```

The server starts on `http://127.0.0.1:5000` and pre-generates 50 keys from
the BB84 simulator. It refills automatically in the background as keys are
consumed.

```bash
# Check status
curl http://127.0.0.1:5000/api/v1/keys/sae-bob/status

# Fetch a key (master SAE)
curl http://127.0.0.1:5000/api/v1/keys/sae-bob/enc_keys
```

### 3 — Run the PSK demo

With the KME server running, open two additional terminals:

```bash
# Terminal 2 — Bob (server/responder)
python tls_psk_demo.py server

# Terminal 3 — Alice (client/initiator)
python tls_psk_demo.py client
```

Alice fetches a key from the KME, sends the key_ID to Bob, Bob retrieves
the matching key from the KME, and they exchange an AES-256-GCM encrypted
message. No Diffie-Hellman occurs anywhere in this flow.

### 4 — IKEv2 integration

See `ikev2_ppk_config.md` for step-by-step strongSwan configuration using
keys dispensed by the KME server.

### 5 — Run the ML modules

Each ML module is self-contained with a demo when run directly:

```bash
source .venv/bin/activate

# Eavesdropper detection (Random Forest, 93% accuracy)
python ml_eavesdrop_classifier.py

# Adaptive parameter tuning (Gradient Boosted Regression, R²=0.85)
python ml_parameter_tuner.py

# Channel noise prediction (ARIMA, MAE=0.006)
python ml_noise_predictor.py

# KME traffic anomaly detection (Isolation Forest, 86% detection rate)
python ml_kme_anomaly.py

# Multi-class attack recognition (Gradient Boosted Classifier, 96% accuracy)
python ml_attack_classifier.py
```

### 6 — Run the adaptive security pipeline API

The API unifies the full closed-loop pipeline behind a single service. It loads
all 5 ML models at startup (~0.3s) and exposes them via REST endpoints.

**Prerequisites:** trained models must exist in `data/`. If they don't, run the
training pipeline first:

```bash
source .venv/bin/activate
python train_all_models.py    # generates data/*.pkl and data/*.csv
```

**Start the server:**

```bash
uvicorn api:app --port 8000
```

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

**Check health:**

```bash
curl http://127.0.0.1:8000/health
```

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

**Run a full pipeline analysis (clean channel):**

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": false}'
```

```json
{
  "verdict": "SECURE",
  "simulation": {
    "qber": 0.0098,
    "secure": true,
    "final_key_hex": "61b4fac2..."
  },
  "ml_analysis": {
    "eavesdrop_detection": {"predicted_label": "clean", "confidence": 1.0},
    "attack_classification": {"predicted_attack": "clean", "confidence": 0.9999},
    "parameter_recommendation": {"recommended_n_bits": 2048, "predicted_key_rate": 0.1259}
  },
  "recommended_actions": ["No action needed — channel is secure"]
}
```

**Detect an eavesdropper:**

```bash
curl -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": true}'
```

```json
{
  "verdict": "ABORT",
  "simulation": {"qber": 0.275, "secure": false, "eavesdropper_detected": true},
  "ml_analysis": {
    "eavesdrop_detection": {"predicted_label": "eavesdrop", "confidence": 1.0},
    "attack_classification": {"predicted_attack": "intercept_resend", "confidence": 1.0}
  },
  "recommended_actions": [
    "Protocol aborted — QBER exceeded threshold",
    "ABORT immediately — full eavesdropper detected. Rotate keys."
  ]
}
```

**Forecast channel noise:**

```bash
curl -X POST http://127.0.0.1:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"steps": 10}'
```

**Get optimal BB84 parameters for current noise:**

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"observed_noise": 0.03}'
```

**Detect KME traffic anomalies:**

```bash
# Normal traffic — returns is_anomaly: false
curl -X POST http://127.0.0.1:8000/detect-anomaly \
  -H "Content-Type: application/json" \
  -d '{
    "request_rate_1min": 2.0, "mean_keys_requested": 2.5,
    "mean_key_size": 256, "inter_request_std": 12.0,
    "enc_dec_ratio": 1.1, "unique_sae_count": 3,
    "max_burst_rate": 2, "failed_ratio": 0.0
  }'

# Burst attack — returns is_anomaly: true
curl -X POST http://127.0.0.1:8000/detect-anomaly \
  -H "Content-Type: application/json" \
  -d '{
    "request_rate_1min": 45.0, "mean_keys_requested": 15.0,
    "mean_key_size": 1024, "inter_request_std": 1.2,
    "enc_dec_ratio": 10.0, "unique_sae_count": 1,
    "max_burst_rate": 20, "failed_ratio": 0.0
  }'
```

**API endpoints summary:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/analyze` | Full pipeline: BB84 sim → eavesdrop detection → attack classification → parameter tuning |
| `POST` | `/forecast` | ARIMA QBER forecast with confidence intervals |
| `POST` | `/recommend` | Optimal BB84 parameters for a given noise level |
| `POST` | `/detect-anomaly` | Classify KME traffic window as normal/anomalous |
| `GET` | `/health` | Model status and session stats |
| `GET` | `/models` | Algorithm details for each loaded model |

---

## How it maps to production QKD

| This simulation | Real deployment |
|----------------|----------------|
| `bb84_simulator.py` (Qiskit Aer) | Physical QKD hardware (Toshiba, ID Quantique, etc.) |
| Single `kme_server.py` | Paired KMEs at each end, synchronized via quantum channel |
| `key_ID` sent over TCP | `key_ID` exchanged via management plane or IKE negotiation |
| AES-256-GCM channel | TLS 1.3 external PSK (RFC 8446), IKEv2 PPK (RFC 8784), or ETSI service mesh rekeying |

The ETSI GS QKD 014 API is identical in both cases — applications see the
same REST interface regardless of whether keys come from simulation or hardware.

### Qiskit backend details

The Qiskit backend prepares each qubit using real quantum gate operations:

| Step | Gate | Purpose |
|------|------|---------|
| Bit encoding | `X` | Flip qubit to \|1⟩ when Alice's bit is 1 |
| Basis selection | `H` | Rotate to X (diagonal) basis when basis = 1 |
| Channel noise | `id` + depolarizing error | Simulates physical channel QBER via Aer noise model |
| Measurement basis | `H` | Rotate back to Z basis before measurement |

Eavesdropper (intercept-resend) is modeled as two sequential circuits:
1. Alice prepares → Eve measures in random basis (ideal backend)
2. Eve re-prepares from her result → Bob measures (noisy backend)

This introduces ~25% QBER from wrong-basis collapse, matching the theoretical BB84 security bound.
