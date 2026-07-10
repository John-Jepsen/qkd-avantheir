# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Technical documentation and working implementation for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure (TLS 1.3, IPsec/IKEv2, service mesh), part of the Avantheir initiative. This is a senior-led MSCS research deliverable. All five milestones are complete; the only remaining item is final presentation preparation.

## Structure

```
qkd-avantheir/
├── 01-qkd-foundations/         # BB84, CV-QKD, MDI-QKD, TF-QKD, global deployments
├── 02-tls-integration/         # TLS 1.3 PSK, hybrid QKD+PQC
├── 03-ipsec-ikev2-integration/ # IPsec RFC 8784, IKEv2 mixed-PSK
├── 04-service-mesh-auth/       # Symmetric rekeying, SDN-controlled allocation
├── 05-key-management/          # ETSI QKD 014 key management
├── 06-vendor-analysis/         # Toshiba, IDQ/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs, IBM, Lockheed
├── 07-operational-constraints/ # Operational constraints and limitations
├── 08-references/              # Full reference list
├── DOCS/
│   ├── capstone-outline.md     # Submission 2 outline with milestones and tech stack
│   ├── capstone-brief.md       # Concise project brief for submission
│   ├── system-architecture-diagram.md  # Mermaid diagrams: pipeline, relay, hybrid, ML layer, FastAPI
│   ├── vocab-study-guide.md    # QKD terminology reference (245 entries)
│   └── images/qkd-image.png    # QKD UML + sequence diagram
├── implementation/
│   ├── bb84_simulator.py       # BB84 on IBM Qiskit Aer: quantum circuits, depolarizing noise, dual-backend
│   ├── kme_server.py           # Flask ETSI GS QKD 014 REST API with thread-safe key pool
│   ├── kme_dual.py             # Dual-KME deployment (Alice port 5001, Bob port 5002) with peer sync
│   ├── tls_psk_demo.py         # End-to-end TLS PSK demo: Alice/Bob AES-256-GCM via KME
│   ├── ikev2_ppk_config.md     # strongSwan RFC 8784 PPK config guide
│   ├── hybrid_kdf.py           # Hybrid QKD+ML-KEM key derivation (HKDF-SHA256, ETSI TS 104 015)
│   ├── relay_network.py        # Trusted-node relay network (XOR hop-by-hop key relay)
│   ├── metrics.py              # MetricsCollector: QBER, key rate, pool depth tracking
│   ├── api.py                  # FastAPI adaptive security pipeline (port 8000) — closed-loop ML
│   ├── ml_eavesdrop_classifier.py  # RandomForest eavesdrop detection (replaces hard 11% threshold)
│   ├── ml_attack_classifier.py     # GradientBoosting 5-class attack classifier
│   ├── ml_noise_predictor.py       # ARIMA QBER time-series forecasting
│   ├── ml_parameter_tuner.py       # GB Regressor for optimal BB84 parameter selection
│   ├── ml_kme_anomaly.py           # Isolation Forest KME traffic anomaly detection
│   ├── features.py             # Shared 8-feature extraction (single source of truth)
│   ├── physics_constraints.py  # QKD physics bounds + covariance enforcement
│   ├── adversarial_eval.py     # Bounded perturbation evasion testing + hardening
│   ├── adversarial_gym.py      # DEAP evolutionary gym: co-evolutionary attacker/defender
│   ├── train_all_models.py     # One-shot training script for all ML models
│   ├── visualize_bb84.py       # BB84 visualization (circuit, QBER, noise sweep, key yield)
│   └── README.md               # Quick-start with three-terminal setup
├── frontend/                   # React + D3 adversarial benchmark dashboard (port 3000)
│   └── src/components/         # EvolutionChart, PhylogenyTree, Controls, etc.
├── poc/                        # Submission 3 MVP / Proof of Concept package — thin
│   │                           # shell over ../implementation/ (no duplicated source)
│   ├── README.md               # MVP scope statement and run instructions
│   ├── docker/                 # Dockerfile + docker-compose for one-command reproduction
│   ├── scripts/                # Numbered demo scripts (00_setup … 05_full_api_sweep, run_mvp.sh)
│   ├── docs/                   # ARCHITECTURE, MVP_SCOPE, RESULTS, NEXT_STEPS
│   └── evidence/               # Captured outputs (API JSON responses, server logs)
├── qkdsec/                     # Git submodule → github.com/John-Jepsen/qkdsec
│                               # Published pip package: ETSI 014 client + doctor probe,
│                               # numerical key-rate proofs, BB84 simulator
└── research-outputs /          # Note: trailing space in directory name
    ├── qkd_signal_research_agent_prompt.md
    └── qkd_signal_research_complete.md
```

Each numbered directory (01–06) also contains a `phase*.md` supporting research file alongside the main document. Directories 07 and 08 have no phase file.

## Submodules

- **`qkdsec/`** → [`John-Jepsen/qkdsec`](https://github.com/John-Jepsen/qkdsec).
  Canonical home of the pip-installable `qkdsec` package. After cloning the
  monorepo, run `git submodule update --init qkdsec`. To work on the package,
  `cd qkdsec`, branch and push from there — the monorepo only tracks the
  pinned SHA. To pick up upstream changes: `git submodule update --remote qkdsec`,
  then commit the new pointer in the monorepo.

## Key Technical Context

- **Baseline protocol**: Discrete-Variable QKD (BB84-style); CV-QKD where cost/integration advantages apply; MDI-QKD for highest implementation security
- **Vendor coverage**: Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs (Tier 1-2 QKD vendors) plus IBM (PQC/research) and Lockheed Martin (defense integration)
- **Standards**: RFC 8446 (TLS 1.3), RFC 8784 (IKEv2 mixed-PSK), ETSI GS QKD 004/014/015/016, ETSI TS 104 015 (hybrid), IETF RFC 9794 (hybrid terminology), NIST FIPS 203/204/205 (PQC)
- **Strategic framing**: QKD vs PQC is not either/or — the docs map where each is appropriate. Hybrid QKD+PQC is the recommended architecture for highest-assurance deployments.
- **Implementation stack**: Python 3.10+, IBM Qiskit 2.x / Qiskit Aer 0.17.x (quantum circuit simulator), Flask, FastAPI/Uvicorn, scikit-learn, statsmodels (ARIMA), `cryptography` library, `requests`. QBER abort threshold: >11%.
- **ML security layer**: Five ML models form a closed-loop adaptive pipeline — eavesdrop detection (RandomForest), attack classification (GradientBoosting, 5 classes), QBER forecasting (ARIMA), parameter tuning (GB Regressor), and KME traffic anomaly detection (Isolation Forest). The FastAPI service (`api.py`) unifies all models behind REST endpoints.
- **Adversarial agents**: DEAP evolutionary gym co-evolves attack strategies (bounded by QKD physics constraints) against defender models that harden via adversarial retraining each generation. Phylogeny tree tracks lineage. React dashboard streams evolution via WebSocket.

## Writing Conventions

- Documents use tables for structured comparisons, ASCII diagrams for protocol flows
- Cross-references between documents are by filename (e.g., "see 05-key-management.md")
- Maintain the numbered prefix ordering when adding new documents

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
