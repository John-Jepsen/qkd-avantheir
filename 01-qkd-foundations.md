# QKD Foundations

## 1. Introduction and Background

Quantum Key Distribution (QKD) establishes shared symmetric keys using quantum-mechanical effects. It targets **information-theoretic secrecy** under standard assumptions:

1. Correctly implemented QKD system
2. Authenticated classical channel (without classical-channel authentication, MITM breaks the system even if the quantum channel detects disturbance)

### BB84 Protocol (Bennett-Brassard 1984)

The best-known protocol is BB84, a discrete-variable (DV) scheme where:

- Single photons encode random basis/state choices
- Interception disturbs quantum states
- Disturbance raises the Quantum Bit Error Rate (QBER)
- Alice and Bob use QBER to bound eavesdropper's information
- Resulting shared key becomes input to classical symmetric cryptography (typically AES-based AEAD)

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

## 2. Discrete-Variable vs Continuous-Variable QKD

### DV-QKD (Baseline for this initiative)

| Aspect | Description |
|--------|-------------|
| Encoding | Discrete quantum properties (polarization, phase, time-bin) |
| Detection | Single-photon detectors (APDs, SNSPDs) |
| Maturity | Common in deployed products |
| Security analysis | Long-standing, well-understood |

### CV-QKD (Include only where uniquely advantageous)

| Aspect | Description |
|--------|-------------|
| Encoding | Continuous quadratures of light |
| Detection | Homodyne/heterodyne detection |
| Alignment | Strong alignment with telecom components |
| Performance | Often higher raw rates at short distances in lab/metro |

**Both face identical integration challenges:**
- Key delivery into classical protocol stacks
- Key coordination between endpoints
- Operational constraints
- System security beyond the quantum channel

## 3. Threat Model and Security Properties

### What QKD Addresses

With large-scale quantum computers as a future risk, classical public-key schemes face compromise:

| Algorithm | Risk |
|-----------|------|
| RSA | Shor's algorithm breaks factoring |
| Finite-field DH | Discrete log vulnerable |
| ECC/ECDHE | Elliptic curve discrete log vulnerable |

QKD provides a path where the shared symmetric secret **does not rely on computational hardness**.

### What QKD Does NOT Address

- Endpoint security (malware, insiders, misconfiguration)
- Side-channel attacks on QKD devices
- Implementation bugs
- Classical channel authentication (still required)

## 4. Key QKD Process Stages

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

## 5. Security Thresholds

| Parameter | Typical Threshold | Notes |
|-----------|------------------|-------|
| QBER | < ~11% (BB84 simplified) | Practical systems target low single digits |
| Key rate | Decreases with distance/noise | Must exceed consumption rate |
| Loss budget | System-dependent | Metro links typically viable |

## References

- Bennett, C.H. and Brassard, G. (1984). [Quantum Cryptography: Public key distribution and coin tossing](https://www.cs.ubc.ca/~hutchins/quantum/crypto/bennett84.pdf)
- Bennett, C.H. et al. (1992). [Experimental quantum cryptography](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.68.3121)
- Ekert, A. (1991). [Quantum cryptography based on Bell's theorem (E91)](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.67.661)
- Lo, Curty, Qi (2012). [Measurement-Device-Independent QKD](https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.130503)
