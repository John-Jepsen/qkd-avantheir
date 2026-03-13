# QKD Key Infrastructure - Avantheir Initiative

## Overview

This repository contains technical documentation and implementation guidance for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure, replacing classical key exchange (Diffie-Hellman/ECDHE) with QKD-derived symmetric material.

![QKD System Architecture](images/qkd-system-diagram.png)

## Scope

| Integration Target | Mechanism | Standard Reference |
|-------------------|-----------|-------------------|
| TLS 1.3 / mTLS | PSK and key-update flows | RFC 8446 |
| IPsec/IKEv2 VPN | RFC 8784 mixed-PSK pattern | RFC 8784 |
| Service-to-service auth | Short-interval symmetric rekeying | ETSI GS QKD 014 |
| Hybrid QKD+PQC | Combined key derivation | ETSI TS 104 015, IETF RFC 9794 |

## Baseline Protocol

**Discrete-Variable QKD (BB84-style)** is the baseline due to deployment realism. CV-QKD is included where it offers unique practical advantage (metro cost, telecom compatibility). MDI-QKD and TF-QKD are covered for their security and distance properties.

## Vendor Coverage

### Tier 1 — Established Commercial QKD Vendors

- **Toshiba** (Japan/UK) — High-performance DV-QKD, 33.4 Tbps DWDM co-existence, cross-state fiber demonstrations
- **ID Quantique / IonQ** (Switzerland/USA) — Commercial DV-QKD market leader, Cerberis XG platform, acquired by IonQ for $250M (Feb 2025)
- **QuantumCTek** (China) — Powers China's 12,000+ km national QKD backbone across 80 cities

### Tier 2 — Growing Commercial Players

- **LuxQuanta** (Spain) — CV-QKD systems using standard telecom components (NOVA LQ platform)
- **Q*Bird** (Netherlands) — MDI-QKD solutions (Falqon Series), first cross-border MDI-QKD in Europe
- **QuintessenceLabs** (Australia) — QKD + QRNG + key management platform, Lockheed Martin strategic investment

### Research & Integration Anchors

- **IBM** — Foundational BB84 research heritage, PQC leadership (CRYSTALS-Kyber/Dilithium)
- **Lockheed Martin** — Defense systems integration, QuintessenceLabs partnership

## Document Structure

```
qkd-avantheir/
├── README.md                          # This file
├── 01-qkd-foundations.md              # QKD protocols, hardware, architectures, global deployments
├── 02-tls-integration.md              # TLS 1.3/mTLS integration patterns (PSK + hybrid)
├── 03-ipsec-ikev2-integration.md      # IPsec VPN integration via RFC 8784
├── 04-service-mesh-auth.md            # Service-to-service symmetric rekeying
├── 05-key-management.md               # ETSI API, key lifecycle, trusted nodes, hybrid models
├── 06-vendor-analysis.md              # Vendor profiles (Toshiba, IDQ/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QLabs, IBM, LM)
├── 07-operational-constraints.md      # Distance, infrastructure, cost, failure modes, certification gaps
├── 08-references.md                   # Full reference list with links
└── implementation/
    ├── etsi-kme-client.py             # Sample ETSI KME client
    ├── tls-psk-adapter.py             # TLS PSK integration adapter
    └── ikev2-ppk-config.md            # IKEv2 PPK configuration guide
```

## Key Contacts

Senior-led MSCS research track — treat as deliverable for execution.
