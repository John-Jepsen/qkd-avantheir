# Capstone Project Brief

**Student:** John Jepsen
**Program:** MSCS
**Date:** March 2026

---

## Subject

Quantum Key Distribution (QKD) integration into enterprise network security infrastructure.

## Project

A technical documentation suite, reference architecture, and working implementation that replaces classical key exchange (Diffie-Hellman/ECDHE) with QKD-derived symmetric key material across three enterprise integration targets: TLS 1.3, IPsec/IKEv2 VPN, and service-to-service mesh authentication. The project also evaluates and demonstrates the hybrid QKD + Post-Quantum Cryptography (PQC) approach as the recommended architecture for highest-assurance deployments.

## What I Built

### Documentation (8 documents)

1. **QKD foundations** — protocol variants (BB84, CV-QKD, MDI-QKD, TF-QKD), hardware components, and global deployment landscape
2. **Protocol integration patterns** — concrete mechanisms for TLS 1.3 PSK modes (RFC 8446), IPsec mixed-PSK (RFC 8784), and service mesh symmetric rekeying
3. **Key management architecture** — ETSI QKD 014 API lifecycle, trusted-node models, and hybrid key derivation (ETSI TS 104 015)
4. **Vendor and operational analysis** — profiles of eight QKD/PQC vendors (Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs, IBM, Lockheed Martin) plus distance constraints, cost considerations, and certification gaps

### Working Implementation (`implementation/`)

A runnable Python stack that emulates the full QKD key delivery pipeline:

| Component | File | What it does |
|-----------|------|--------------|
| BB84 simulator | `bb84_simulator.py` | Simulates the complete BB84 protocol — qubit exchange, basis sifting, QBER estimation, error correction, privacy amplification — and outputs a 256-bit shared secret |
| ETSI KME server | `kme_server.py` | REST API implementing ETSI GS QKD 014, backed by the BB84 simulator, dispensing keys to applications via standard endpoints |
| PSK demo | `tls_psk_demo.py` | Alice and Bob each fetch the same key from the KME and use it for AES-256-GCM authenticated encryption — demonstrating the PSK pattern that replaces Diffie-Hellman |
| IKEv2 PPK guide | `ikev2_ppk_config.md` | Step-by-step configuration guide for feeding KME-derived keys into strongSwan as RFC 8784 Post-quantum Preshared Keys |

Running `python tls_psk_demo.py client` in one terminal and `server` in another produces a live end-to-end exchange where no classical key agreement takes place — the shared secret comes entirely from the quantum channel simulation.

## Why This Subject

The "harvest now, decrypt later" threat makes quantum-safe key exchange an active concern for enterprise security teams today, not a future problem. This project maps where QKD, PQC, and hybrid approaches each fit — a question practitioners face now as NIST PQC standards finalize and QKD hardware reaches commercial maturity.
