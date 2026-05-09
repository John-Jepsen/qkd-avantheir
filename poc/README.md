# MVP / Proof of Concept — ML-Augmented QKD

**Project:** Adaptive Machine Learning Defenses for Quantum Key Distribution
**Student:** John Jepsen
**Program:** MSCS Capstone
**Phase:** Submission 3 (MVP / POC)
**Date:** 2026-05-09

---

## What this folder is

This folder packages the **Minimum Viable Product** for the capstone project.
It is a thin shell over the working code in `../implementation/` — it does
not duplicate source. Everything here exists to:

1. State what the MVP is (and what it is not).
2. Show the business logic is valid (the closed-loop ML+QKD pipeline runs
   end-to-end).
3. Make the POC reproducible in one command.
4. Capture evidence (sample outputs, screenshots of API responses) so the
   result is verifiable without re-running.

The full code lives in `../implementation/`. The full research documentation
lives in `../DOCS/`. This folder is the bridge between them.

---

## MVP scope (what is in)

The MVP is a single closed-loop pipeline:

```
BB84 quantum simulation  →  KME (ETSI 014)  →  TLS PSK exchange
        │
        └──►  ML security layer  ──►  verdict (SECURE | ABORT)
                  (5 models)
```

Concretely, the MVP demonstrates:

| Capability | Module | Verified by |
|------------|--------|-------------|
| BB84 protocol on Qiskit Aer with classical fallback | `bb84_simulator.py` | `scripts/01_bb84_demo.sh` |
| Eavesdropper detection that beats the 11% QBER threshold | `ml_eavesdrop_classifier.py` (RandomForest, 12 features) | `scripts/02_ml_pipeline_demo.sh` |
| Attack classification (5 classes) | `ml_attack_classifier.py` (GradientBoosting) | `scripts/02_ml_pipeline_demo.sh` |
| ETSI GS QKD 014 KME REST API | `kme_server.py` (Flask) | `scripts/03_kme_psk_demo.sh` |
| Diffie-Hellman-free TLS PSK exchange | `tls_psk_demo.py` | `scripts/03_kme_psk_demo.sh` |
| Unified FastAPI pipeline (`/analyze`) | `api.py` | `scripts/04_api_demo.sh` |

Models 4 and 5 (ARIMA noise predictor, Isolation Forest KME anomaly detector)
load and serve through the same FastAPI service but are not part of the
critical path the MVP demonstrates. They are exercised by `scripts/05_full_api_sweep.sh`.

## MVP scope (what is out)

Deliberately out of scope for the MVP — these are tracked for later milestones,
not gaps in the POC:

- **Real quantum hardware.** The pipeline runs against the Qiskit Aer
  simulator. Integration with IBM Quantum Runtime is wired but not exercised
  here.
- **The React + D3 adversarial dashboard.** It runs (`../frontend/`) but the
  MVP is the backend pipeline. The dashboard is part of M5.
- **The full DEAP evolutionary gym.** The eval module
  (`adversarial_eval.py`) ships and is callable through the API; the gym
  itself is M5 territory.
- **Production hardening.** No auth on the KME, in-memory key pool, no TLS
  on the management plane. This is a reference architecture, not a deployable
  product.

---

## Run it

### Option A — Docker (recommended)

You only need Docker. Models are baked in at build time, so first run after
build is fast.

```bash
# From the repo root
docker build -f poc/docker/Dockerfile -t qkd-poc .
docker run --rm qkd-poc
```

That builds the image and runs the full MVP demo, asserting all 8 exit
criteria. To capture the evidence files on the host:

```bash
docker run --rm -v "$PWD/poc/evidence:/app/poc/evidence" qkd-poc
```

For long-running services (KME, FastAPI) and the full multi-container
flow, see [`docker/README.md`](docker/README.md).

### Option B — Local Python

You need Python 3.10+ on macOS or Linux.

```bash
cd poc
./scripts/run_mvp.sh
```

That single script does everything:

1. Creates a virtualenv at `../implementation/.venv` if missing.
2. Installs `../implementation/requirements.txt`.
3. Trains all 5 ML models if pickle files are missing (`train_all_models.py`).
4. Runs the BB84 simulator (clean + eavesdropper).
5. Starts the KME server, runs the TLS PSK demo, tears the KME down.
6. Starts the FastAPI service, hits `/analyze` clean, hits `/analyze`
   eavesdropper, captures both responses to `evidence/`, tears down.
7. Prints a final pass/fail summary against the MVP exit criteria.

For step-by-step exploration, run the individual scripts in `scripts/`
in order.

---

## What success looks like

The MVP passes when **all of these are true** (asserted by `run_mvp.sh`):

| # | Criterion | Where checked |
|---|-----------|---------------|
| 1 | BB84 clean run returns `secure=true`, QBER < 11% | `01_bb84_demo.sh` |
| 2 | BB84 with eavesdropper returns `secure=false`, QBER > 11% | `01_bb84_demo.sh` |
| 3 | Eavesdrop classifier predicts `clean` on clean run, `eavesdrop` on attack run | `02_ml_pipeline_demo.sh` |
| 4 | Attack classifier identifies `intercept_resend` on the attack run | `02_ml_pipeline_demo.sh` |
| 5 | KME `/enc_keys` and `/dec_keys` return identical key bytes for the same `key_ID` | `03_kme_psk_demo.sh` |
| 6 | Alice and Bob exchange an AES-256-GCM message using only KME-derived key material (no DH) | `03_kme_psk_demo.sh` |
| 7 | FastAPI `/health` reports 5/5 models loaded | `04_api_demo.sh` |
| 8 | FastAPI `/analyze` returns verdict `SECURE` for clean and `ABORT` for eavesdropper | `04_api_demo.sh` |

Sample passing output is captured in `evidence/` and summarized in
`docs/RESULTS.md`.

---

## Folder layout

```
poc/
├── README.md                  ← this file
├── scripts/
│   ├── run_mvp.sh             ← single-command demo
│   ├── 00_setup.sh            ← venv + deps + model training (no-op in container)
│   ├── 01_bb84_demo.sh        ← BB84 clean vs eavesdropper
│   ├── 02_ml_pipeline_demo.sh ← Eavesdrop + attack classifier on BB84 output
│   ├── 03_kme_psk_demo.sh     ← KME + TLS PSK end-to-end
│   ├── 04_api_demo.sh         ← FastAPI /health + /analyze
│   └── 05_full_api_sweep.sh   ← All 11 endpoints (forecast, recommend, anomaly, etc.)
├── docker/
│   ├── README.md              ← Docker usage in detail
│   ├── Dockerfile             ← Single image, multi-mode entrypoint
│   ├── docker-compose.yml     ← KME + FastAPI as long-lived services
│   └── entrypoint.sh          ← Routes mvp/api/kme/psk-server/psk-client
├── docs/
│   ├── MVP_SCOPE.md           ← What the MVP is and isn't
│   ├── ARCHITECTURE.md        ← MVP-level architecture diagram
│   ├── RESULTS.md             ← Pass/fail summary with sample outputs
│   └── NEXT_STEPS.md          ← Honest list of what comes after the MVP
└── evidence/                  ← Captured sample outputs (populated by run_mvp.sh)
    ├── bb84_clean.json
    ├── bb84_eavesdrop.json
    ├── analyze_clean.json
    ├── analyze_eavesdrop.json
    ├── kme_status.json
    └── psk_demo.log
```

---

## Why a separate POC folder

Per the assignment brief:

> After organizing the Milestones (Submission 2), Students are required to
> organize their workflow to have a Minimum Viable Product as the first
> deliverable... This serves a double purpose: First, it shows both Qwasar
> and Students that their business logic is valid. Second, it allows
> Students to review their Milestones, timeframe for each of them, and also
> review the technology they are using.

The folder is the bundled artifact a reviewer can run in one command to
validate that the project is real and the chosen stack works. Putting it at
the repo root makes it the obvious entry point for anyone reviewing the
deliverable.
