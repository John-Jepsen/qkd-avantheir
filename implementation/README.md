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

## Requirements

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ required. The BB84 simulator requires `qiskit` and `qiskit-aer` (IBM Quantum).
The ML modules require scikit-learn, numpy, and statsmodels.

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
