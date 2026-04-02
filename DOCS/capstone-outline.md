# Capstone Outline — Submission 2

**Student:** John Jepsen
**Program:** MSCS
**Date:** March 16, 2026

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
│  Service Mesh mTLS   │                 │  Service Mesh mTLS         │
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
| KME Server (ETSI QKD 014) | Stores, indexes, and dispenses key material to authorized applications via REST | BB84 Simulator | TLS PSK demo, IPsec config |
| TLS PSK Demo | Demonstrates QKD-backed authenticated encryption replacing Diffie-Hellman | KME Server | End-user validation |
| IKEv2 PPK Config | Maps KME-derived keys into strongSwan as RFC 8784 Post-quantum Preshared Keys | KME Server (conceptually) | IPsec/VPN operator |
| Documentation Suite (8 docs) | Explains protocol mechanics, vendor landscape, and operational constraints | All implementation components | Practitioners and evaluators |
| Hybrid QKD+PQC Architecture | Combines QKD keys with ML-KEM (Kyber) for defense-in-depth | KME Server + NIST PQC standards | Highest-assurance deployments |

---

## 2. Major Milestones

### Milestone 1 — QKD Foundations & Research Documentation
*Estimated effort: ~3 weeks*

Deliver a thorough technical foundation covering QKD protocol variants, hardware realities, and global deployment landscape. This is the research bedrock that the integration work builds on.

**Status:** Complete

---

### Milestone 2 — Protocol Integration Documentation (TLS, IPsec, Service Mesh)
*Estimated effort: ~4 weeks*

Document the concrete mechanisms for integrating QKD key material into each target protocol. Each integration section must stand alone as a practitioner reference.

**Status:** Complete

---

### Milestone 3 — Key Management Architecture & Vendor Analysis
*Estimated effort: ~3 weeks*

Document the ETSI QKD 014 key lifecycle, trusted-node models, hybrid key derivation, and vendor profiles covering eight commercial/research entities.

**Status:** Complete

---

### Milestone 4 — Working Implementation (BB84 + KME + PSK Demo)
*Estimated effort: ~2 weeks*

Produce a runnable Python stack that emulates the end-to-end QKD key delivery pipeline — from qubit simulation through key management to authenticated encryption — with no quantum hardware required.

**Status:** Complete

---

### Milestone 5 — Integration, Testing & Final Deliverables
*Estimated effort: ~1 week*

Tie all components together: cross-reference documentation against implementation, validate the running stack, produce the capstone brief, and prepare the final presentation.

**Status:** Complete

---

## 3. Specifications / Requirements

### Milestone 1 — QKD Foundations & Research Documentation

- [x] Document BB84 protocol mechanics: qubit encoding, basis sifting, QBER estimation, error correction, privacy amplification
- [x] Cover CV-QKD, MDI-QKD, and TF-QKD as protocol variants with tradeoff analysis
- [x] Describe QKD hardware components: photon sources, quantum channels, single-photon detectors, classical channel
- [x] Survey global QKD deployment landscape (EU, China, Japan, US)
- [x] Explain the "harvest now, decrypt later" threat and its urgency for enterprise security teams
- [x] Define QKD vs. PQC positioning — when each is appropriate

---

### Milestone 2 — Protocol Integration Documentation

**TLS 1.3 Integration**
- [x] Map QKD key material to RFC 8446 PSK handshake modes (external PSK, resumption PSK)
- [x] Document `psk_dhe_ke` vs. `psk_ke` mode selection rationale
- [x] Cover HKDF key schedule integration points for QKD-derived secrets
- [x] Address mTLS mutual authentication with QKD-backed PSK
- [x] Include hybrid QKD+ML-KEM key derivation (ETSI TS 104 015)

**IPsec/IKEv2 Integration**
- [x] Map QKD key material to RFC 8784 Post-quantum Preshared Key (PPK) mechanism
- [x] Document IKEv2 USE_PPK and PPK_IDENTITY notify payloads
- [x] Cover PPK injection into IKEv2 SK_d derivation
- [x] Provide strongSwan configuration guide for RFC 8784 PPK

**Service Mesh Integration**
- [x] Document short-interval symmetric rekeying pattern for service-to-service auth
- [x] Cover SDN-controlled QKD allocation across mesh topologies
- [x] Address sidecar proxy integration for QKD key consumption

---

### Milestone 3 — Key Management & Vendor Analysis

**Key Management**
- [x] Document ETSI GS QKD 014 API endpoints (enc_keys, dec_keys, status)
- [x] Cover key ID lifecycle: generation, storage, delivery, expiry
- [x] Address trusted-node relay models for extending QKD range
- [x] Document hybrid key derivation (HKDF combining QKD + PQC output)
- [x] Cover key freshness, rotation intervals, and entropy accounting

**Vendor Analysis**
- [x] Profile Toshiba: DV-QKD hardware, DWDM co-existence specs, fiber range
- [x] Profile ID Quantique / IonQ: Cerberis XG platform, IonQ acquisition context
- [x] Profile QuantumCTek: China national QKD backbone specs
- [x] Profile LuxQuanta: CV-QKD, telecom component compatibility
- [x] Profile Q*Bird: MDI-QKD, cross-border deployment
- [x] Profile QuintessenceLabs: QKD + QRNG + key management integration
- [x] Profile IBM: PQC standards leadership, CRYSTALS-Kyber/Dilithium
- [x] Profile Lockheed Martin: defense integration, QuintessenceLabs partnership
- [x] Document operational constraints: distance limits, infrastructure requirements, cost, failure modes, certification gaps

---

### Milestone 4 — Working Implementation

**BB84 Simulator (`bb84_simulator.py`) — IBM Qiskit Backend**
- [x] Simulate qubit exchange using Qiskit quantum circuits (X/H gates) on Aer simulator
- [x] Model channel noise via Qiskit Aer depolarizing error on identity gates
- [x] Model intercept-resend eavesdropper as two sequential quantum circuits
- [x] Implement basis sifting and raw key generation
- [x] Implement QBER estimation with configurable noise threshold
- [x] Implement error correction (Cascade-style reconciliation)
- [x] Implement privacy amplification (hash-based key compression)
- [x] Demonstrate eavesdropper detection: abort when QBER exceeds threshold
- [x] Output deterministic 256-bit symmetric key
- [x] Dual-backend support: `qiskit` (default) and `classical` fallback

**KME Server (`kme_server.py`)**
- [x] Implement ETSI GS QKD 014 REST endpoints: `/enc_keys`, `/dec_keys`, `/status`
- [x] Back key store with BB84 simulator output
- [x] Implement background key refill as keys are consumed
- [x] Assign and track unique key IDs
- [x] Validate SAE identity on key requests

**TLS PSK Demo (`tls_psk_demo.py`)**
- [x] Alice fetches key from KME `/enc_keys` endpoint
- [x] Alice transmits key_ID to Bob out-of-band
- [x] Bob fetches matching key from KME `/dec_keys` endpoint
- [x] Alice encrypts message with AES-256-GCM using QKD-derived key
- [x] Bob decrypts and verifies — no classical key agreement used
- [x] Run end-to-end successfully in two-terminal demo

**IKEv2 PPK Config Guide (`ikev2_ppk_config.md`)**
- [x] Document strongSwan `ppk_id` and `ppk` configuration fields
- [x] Map KME key fetch to PPK provisioning workflow
- [x] Provide example ipsec.conf / swanctl.conf snippets for RFC 8784 PPK

---

### Milestone 5 — Integration, Testing & Final Deliverables

- [x] Cross-reference all documentation against implementation components
- [x] Verify `python tls_psk_demo.py client/server` runs end-to-end without errors
- [x] Confirm BB84 simulator correctly aborts on simulated eavesdropper scenario
- [x] Produce capstone brief (`DOCS/capstone-brief.md`)
- [x] Produce vocab study guide (`DOCS/vocab-study-guide.md`)
- [x] Complete reference list (`08-references/08-references.md`)
- [ ] Final presentation preparation

---

## 4. Technology Stack

### Languages

| Language | Version | Usage |
|----------|---------|-------|
| Python | 3.10+ | BB84 simulator, KME server, PSK demo |
| Markdown | — | All documentation (8 documents + guides) |

### Libraries & Frameworks

| Library | Version | Usage |
|---------|---------|-------|
| Qiskit | 2.x | IBM quantum circuit construction and transpilation (`bb84_simulator.py`) |
| Qiskit Aer | 0.17.x | Quantum circuit simulation with depolarizing noise model |
| Flask | 3.x | ETSI GS QKD 014 REST API server (`kme_server.py`) |
| requests | 2.x | HTTP client for KME key fetch in PSK demo |
| cryptography | 42.x | AES-256-GCM encryption, HKDF key derivation |
| hashlib | stdlib | SHA-256 / SHA-3 for privacy amplification |
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
| IBM Qiskit / Aer | Quantum circuit simulator backend for BB84 protocol |
| strongSwan | IKEv2/IPsec VPN software referenced in PPK configuration guide |
| Git / GitHub | Version control |
| VS Code | Primary editor |
| macOS | Development OS |
| curl | Manual API testing against KME server |

### AI / Research Assistance

| Tool | Usage |
|------|-------|
| GitHub Copilot | Code generation assistance for implementation files |
| Claude (Anthropic) | Research synthesis and documentation drafting |
