# Capstone Project Outline — Submission 2

**Student:** John Jepsen
**Program:** MSCS (Season 04 Masters)
**Date:** March 30, 2026

---

## Approved Idea (Submission 1)

Quantum Key Distribution (QKD) integration into enterprise network security infrastructure.

A technical documentation suite, reference architecture, and working implementation that replaces classical key exchange (Diffie-Hellman/ECDHE) with QKD-derived symmetric key material across three enterprise integration targets: TLS 1.3, IPsec/IKEv2 VPN, and service-to-service mesh authentication. The project evaluates and demonstrates the hybrid QKD + Post-Quantum Cryptography (PQC) approach as the recommended architecture for highest-assurance deployments.

Motivating threat: "harvest now, decrypt later" adversaries who record encrypted traffic today to decrypt it once a sufficiently powerful quantum computer becomes available, making quantum-safe key exchange an active operational concern rather than a future research topic.

---

## 1. Business Logic

### Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         QKD Physical Layer                          │
│  Alice's QKD Node ──── quantum fiber channel ────► Bob's QKD Node  │
│       (photon source)         BB84 protocol        (photon detector) │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ raw key bits
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Post-Processing / Distillation Pipeline              │
│   Basis Sifting → QBER Estimation → Error Correction (Cascade)     │
│                → Privacy Amplification → 256-bit symmetric key      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ key material
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│               Key Management Entity (KME) — ETSI GS QKD 014        │
│                                                                     │
│  Key Store  ←──── bb84_simulator.py (software emulation)           │
│      │                                                              │
│  REST API:                                                          │
│    GET  /enc_keys  → key_ID + key_bytes  → master SAE               │
│    POST /dec_keys  → key_bytes by ID     → slave SAE                │
└──────────┬──────────────────────────────────────────┬──────────────┘
           │ key_ID + key material                    │ key material
           ▼                                          ▼
┌──────────────────────┐                 ┌────────────────────────────┐
│  Application Layer A │                 │  Application Layer B       │
│                      │                 │                            │
│  TLS 1.3 PSK         │◄── encrypted ──►│  TLS 1.3 PSK               │
│  (RFC 8446 §2.2)     │    channel      │  (RFC 8446 §2.2)           │
│                      │                 │                            │
│  IPsec/IKEv2 PPK     │                 │  IPsec/IKEv2 PPK           │
│  (RFC 8784)          │                 │  (RFC 8784)                │
│                      │                 │                            │
│  Service Mesh Auth   │                 │  Service Mesh Auth         │
│  (ETSI QKD 014)      │                 │  (ETSI QKD 014)            │
└──────────────────────┘                 └────────────────────────────┘

                ┌──────────────────────────────────┐
                │        Hybrid Layer (optional)   │
                │  KME key  +  PQC key (ML-KEM)    │
                │  ──── HKDF ────► combined secret │
                │  (ETSI TS 104 015 / RFC 9794)    │
                └──────────────────────────────────┘
```

### Component Relationships

| Component | Role | Depends On | Consumed By |
|-----------|------|-----------|-------------|
| BB84 Simulator | Generates raw symmetric key material via quantum protocol simulation | None (entry point) | KME Server |
| KME Server (ETSI QKD 014) | Stores, indexes, and dispenses key material to authorized applications via REST | BB84 Simulator | TLS PSK Demo, IPsec Config |
| TLS PSK Demo | Demonstrates QKD-backed authenticated encryption replacing Diffie-Hellman | KME Server | End-user validation |
| IKEv2 PPK Config | Maps KME-derived keys into strongSwan as RFC 8784 Post-quantum Preshared Keys | KME Server (conceptually) | IPsec/VPN operator |
| Documentation Suite (8 docs) | Explains protocol mechanics, vendor landscape, and operational constraints | All implementation components | Practitioners and evaluators |
| ML Analysis Modules | Eavesdropper detection, noise prediction, anomaly detection, attack classification | BB84 Simulator, KME Server | Security monitoring and adaptive tuning |
| Hybrid QKD+PQC Architecture | Combines QKD keys with ML-KEM (Kyber) for defense-in-depth | KME Server + NIST PQC standards | Highest-assurance deployments |

---

## 2. Major Milestones

### Milestone 1 — QKD Foundations & Research Documentation

Deliver a thorough technical foundation covering QKD protocol variants, hardware realities, and global deployment landscape. This is the research bedrock that the integration work builds on.

---

### Milestone 2 — Protocol Integration Documentation (TLS, IPsec, Service Mesh)

Document the concrete mechanisms for integrating QKD key material into each target protocol. Each integration section must stand alone as a practitioner reference.

---

### Milestone 3 — Key Management Architecture & Vendor Analysis

Document the ETSI QKD 014 key lifecycle, trusted-node models, hybrid key derivation, and vendor profiles covering eight commercial/research entities.

---

### Milestone 4 — Working Implementation (BB84 + KME + PSK Demo)

Produce a runnable Python stack that emulates the end-to-end QKD key delivery pipeline — from qubit simulation through key management to authenticated encryption — with no quantum hardware required.

---

### Milestone 5 — Integration, Testing & Final Deliverables

Tie all components together: cross-reference documentation against implementation, validate the running stack, produce the capstone brief, and prepare the final presentation.

---

## 3. Specifications / Requirements

### Milestone 1 — QKD Foundations & Research Documentation

- [] Document BB84 protocol mechanics: qubit encoding, basis sifting, QBER estimation, error correction, privacy amplification
- [] Cover CV-QKD, MDI-QKD, and TF-QKD as protocol variants with tradeoff analysis
- [] Describe QKD hardware components: photon sources, quantum channels, single-photon detectors, classical channel
- [] Survey global QKD deployment landscape (EU, China, Japan, US)
- [] Explain the "harvest now, decrypt later" threat and its urgency for enterprise security teams
- [] Define QKD vs. PQC positioning — when each is appropriate

### Milestone 2 — Protocol Integration Documentation

**TLS 1.3 Integration**
- [] Map QKD key material to RFC 8446 PSK handshake modes (external PSK, resumption PSK)
- [] Document `psk_dhe_ke` vs. `psk_ke` mode selection rationale
- [] Cover HKDF key schedule integration points for QKD-derived secrets
- [] Address mTLS mutual authentication with QKD-backed PSK
- [] Include hybrid QKD+ML-KEM key derivation (ETSI TS 104 015)

**IPsec/IKEv2 Integration**
- [] Map QKD key material to RFC 8784 Post-quantum Preshared Key (PPK) mechanism
- [] Document IKEv2 USE_PPK and PPK_IDENTITY notify payloads
- [] Cover PPK injection into IKEv2 SK_d derivation
- [] Provide strongSwan configuration guide for RFC 8784 PPK

**Service Mesh Integration**
- [] Document short-interval symmetric rekeying pattern for service-to-service auth
- [] Cover SDN-controlled QKD allocation across mesh topologies
- [] Address sidecar proxy integration for QKD key consumption

### Milestone 3 — Key Management 

**Key Management**
- [] Document ETSI GS QKD 014 API endpoints (enc_keys, dec_keys, status)
- [] Cover key ID lifecycle: generation, storage, delivery, expiry
- [] Address trusted-node relay models for extending QKD range
- [] Document hybrid key derivation (HKDF combining QKD + PQC output)
- [] Cover key freshness, rotation intervals, and entropy accounting

### Milestone 4 — Working Implementation

**BB84 Simulator (`bb84_simulator.py`)**
- [] Simulate qubit exchange over ideal and noisy channels
- [] Implement basis sifting and raw key generation
- [] Implement QBER estimation with configurable noise threshold
- [] Implement error correction (Cascade-style reconciliation)
- [] Implement privacy amplification (hash-based key compression)
- [] Demonstrate eavesdropper detection: abort when QBER exceeds threshold
- [] Output deterministic 256-bit symmetric key

**KME Server (`kme_server.py`)**
- [] Implement ETSI GS QKD 014 REST endpoints: `/enc_keys`, `/dec_keys`, `/status`
- [] Back key store with BB84 simulator output
- [] Implement background key refill as keys are consumed
- [] Assign and track unique key IDs
- [] Validate SAE identity on key requests

**TLS PSK Demo (`tls_psk_demo.py`)**
- [] Alice fetches key from KME `/enc_keys` endpoint
- [] Alice transmits key_ID to Bob out-of-band
- [] Bob fetches matching key from KME `/dec_keys` endpoint
- [] Alice encrypts message with AES-256-GCM using QKD-derived key
- [] Bob decrypts and verifies — no classical key agreement used
- [] Run end-to-end successfully in two-terminal demo

**IKEv2 PPK Config Guide (`ikev2_ppk_config.md`)**
- [] Document strongSwan `ppk_id` and `ppk` configuration fields
- [] Map KME key fetch to PPK provisioning workflow
- [] Provide example swanctl.conf snippets for RFC 8784 PPK

### Milestone 5 — Integration, Testing & Final Deliverables

- [] Build ML-enhanced analysis modules (eavesdrop classifier, noise predictor, anomaly detector, attack classifier, parameter tuner)
- [] Cross-reference all documentation against implementation components
- [] Verify `python tls_psk_demo.py client/server` runs end-to-end without errors
- [] Confirm BB84 simulator correctly aborts on simulated eavesdropper scenario
- [] Produce capstone brief (`DOCS/capstone-brief.md`)
- [] Produce vocab study guide (`DOCS/vocab-study-guide.md`, 245 entries)
- [] Complete reference list (`08-references/08-references.md`)
- [] Final presentation preparation

---

## 4. Technology Stack

### Languages

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.10+ | BB84 simulator, KME server, PSK demo, ML modules |
| Markdown | — | All documentation (8 documents + guides) |

### Libraries & Frameworks

| Library | Version | Usage |
|---------|---------|-------|
| Flask | 3.x | ETSI GS QKD 014 REST API server (`kme_server.py`) |
| requests | 2.x | HTTP client for KME key fetch in PSK demo |
| cryptography | 42.x | AES-256-GCM encryption, HKDF key derivation |
| scikit-learn | 1.x | Random Forest, Gradient Boosting, Isolation Forest (ML modules) |
| statsmodels | 0.14+ | ARIMA time-series forecasting (noise prediction) |
| hashlib | stdlib | BLAKE2b / SHA-256 for privacy amplification |
| secrets / os.urandom | stdlib | Cryptographically secure random bit generation |

### Standards & Protocols

| Standard | Usage |
|----------|-------|
| RFC 8446 (TLS 1.3) | PSK handshake modes, key schedule integration |
| RFC 8784 (IKEv2 mixed-PSK) | PPK injection into IKEv2 key derivation |
| ETSI GS QKD 014 | Key management REST API design |
| ETSI GS QKD 004 | QKD application interface reference |
| ETSI TS 104 015 | Hybrid QKD+PQC key derivation |
| IETF RFC 9794 | Hybrid key exchange terminology |
| NIST FIPS 203 (ML-KEM) | PQC key encapsulation in hybrid architecture |
| NIST FIPS 204 (ML-DSA) | PQC digital signatures reference |
| NIST FIPS 205 (SLH-DSA) | PQC stateless hash-based signatures reference |

### Infrastructure & Tools

| Tool | Usage |
|------|-------|
| strongSwan | IKEv2/IPsec VPN software referenced in PPK configuration guide |
| Git / GitHub | Version control |
| VS Code | Primary editor |
| macOS | Development OS |
| curl | Manual API testing against KME server |

---

## 5. Post-Project Change Justifications

### Major Milestone Changes

**Added to Milestone 5 — ML-Enhanced Analysis Modules**

Five machine learning modules were added in Milestone 5:

| Module | Model | Purpose | Result |
|--------|-------|---------|--------|
| `ml_eavesdrop_classifier.py` | Random Forest | Detect eavesdroppers beyond simple QBER threshold | 93% accuracy |
| `ml_parameter_tuner.py` | Gradient Boosting Regression | Adaptively tune BB84 parameters based on channel conditions | R² = 0.85 |
| `ml_noise_predictor.py` | ARIMA(1,0,1) | Forecast channel QBER 5–10 rounds ahead | MAE = 0.006 |
| `ml_kme_anomaly.py` | Isolation Forest | Detect anomalous KME traffic patterns | 86% detection rate |
| `ml_attack_classifier.py` | Gradient Boosting Classifier | Classify attack type (5 classes) | 96% accuracy |

**Justification:** The working BB84 simulator and KME server produced rich signal data (QBER, sift ratios, error distributions, request patterns) that could be analyzed beyond static thresholds. Adding ML classifiers demonstrated that sophisticated partial-intercept attacks — which fall below the standard 11% QBER abort threshold — can still be detected through pattern analysis. This directly strengthens the project's security analysis and aligns with the hybrid QKD+classical approach.

