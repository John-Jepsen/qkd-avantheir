---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  table { font-size: 20px; }
  code { font-size: 20px; }
---

<!-- _paginate: false -->

# Quantum Key Distribution for Enterprise Security

## Integrating QKD into TLS 1.3, IPsec/IKEv2, and Service Mesh Authentication

**John Jepsen — MSCS Capstone**

---

## The Threat: Harvest Now, Decrypt Later

- Adversaries record encrypted traffic **today** and decrypt it once a
  cryptographically relevant quantum computer exists
- Shor's algorithm breaks the key exchange (Diffie-Hellman/ECDHE), not the
  symmetric cipher — AES-256 survives, but the key agreement doesn't
- Any data with a shelf life longer than the quantum timeline is already at risk
- **This makes quantum-safe key exchange an operational concern now, not a
  research topic for later**

---

## Two Answers — Not Either/Or

| | Post-Quantum Cryptography | Quantum Key Distribution |
|---|---|---|
| Security basis | Computational hardness (lattices) | Physics (no-cloning theorem) |
| Deployment | Software upgrade | Dedicated fiber + hardware |
| Range | Unlimited | ~100–500 km per link |
| Maturity | NIST FIPS 203/204/205 finalized | Commercial, certification gaps |
| Cost | Low | High |

**Thesis:** map where each fits — and demonstrate the **hybrid QKD + PQC**
architecture (ETSI TS 104 015) for highest-assurance deployments.

---

## What I Built

1. **Documentation suite** — 8 practitioner documents: protocol foundations,
   TLS/IPsec/mesh integration patterns, key management, 8 vendor profiles,
   operational constraints
2. **Working implementation** — full QKD key-delivery pipeline in Python:
   BB84 on IBM Qiskit → ETSI QKD 014 key server → applications
3. **ML adaptive security layer** — five models in a closed loop behind a
   FastAPI service
4. **Adversarial gym** — co-evolutionary attacker/defender arena with a live
   React dashboard
5. **`qkdsec`** — pip-installable open-source package (ETSI 014 client,
   key-rate proofs, BB84 simulator), released to PyPI

---

## BB84 in 60 Seconds

1. Alice encodes random bits in random bases — implemented as real quantum
   circuits (X/H gates) on the Qiskit Aer simulator
2. Bob measures in his own random bases; they keep only matching-basis bits
   (**sifting**)
3. They sacrifice a sample to estimate the **QBER** (quantum bit error rate)
4. **Eavesdropper detection is physics:** intercept-resend forces ~25% QBER
   from wrong-basis collapse — protocol aborts above the 11% threshold
5. Error correction (Cascade) + privacy amplification → **256-bit shared secret**

No classical key agreement anywhere in the flow.

---

## System Architecture

```
BB84 (Qiskit Aer)  ──►  distillation: sift → QBER → correct → amplify
        │
        ▼
KME — ETSI GS QKD 014 REST API (Flask)
  GET /enc_keys → key_ID + key      POST /dec_keys → key by ID
        │                                   │
        ▼                                   ▼
   Alice (master SAE)  ── key_ID ──►  Bob (slave SAE)
        └────── AES-256-GCM encrypted channel ──────┘
```

- The ETSI 014 interface is **identical** for simulation and real hardware —
  vendor adapters (Toshiba, IDQ, QuintessenceLabs, QuantumCTek) plug in via
  `--upstream-kme`
- Trusted-node XOR relay network extends range beyond a single fiber link

---

## Integration Target 1 — TLS 1.3

- QKD key material maps to **RFC 8446 external PSK** handshake mode
- `psk_dhe_ke` keeps an (EC)DHE contribution alongside the PSK —
  defense-in-depth; `psk_ke` is pure-PSK
- QKD-derived secret enters the HKDF key schedule at the early-secret stage
- Demo: `tls_psk_demo.py` — Alice and Bob fetch the same key from the KME
  and exchange AES-256-GCM traffic with **no Diffie-Hellman**

## Integration Target 2 — IPsec/IKEv2

- **RFC 8784** Post-quantum Preshared Keys: PPK mixed into IKEv2 `SK_d`
- Working strongSwan configuration guide maps KME key fetch → PPK provisioning

---

## Integration Target 3 — Service Mesh

- Short-interval **symmetric rekeying** for service-to-service authentication
- SDN-controlled allocation of QKD key material across mesh topologies
- Sidecar proxies consume keys through the same ETSI 014 REST interface

## Hybrid QKD + PQC (the recommendation)

```
KME key  +  ML-KEM (FIPS 203) shared secret
        └── HKDF-SHA256 ──►  combined secret
```

- ETSI TS 104 015 / RFC 9794 — secure if **either** input remains secure
- Implemented in `hybrid_kdf.py`

---

## ML Adaptive Security Layer

Five models, one closed loop, unified behind FastAPI (`/analyze`):

| Model | Task | Result |
|---|---|---|
| Random Forest | Eavesdrop detection (vs. hard 11% threshold) | 93% accuracy |
| Gradient Boosting | 5-class attack classification | 96% accuracy |
| ARIMA | QBER time-series forecasting | MAE 0.006 |
| GB Regressor | Optimal BB84 parameter tuning | R² = 0.85 |
| Isolation Forest | KME traffic anomaly detection | 86% detection |

Shared 8-feature extraction (`features.py`) keeps train/serve consistent;
physics constraints bound every synthetic sample.

---

## Adversarial Gym

- **DEAP evolutionary arena:** attack strategies evolve against defender
  models, bounded by QKD physics constraints
- Defenders **harden via adversarial retraining** each generation
- Phylogeny tree tracks attack lineage; React + D3 dashboard streams
  evolution live over WebSocket
- Answers the question a static benchmark can't: *does the defense hold
  against an adapting adversary?*

---

## Live Demo

Three terminals + dashboard:

1. `kme_server.py` — ETSI 014 key server, pre-generates 50 BB84 keys
2. `tls_psk_demo.py server` / `client` — QKD-keyed AES-256-GCM exchange
3. `curl /analyze` — clean channel → **SECURE**; eavesdropper → **ABORT**
   (QBER 27%, attack classified as intercept-resend)
4. Adversarial gym dashboard — co-evolution in real time

*(Fallback: recorded run + captured outputs, see demo script)*

---

## Vendor & Operational Reality

- **8 profiles:** Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird,
  QuintessenceLabs, IBM (PQC), Lockheed Martin (defense)
- Distance: ~100 km practical fiber spans; trusted nodes or satellites beyond
- Cost: dedicated dark fiber + cryogenic/SNSPD detectors at the high end
- Certification gap: no FIPS-equivalent for QKD hardware yet — a real
  procurement blocker
- **Where QKD fits today:** fixed high-value links (data-center pairs,
  financial backbones, government) — not general internet traffic

---

## Deliverables & Engineering Practice

- 8-document suite + 245-entry vocabulary study guide + full reference list
- ~20 Python modules; three-terminal reproducible demo
- `qkdsec` published on PyPI — CI matrix (3.10/3.11/3.12), tag-driven
  releases via PyPI Trusted Publishing, versions derived from git tags
- All five milestones complete

---

## Conclusions

1. QKD integrates into existing enterprise protocols **without modifying
   them** — external PSK (TLS), PPK (IKEv2), symmetric rekeying (mesh)
2. ETSI GS QKD 014 is the right abstraction: applications don't care whether
   keys come from simulation or hardware
3. **Hybrid QKD + PQC** is the defensible recommendation — physics and
   mathematics fail independently
4. ML turns a static QBER threshold into an adaptive, attack-aware control
   loop — and survives an evolving adversary

**Questions?**
