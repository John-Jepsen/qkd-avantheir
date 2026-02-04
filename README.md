# QKD Key Infrastructure - Avantheir Initiative

## Overview

This repository contains technical documentation and implementation guidance for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure, replacing classical key exchange (Diffie-Hellman/ECDHE) with QKD-derived symmetric material.

## Scope

| Integration Target | Mechanism | Standard Reference |
|-------------------|-----------|-------------------|
| TLS 1.3 / mTLS | PSK and key-update flows | RFC 8446 |
| IPsec/IKEv2 VPN | RFC 8784 mixed-PSK pattern | RFC 8784 |
| Service-to-service auth | Short-interval symmetric rekeying | ETSI GS QKD 014 |

## Baseline Protocol

**Discrete-Variable QKD (BB84-style)** is the baseline due to deployment realism. CV-QKD included only where it offers unique practical advantage.

## Vendor Anchors

- IBM (foundational research, quantum learning resources)
- Lockheed Martin (defense integration, QuintessenceLabs partnership)

## Document Structure

```
qdk-avantheir/
├── README.md                          # This file
├── 01-qkd-foundations.md              # QKD theory and protocol basics
├── 02-tls-integration.md              # TLS 1.3/mTLS integration patterns
├── 03-ipsec-ikev2-integration.md      # IPsec VPN integration via RFC 8784
├── 04-service-mesh-auth.md            # Service-to-service symmetric rekeying
├── 05-key-management.md               # ETSI API, key lifecycle, trusted nodes
├── 06-vendor-analysis.md              # IBM and Lockheed Martin contributions
├── 07-operational-constraints.md      # Distance, infrastructure, failure modes
├── 08-references.md                   # Full reference list with links
└── implementation/
    ├── etsi-kme-client.py             # Sample ETSI KME client
    ├── tls-psk-adapter.py             # TLS PSK integration adapter
    └── ikev2-ppk-config.md            # IKEv2 PPK configuration guide
```

## Key Contacts

Senior-led research track - treat as deliverable for execution.
