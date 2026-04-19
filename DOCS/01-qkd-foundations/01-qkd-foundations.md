# QKD Foundations

## 1. Introduction and Background

Quantum Key Distribution (QKD) establishes shared symmetric keys using quantum-mechanical effects. It targets **information-theoretic secrecy** under standard assumptions:

1. Correctly implemented QKD system
2. Authenticated classical channel (without classical-channel authentication, MITM breaks the system even if the quantum channel detects disturbance)

### Why QKD (vs. PQC Alone)

Post-Quantum Cryptography (PQC) — standardized by NIST as FIPS 203/204/205 (August 2024) — provides security based on mathematical hardness conjectures (lattice problems). QKD provides security based on the laws of physics. The distinction matters for:

- Data requiring 50+ year confidentiality (beyond foreseeable computational advances)
- Eavesdropping detection (QBER monitoring detects interception; PQC cannot)
- Defense-in-depth hybrid architectures combining both security models
- Adversary models including unknown future algorithmic breakthroughs

PQC alone is sufficient for most commercial applications. QKD is justified for the highest-value, longest-lived secrets. The strategic choice is not QKD versus PQC, but where to deploy each.

## 2. Core QKD Protocols

### BB84 (Bennett-Brassard, 1984) — Baseline Protocol

Alice encodes random bits using one of two conjugate bases (rectilinear or diagonal polarization). Bob measures in a randomly chosen basis. After transmission, they publicly compare basis choices and discard mismatches (sifting). Remaining correlated bits undergo error correction and privacy amplification to yield a secure shared key.

```
┌─────────┐     Quantum Channel      ┌─────────┐
│  Alice  │ ──────────────────────── │   Bob   │
│         │   (single photons)       │         │
│         │                          │         │
│         │     Classical Channel    │         │
│         │ ──────────────────────── │         │
│         │   (authenticated)        │         │
└─────────┘                          └─────────┘
     │                                    │
     ▼                                    ▼
┌─────────┐                          ┌─────────┐
│   KME   │                          │   KME   │
│(Key Mgmt│                          │(Key Mgmt│
│ Entity) │                          │ Entity) │
└─────────┘                          └─────────┘
```

**Security basis:** The no-cloning theorem prevents an eavesdropper from perfectly copying unknown quantum states. Any measurement by Eve introduces detectable disturbance in the QBER. Security proofs hold against general coherent attacks in both asymptotic and finite-key regimes.

**Key rates:** Commercial systems achieve 1-10 Mbps at metro distances (10-20 km), dropping to low kbps at 100+ km. Toshiba demonstrated 63+ Mbps using multi-pixel SNSPDs over short spans.

**Maximum distances:** ~200-250 km in fiber before key rates become impractical. Limited by the Pirandola-Laurenza-Ottaviani-Banchi (PLOB) repeaterless secret-key capacity bound.

**Known vulnerabilities:** Photon-number splitting (PNS) attacks on multi-photon emissions — mitigated by decoy-state BB84 (now standard in all commercial DV-QKD). Detector blinding attacks manipulate SPDs into classical mode. Trojan horse attacks inject light to probe internal states.

### E91 (Ekert, 1991)

Entangled photon pair source distributes one photon to Alice, one to Bob. Bell inequality violations confirm entanglement and detect eavesdropping. Security is device-independent in principle.

- **Key rates:** 100 bps to low kbps at metro distances
- **Max distance:** ~1,200 km via satellite (Micius demonstration)
- **Status:** Research/limited commercial availability

### Continuous-Variable QKD (CV-QKD)

Encodes key information in continuous quadratures (amplitude and phase) of coherent light. Detection uses standard homodyne/heterodyne receivers instead of single-photon detectors.

| Aspect | Description |
|--------|-------------|
| Encoding | Continuous quadratures of light |
| Detection | Homodyne/heterodyne (standard telecom coherent receivers) |
| Key rates | 18.93 Mbps at 25 km (2024-25), competitive with DV-QKD |
| Max distance | 120 km co-existing with fully populated CWDM traffic (2025) |
| Cost advantage | Uses entirely standard telecom components |
| Commercial status | LuxQuanta NOVA LQ (2nd gen, March 2025); DE-QOR project (Germany) |

**Security basis:** Heisenberg uncertainty principle. Security proofs exist against collective and general attacks; finite-size analyses maturing rapidly.

**Known vulnerabilities:** Local oscillator attacks (mitigated by locally generated LO designs), excess noise in co-propagation, finite-size effects reducing practical security margins.

### Measurement-Device-Independent QKD (MDI-QKD)

Both Alice and Bob send quantum states to an untrusted central relay (Charlie) that performs a Bell-state measurement. Charlie never learns the key bits. **Eliminates all detector-side attacks by design.**

| Aspect | Description |
|--------|-------------|
| Max distance | 303 km with flawed state preparation (2025) |
| Multi-user rates | 267 bps per user pair at ~30 dB using optical frequency combs (Jan 2025) |
| Deployment milestone | Q*Bird: first cross-border MDI-QKD link in Europe (Belgium-Luxembourg, 132 km, June 2025) |
| Commercial product | Q*Bird Falqon Series |

### Twin-Field QKD (TF-QKD)

Alice and Bob send phase-encoded weak coherent pulses to an untrusted central node performing single-photon interference. Key rates scale as the **square root** of channel transmittance — overcoming the PLOB bound without quantum repeaters.

| Aspect | Description |
|--------|-------------|
| World record | 1,002 km fiber (USTC, May 2023) using ultra-low-loss fiber (0.16 dB/km) |
| Key rate at record | 0.0034 bps (lab demonstration) |
| Practical advantage | Significantly higher rates than standard protocols at equivalent loss |
| Status | Pre-commercial; requires precise inter-laser phase stabilization |

### Protocol Comparison Summary

| Protocol | Max Distance (Fiber) | Typical Key Rate (Metro) | Security Model | Commercial Availability |
|----------|---------------------|-------------------------|----------------|------------------------|
| BB84 (decoy-state) | ~250 km | 1-10 Mbps @ 20 km | IT security (proven) | Widely available |
| E91 | ~1,200 km (satellite) | 100 bps - low kbps | Device-independent (theory) | Research/limited |
| CV-QKD | 120 km | 18.93 Mbps @ 25 km | IT security (proofs maturing) | LuxQuanta, others |
| MDI-QKD | 303 km | 267 bps @ 30 dB | Removes detector attacks | Q*Bird Falqon |
| TF-QKD | 1,002 km (lab) | Higher than BB84 at equiv. loss | Overcomes PLOB bound | Pre-commercial |

## 3. DV-QKD vs CV-QKD for Deployment

### DV-QKD (Baseline for this initiative)

| Aspect | Description |
|--------|-------------|
| Encoding | Discrete quantum properties (polarization, phase, time-bin) |
| Detection | Single-photon detectors (SPADs, SNSPDs) |
| Maturity | Common in deployed products (Toshiba, ID Quantique, QuantumCTek) |
| Security analysis | Long-standing, well-understood, finite-key proofs mature |

### CV-QKD (Include where cost/integration advantages apply)

| Aspect | Description |
|--------|-------------|
| Encoding | Continuous quadratures of light |
| Detection | Homodyne/heterodyne (standard telecom coherent receivers) |
| Cost advantage | No single-photon detectors, no cryogenics |
| Integration | Plug-and-play addition to existing metro optical networks |
| Commercial leader | LuxQuanta (NOVA LQ), DE-QOR project |

**Both face identical integration challenges** into classical protocol stacks — the QKD-to-application interface (ETSI GS QKD 014) is protocol-agnostic.

## 4. QKD Hardware Components

### Single-Photon Sources

Practical QKD systems use attenuated laser pulses (weak coherent pulses) with decoy-state protocols. Quantum dot single-photon sources are progressing in research but not standard commercially. Entangled photon pair sources (SPDC) serve entanglement-based protocols.

### Single-Photon Detectors

**SPADs (Single-Photon Avalanche Diodes):** InGaAs/InP, 10-25% detection efficiency, no cryogenics for gated operation, lower cost. Used in most commercial QKD systems.

**SNSPDs (Superconducting Nanowire Single-Photon Detectors):** >90% efficiency, ultra-low dark counts (~0.01-1 cps), <15 ps timing jitter. Require cryogenic cooling (~2.5 K). Critical for long-distance and high-rate QKD. Market projected to reach $45.39M by 2030.

**Key detector vendors:** ID Quantique/IonQ (SPADs and SNSPDs), Single Quantum (multi-channel SNSPDs, >90% efficiency), Pixel Photonics (waveguide-integrated SNSPDs).

### Quantum Random Number Generators (QRNGs)

Essential for generating random basis choices and bit values. Commercial products: ID Quantique/IonQ Quantis series, QuintessenceLabs qStream.

## 5. Threat Model and Security Properties

### What QKD Addresses

With large-scale quantum computers as a future risk, classical public-key schemes face compromise:

| Algorithm | Risk | Timeline |
|-----------|------|----------|
| RSA-2048 | Shor's algorithm breaks factoring | CRQC emergence (~2035 central estimate) |
| ECDH/ECDSA | Elliptic curve discrete log | Same |
| Finite-field DH | Discrete log vulnerable | Same |

**Harvest Now, Decrypt Later (HNDL):** Adversaries collect encrypted data today for future quantum decryption. Acknowledged as active by DHS, NCSC, ENISA, and Australian CSC.

QKD provides a path where the shared symmetric secret **does not rely on computational hardness** — immune to future mathematical and computational advances.

### What QKD Does NOT Address

- Endpoint security (malware, insiders, misconfiguration)
- Side-channel attacks on QKD devices (gap between theory and implementation)
- Implementation bugs
- Classical channel authentication (still required)
- Digital signatures (QKD provides key agreement only)

### NSA Position

NSA does not recommend QKD for National Security Systems and mandates CNSA 2.0 (PQC) transition. However, EU, UK, China, South Korea, and Japan invest heavily in QKD, creating strategic divergence. Hybrid QKD+PQC architectures satisfy both CNSA 2.0 compliance and physics-based security.

## 6. Key QKD Process Stages

```
Raw Key Exchange
       │
       ▼
┌──────────────┐
│   Sifting    │  Discard mismatched basis measurements
└──────────────┘
       │
       ▼
┌──────────────┐
│    Error     │  Estimate and correct errors
│  Correction  │  (reveals some information)
└──────────────┘
       │
       ▼
┌──────────────┐
│   Privacy    │  Hash to remove Eve's potential
│ Amplification│  information
└──────────────┘
       │
       ▼
   Final Key
   (shared secret)
```

## 7. Security Thresholds

| Parameter | Typical Threshold | Notes |
|-----------|------------------|-------|
| QBER | < ~11% (BB84 simplified) | Practical systems target low single digits |
| Key rate | Decreases with distance/noise | Must exceed consumption rate |
| Loss budget | System-dependent | Metro links (<50 km) generally viable |

## 8. QKD Network Architectures

### Point-to-Point Links

Direct quantum channel between two endpoints. Most commercial deployments today. Key rates depend on distance and channel loss.

### Trusted-Node Networks (Multi-Hop)

```
┌───────┐      ┌───────┐      ┌───────┐      ┌───────┐
│ End A │◄────►│Trust 1│◄────►│Trust 2│◄────►│ End B │
└───────┘      └───────┘      └───────┘      └───────┘
    │              │              │              │
    │   QKD Link   │   QKD Link   │   QKD Link   │
    └──────────────┴──────────────┴──────────────┘
```

Each hop runs QKD independently. Intermediate nodes see key material during relay — security depends on physical security at every node. This is the architecture of China's 12,000+ km backbone and most current long-distance networks.

### Satellite-Based QKD

Overcomes fiber distance limitations via free-space optical links. LEO satellites distribute keys to ground stations separated by thousands of km.

| Program | Status | Notable |
|---------|--------|---------|
| Micius (China) | Operational since 2016 | 12,800 km Beijing-South Africa link (2025); constellation planned 2027 |
| Eagle-1 (EU/ESA) | Launch 2026 | First European QKD satellite demonstrator; EuroQCI integration |
| QEYSSat (Canada) | Launch late 2026 | ~100 kg microsatellite for ground-to-space QKD |

### Quantum Repeaters (Future)

True quantum repeaters would enable end-to-end entanglement distribution without trusted nodes. Current state: proof-of-concept. AWS-Harvard demonstrated entanglement across 35 km of deployed fiber in Boston (2024). Field-deployable systems estimated 2033-2040.

## 9. Current Global QKD Deployments

| Network | Country/Region | Scale | Status (2025-26) |
|---------|---------------|-------|-------------------|
| CN-QCN + BSBN | China | 12,000+ km, 80 cities, 145 nodes | Operational, carrier-grade |
| EuroQCI (terrestrial) | EU-27 | Cross-border links deploying | Transitioning to operational |
| Eagle-1 (satellite) | EU/ESA | LEO QKD demonstrator | Launch 2026 |
| Romania QKD | Romania/EU | 1,500 km, 36 links (IonQ/IDQ) | Operational |
| Chicago Quantum Exchange | USA | 84 km testbed | Operational testbed |
| IEQNET | USA | Multi-node, Chicago area | Research operational |
| Tokyo QKD | Japan | Metro network (NICT) | Operational testbed |

## References

- Bennett, C.H. and Brassard, G. (1984). [Quantum Cryptography: Public key distribution and coin tossing](https://www.cs.ubc.ca/~hutchins/quantum/crypto/bennett84.pdf)
- Bennett, C.H. et al. (1992). [Experimental quantum cryptography](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.68.3121)
- Ekert, A. (1991). [Quantum cryptography based on Bell's theorem (E91)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.67.661)
- Lo, Curty, Qi (2012). [Measurement-Device-Independent QKD](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.130503)
- [Experimental TF-QKD over 1000 km - PRL](https://link.aps.org/doi/10.1103/PhysRevLett.130.210801)
- [MDI-QKD network with optical frequency combs - npj QI](https://www.nature.com/articles/s41534-025-01052-7)
- [Q*Bird cross-border MDI-QKD](https://q-bird.com/press/fortifying-europes-quantum-communication-qbird-and-beqci-achieve-the-first-cross-border-mdi-qkd-link-in-benelux/)
- [CV-QKD coexistence 120 km - PRL](https://link.aps.org/doi/10.1103/zy2d-m3ch)
- [Carrier-grade QKD over 10,000 km - npj QI](https://www.nature.com/articles/s41534-025-01089-8)
- [NIST PQC Standards (Aug 2024)](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards)
