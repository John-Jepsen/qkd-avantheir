# QKD Vocabulary Study Guide

A comprehensive study reference for all technical terms across the Avantheir QKD project.

---

## QKD Protocols & Variants

| Term | Definition |
|------|-----------|
| **BB84** | Bennett-Brassard 1984. Baseline discrete-variable QKD protocol using conjugate polarization bases (rectilinear + diagonal). Foundation of modern QKD. |
| **E91** | Ekert 1991. Entanglement-based QKD using Bell inequality violations to detect eavesdropping. |
| **DV-QKD** | Discrete-Variable QKD. Encodes keys in discrete quantum properties (polarization, phase, time-bin); uses single-photon detectors. |
| **CV-QKD** | Continuous-Variable QKD. Encodes keys in amplitude and phase quadratures of coherent light; uses homodyne/heterodyne receivers instead of single-photon detectors. |
| **MDI-QKD** | Measurement-Device-Independent QKD. Both parties send states to an untrusted central relay performing Bell-state measurement; eliminates all detector-side attacks. |
| **TF-QKD** | Twin-Field QKD. Phase-encoded weak coherent pulses sent to an untrusted node with single-photon interference. Key rates scale as √transmittance, overcoming the PLOB bound. |
| **Decoy-state BB84** | Enhanced BB84 using decoy-state protocols (varying pulse intensities) to detect photon-number splitting attacks. Now standard in all commercial DV-QKD. |
| **Device-independent QKD** | Theoretical protocol providing security without trusting the measurement apparatus at all. |

---

## Physics & Math Foundations

| Term | Definition |
|------|-----------|
| **No-cloning theorem** | Quantum principle: unknown quantum states cannot be perfectly copied. Fundamental basis of QKD security. |
| **Heisenberg uncertainty principle** | Measuring one quantum observable disturbs the conjugate observable. Underlies CV-QKD security. |
| **Bell inequality violations** | Statistical test proving entanglement between particles. Used in E91 for eavesdropping detection. |
| **Information-theoretic security** | Security guaranteed by laws of physics, not by computational difficulty. QKD's key advantage over PQC. |
| **Computational hardness** | Security based on conjectured difficulty of math problems (e.g., factoring, discrete log). Basis of classical and PQC crypto. |
| **QBER** | Quantum Bit Error Rate. Fraction of sifted key bits with errors; indicates potential eavesdropping. Threshold: <11% for BB84; practical systems target low single digits. |
| **PLOB bound** | Pirandola-Laurenza-Ottaviani-Banchi bound. Theoretical limit on key rates in direct fiber without quantum repeaters. TF-QKD overcomes it via square-root scaling. |
| **Shor's algorithm** | Quantum algorithm that breaks RSA and elliptic curve crypto in polynomial time. Primary motivation for quantum-safe cryptography. |
| **Grover's algorithm** | Quantum algorithm giving quadratic speedup on unstructured search. Effectively halves symmetric key strength (AES-256 → 128-bit security). |
| **LWE** | Learning with Errors. Lattice-based hardness problem underlying ML-KEM (CRYSTALS-Kyber) security. |
| **Photon transmission probability** | Exponential decay with fiber distance (~0.2 dB/km telecom fiber). Every ~15 km roughly halves transmission. |

---

## Key Processing Stages

| Term | Definition |
|------|-----------|
| **Sifting** | Discard measurements where Alice and Bob chose different bases; keep only matching-basis results. |
| **Error correction** | Estimate and correct bit errors in the sifted key. Reveals some information to a potential eavesdropper. |
| **Privacy amplification** | Final stage: hash the corrected key to remove any information Eve may have gained. Produces the final secure key. |

---

## Cryptographic Standards & RFCs

| Standard | What It Covers |
|----------|---------------|
| **RFC 8446** | TLS 1.3 specification. Defines PSK modes used for QKD integration. |
| **RFC 8784** | IKEv2 Post-quantum Preshared Key (PPK). Mixes additional preshared key material into IKEv2 derivation. |
| **RFC 9794** | Hybrid cryptography terminology (June 2025). |
| **RFC 7296** | Base IKEv2 specification. |
| **RFC 4301** | IPsec architecture. |
| **FIPS 203** | ML-KEM (CRYSTALS-Kyber). NIST post-quantum key encapsulation mechanism. |
| **FIPS 204** | ML-DSA (CRYSTALS-Dilithium). NIST post-quantum digital signature standard. |
| **FIPS 205** | SLH-DSA (SPHINCS+). NIST post-quantum hash-based signature standard. |
| **CNSA 2.0** | NSA's Commercial National Security Algorithm Suite. Mandates ML-KEM, ML-DSA, AES-256 for post-quantum transition (2030 equipment, 2033 exclusive). |
| **ETSI GS QKD 004** | QKD application interface standard. |
| **ETSI GS QKD 008** | QKD quality of service standard. |
| **ETSI GS QKD 014** | REST key delivery API. Primary interface for KME-to-SAE communication. |
| **ETSI GS QKD 015** | QKD security proofs standard. |
| **ETSI GS QKD 016** | QKD security evaluation methodology (limited adoption). |
| **ETSI TS 104 015** | Hybrid key exchanges with KEMAC (Feb 2025). |
| **ITU-T Y.3800 / Y.3801** | QKD network overview and functional requirements. |

---

## Network & Security Protocols

| Term | Definition |
|------|-----------|
| **TLS 1.3** | Transport Layer Security 1.3. Current standard for securing web/application traffic. |
| **IPsec** | Internet Protocol Security. Layer 3 encryption for VPNs and site-to-site links. |
| **IKEv2** | Internet Key Exchange v2. Establishes Security Associations for IPsec tunnels. |
| **mTLS** | Mutual TLS. Both client and server authenticate with certificates. |
| **PSK** | Pre-Shared Key. Symmetric key agreed before the TLS handshake. QKD delivers PSK material to TLS stacks. |
| **PSK-only mode** | TLS using only PSK for key derivation. No forward secrecy. |
| **PSK + (EC)DHE** | TLS mixing PSK with ephemeral Diffie-Hellman. Recommended for QKD — preserves forward secrecy. |
| **PSK + ML-KEM + (EC)DHE** | Hybrid mode combining QKD-PSK, post-quantum KEM, and classical ECDHE. Strongest option. |
| **ECDHE** | Elliptic Curve Diffie-Hellman Ephemeral. Classical key agreement providing forward secrecy. |
| **PPK** | Post-quantum Preshared Key (RFC 8784). Mechanism for mixing QKD key material into IKEv2. |
| **SDN** | Software-Defined Networking. Enables dynamic QKD key allocation and routing via centralized control plane. |
| **DWDM** | Dense Wavelength Division Multiplexing. Many wavelengths on one fiber. Toshiba demonstrated 33.4 Tbps co-existence with QKD. |
| **CWDM** | Coarse Wavelength Division Multiplexing. LuxQuanta CV-QKD co-exists over 120 km. |

---

## Key Management (ETSI Architecture)

| Term | Definition |
|------|-----------|
| **KME** | Key Management Entity. Holds QKD-distilled key material, serves keys to applications via ETSI 014 REST API. |
| **SAE** | Secure Application Entity. Application that consumes keys from the KME. |
| **Key ID** | Identifier for a key block enabling coordination between peers. |
| **Key buffer** | Storage for distilled QKD key material prior to issuance. |
| **Key lifecycle states** | CREATED → INDEXED → ISSUED → CONFIRMED → EXPIRED → ERASED |
| **Key rotation** | Regular replacement of active keys. Typical interval: 5–300 seconds in service mesh. |
| **Key epoch** | Logical grouping of keys by rotation cycle (epoch 1, 2, 3…). |
| **Grace period** | Transition window where both old and new keys are valid during rotation. |
| **Key mixing** | Combining QKD + PQC + classical keys: `Final_Key = KDF(QKD ‖ PQC ‖ Classical ‖ Context)` |
| **KEMAC** | Key Encapsulation Mechanism with Authentication Code. ETSI TS 104 015 hybrid exchange method. |
| **One-time use keys** | Keys retrievable only once from KME (highest security model). |
| **Zeroization** | Secure erasure of key material after use. |

---

## Hardware & Components

| Term | Definition |
|------|-----------|
| **SPAD** | Single-Photon Avalanche Diode. InGaAs/InP detector; 10–25% efficiency; no cryogenics needed. Widely used in commercial QKD. |
| **SNSPD** | Superconducting Nanowire Single-Photon Detector. >90% efficiency, ultra-low dark counts, <15 ps jitter. Requires cryogenic cooling (~2.5 K). |
| **Weak coherent pulses** | Attenuated laser pulses with Poisson photon statistics. Practical QKD systems use these instead of true single-photon sources. |
| **SPDC** | Spontaneous Parametric Down-Conversion. Generates entangled photon pairs for E91-type protocols. |
| **Homodyne detection** | Coherent detection using local oscillator interference. Used in CV-QKD. |
| **Heterodyne detection** | Alternative coherent detection measuring both quadratures simultaneously. Used in CV-QKD. |
| **Local Oscillator (LO)** | Reference light beam for coherent detection in CV-QKD systems. |
| **QRNG** | Quantum Random Number Generator. Hardware source for quantum-certified randomness. |
| **Photonic integrated circuits** | On-chip optical components for cost reduction in QKD systems. |

---

## Attack Vectors & Threats

| Term | Definition |
|------|-----------|
| **HNDL** | Harvest Now, Decrypt Later. Adversary collects encrypted data today to decrypt with future quantum computers. Acknowledged as active threat by DHS, NCSC, ENISA. |
| **CRQC** | Cryptographically Relevant Quantum Computer. Hypothetical future quantum computer capable of breaking classical public-key crypto (~2035 central estimate). |
| **PNS attack** | Photon-Number Splitting. Exploits multi-photon emissions in weak coherent pulses. Mitigated by decoy-state protocols. |
| **Detector blinding** | Bright light forces single-photon detectors into classical mode, completely breaking DV-QKD security. |
| **Trojan horse attack** | Injects light to probe internal QKD system states. |
| **Side-channel attacks** | Exploit implementation gaps between theoretical proofs and real systems. Most frequently cited QKD criticism. |
| **LO attacks** | Exploits the local oscillator in CV-QKD. Mitigated by locally-generated LO designs. |
| **Endpoint compromise** | Breach at the application level — QKD cannot prevent this. |

---

## Architecture & Deployment

| Term | Definition |
|------|-----------|
| **Point-to-point QKD link** | Direct quantum channel between two endpoints. Most common commercial deployment. |
| **Trusted-node network** | Multi-hop architecture where intermediate nodes relay keys. Security depends on physical security at each node. |
| **Quantum repeaters** | Future technology enabling end-to-end entanglement without trusted nodes. Field-deployable estimated 2033–2040. |
| **Satellite QKD** | Free-space optical QKD from orbiting platforms. Overcomes fiber distance limits. |
| **Dark fiber** | Dedicated fiber not multiplexed with other traffic. Historically required for QKD; now DWDM co-existence is proven. |
| **Service mesh** | Microservice infrastructure layer (e.g., Envoy proxy) for inter-service security. |
| **Pairwise service keys** | Unique keys between each service pair (A↔B, A↔C, B↔C). |
| **Group service keys** | Shared epoch keys across a trust group. Simpler but higher breach impact. |
| **Forward secrecy** | Compromising long-term keys doesn't compromise past sessions. Maintained via (EC)DHE in QKD-TLS hybrid mode. |
| **Defense in depth** | Multiple independent protective layers. Core argument for hybrid QKD+PQC. |
| **Fail-closed** | Reject connections when QKD is unavailable (security over availability). |

### Distance Tiers

| Range | Distance | Key Rate | Status |
|-------|----------|----------|--------|
| Metro | <50 km | Mbps | Production-ready |
| Regional | 50–100 km | kbps–low Mbps | Careful engineering |
| Long-haul | 100–300 km | bps–low kbps | Marginal feasibility |
| Ultra-long | 300–1000+ km | Sub-bps (lab) | Requires TF-QKD or trusted nodes |

---

## Vendors & Organizations

| Vendor | Headquarters | Specialty |
|--------|-------------|-----------|
| **Toshiba** | Cambridge, UK | High-performance DV-QKD, DWDM co-existence |
| **ID Quantique (IDQ)** | Geneva, Switzerland | First commercial QKD vendor (2001). Acquired by IonQ Feb 2025 for $250M. Cerberis XG, Quantis QRNG. |
| **IonQ** | US | Trapped-ion quantum computing; acquired IDQ for computing + networking convergence. |
| **QuantumCTek** | Anhui, China | Primary vendor for China's national QKD network (CN-QCN). Largest deployed QKD infrastructure globally. |
| **LuxQuanta** | Barcelona, Spain | CV-QKD specialist. NOVA LQ uses standard telecom components, no cryogenics. |
| **Q*Bird** | Delft, Netherlands | MDI-QKD specialist (QuTech/TU Delft spin-off). Falqon Series product. |
| **QuintessenceLabs** | Canberra, Australia | Integrated QKD + QRNG + key management platform. Lockheed Martin investor. |
| **IBM** | US | Historical (BB84 co-inventor, first experimental QKD 1992). Current focus: PQC (Kyber/Dilithium). |
| **Lockheed Martin** | US | Defense integration, ruggedization, accreditation pathways. Strategic investor in QuintessenceLabs. |

### Standards Bodies

| Organization | Role |
|-------------|------|
| **NIST** | PQC standards (FIPS 203-205), quantum information guidance |
| **NSA** | CNSA 2.0 mandate; recommends PQC-first, does not endorse QKD |
| **ETSI** | Primary QKD standards body (QKD ISG) |
| **ITU-T** | QKD network standards (Y.3800 series) |
| **NATO** | Quantum Technologies Strategy (Jan 2024); DISCRETION project |

---

## Major Deployment Programs

| Program | Scope | Status |
|---------|-------|--------|
| **CN-QCN** | China: 12,000+ km, 80 cities, 145 nodes | Operational |
| **BSBN** | Beijing–Shanghai backbone: 2,000+ km | Operational since 2016 |
| **EuroQCI** | All 27 EU member states + ESA | Target operational 2030 |
| **Eagle-1** | EU/ESA LEO QKD satellite | Launch 2026 |
| **QEYSSat** | Canadian Space Agency QKD microsatellite | Launch late 2026 |
| **Micius** | Chinese satellite QKD | Operational since 2016; 12,800 km link achieved 2025 |
| **DISCRETION** | NATO military CV-QKD project | Active |
| **Romania network** | 1,500 km, 36 links (IonQ/IDQ) | 2025 |

---

## Key Acronyms (Quick Reference)

| Acronym | Expansion |
|---------|-----------|
| QKD | Quantum Key Distribution |
| PQC | Post-Quantum Cryptography |
| TLS | Transport Layer Security |
| IPsec | Internet Protocol Security |
| IKEv2 | Internet Key Exchange v2 |
| PSK | Pre-Shared Key |
| ECDHE | Elliptic Curve Diffie-Hellman Ephemeral |
| KME | Key Management Entity |
| SAE | Secure Application Entity |
| QBER | Quantum Bit Error Rate |
| SPAD | Single-Photon Avalanche Diode |
| SNSPD | Superconducting Nanowire Single-Photon Detector |
| QRNG | Quantum Random Number Generator |
| HNDL | Harvest Now, Decrypt Later |
| CRQC | Cryptographically Relevant Quantum Computer |
| PLOB | Pirandola-Laurenza-Ottaviani-Banchi (capacity bound) |
| DWDM | Dense Wavelength Division Multiplexing |
| SDN | Software-Defined Networking |
| PPK | Post-quantum Preshared Key |
| ML-KEM | Module-Lattice Key Encapsulation Mechanism |
| ML-DSA | Module-Lattice Digital Signature Algorithm |
| CNSA | Commercial National Security Algorithm Suite |
| ETSI | European Telecommunications Standards Institute |
| FIPS | Federal Information Processing Standard |
| LWE | Learning with Errors |
| SPDC | Spontaneous Parametric Down-Conversion |
| MDI | Measurement-Device-Independent |
| TF | Twin-Field |
| DV | Discrete-Variable |
| CV | Continuous-Variable |
