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
| **Binary reconciliation** | Error correction method comparing block parities over a classical channel to locate and flip mismatched bits. |
| **Cascade** | Multi-pass binary reconciliation protocol. Performs several rounds of block-parity comparison at increasing block sizes. Near-zero residual error rate. Used in most commercial DV-QKD. |
| **LDPC reconciliation** | Low-Density Parity-Check based error correction. More efficient than Cascade for high QBER channels. Used in CV-QKD. |
| **Privacy amplification** | Final stage: hash the corrected key to remove any information Eve may have gained. Produces the final secure key. |
| **Universal hash** | Hash function family where the collision probability is bounded regardless of input. BLAKE2b used as universal hash in BB84 privacy amplification. |
| **Leftover Hash Lemma** | Theorem guaranteeing that HKDF/universal hashing bounds Eve's information to 2^(−security_param) bits even when she has partial knowledge of the input. |
| **QBER sample fraction** | Fraction of sifted bits sacrificed publicly for error rate estimation (typically 10%). These bits are discarded and cannot appear in the final key. |

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
| **Master SAE** | The SAE that initiates key retrieval via `GET /enc_keys`. Receives key_ID + key_bytes. |
| **Slave SAE** | The SAE that retrieves the matching key via `POST /dec_keys` using the key_ID sent by the master SAE. |
| **Key ID** | Non-secret identifier for a key block, enabling the master SAE to tell the slave SAE which key to retrieve without transmitting key bytes. Maps to TLS 1.3 `psk_identity`. |
| **Key pool** | Internal buffer of pre-generated BB84 keys held in the KME, ready for issuance. Replenished by background BB84 sessions. |
| **Key pool target** | Configured minimum number of keys the KME maintains in its available pool (e.g., 50). |
| **Dual-KME deployment** | Architecture where Alice and Bob each run their own KME instance. Keys are generated on one side and synchronized to the peer via a secure internal channel. Mirrors commercial deployments (Toshiba, IDQ Cerberis). |
| **Peer sync** | Mechanism by which a master KME pushes key_ID + key_bytes to the peer KME after issuing keys. Allows the peer's slave SAE to later retrieve the key by key_ID without re-running BB84. |
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
| **Trusted-node network** | Multi-hop architecture where intermediate nodes relay keys. Security depends on physical security at each node. Each relay node necessarily learns the session key in cleartext. |
| **OTP relay pattern** | One-Time Pad relay: each hop XOR-encrypts the session key payload with the outgoing link key after XOR-decrypting it with the incoming link key. Used in Beijing-Shanghai backbone and EuroQCI. |
| **Link key** | BB84-generated symmetric key shared between exactly two adjacent QKD nodes. Consumed once per relay operation (OTP semantics). |
| **Session key** | Ephemeral 256-bit key generated fresh at the source for a single relay operation. Relayed to the destination via OTP relay; never travels in plaintext over any quantum link. |
| **Relay integrity check** | Verification at the destination that the recovered session key matches the original (XOR cancellation check). |
| **BFS routing** | Breadth-first search over the QKD network graph to find the shortest active path between source and destination. |
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

## Hybrid Key Derivation & KEM Primitives

| Term | Definition |
|------|-----------|
| **KEM** | Key Encapsulation Mechanism. Asymmetric primitive where one party encapsulates a shared secret under a public key; the other decapsulates with their secret key to recover the same secret. |
| **Encapsulate** | KEM operation: generates (ciphertext, shared_secret). The ciphertext is sent to the peer; the shared secret is kept locally. |
| **Decapsulate** | KEM operation: recovers the shared secret from the ciphertext using the secret key. |
| **ML-KEM (Kyber-768)** | NIST FIPS 203 key encapsulation mechanism. Kyber-768 wire sizes: 1184-byte public key, 1088-byte ciphertext, 32-byte shared secret. Security based on Module-LWE. |
| **HKDF** | HMAC-based Key Derivation Function (RFC 5869). Two-step: Extract (compress entropy into PRK) + Expand (derive keying material). Used in TLS 1.3, hybrid QKD+PQC derivation, and IPsec. |
| **IKM** | Input Key Material. The raw entropy fed into HKDF-Extract. In hybrid derivation: `IKM = qkd_key ‖ kem_shared_secret`. |
| **PRK** | Pseudorandom Key. The intermediate 32-byte value output by HKDF-Extract. Used as input to HKDF-Expand. |
| **Info / context** | Domain-separation string passed to HKDF-Expand (e.g., `"hybrid-key-derivation"`). Ensures keys derived for different purposes are independent. |
| **Hybrid key derivation** | Combining QKD key material with a PQC KEM shared secret via HKDF: `IKM = qkd_key ‖ kem_secret; OKM = HKDF-SHA256(IKM)`. Combined key is secure if either QKD or ML-KEM is unbroken. Per ETSI TS 104 015 §6.3. |
| **AEAD** | Authenticated Encryption with Associated Data. Provides both confidentiality and integrity. AES-256-GCM is the AEAD used in the PSK demo and TLS 1.3. |
| **AES-256-GCM** | AES in Galois/Counter Mode with 256-bit key. Provides 128-bit security against Grover's algorithm. Standard AEAD for QKD-secured sessions. |
| **GCM authentication tag** | 128-bit integrity verification appended to AES-GCM ciphertext. Decryption fails with `InvalidTag` if key, nonce, or ciphertext is modified. |
| **Nonce** | Number used once. 12-byte random value prepended to AES-GCM ciphertext. Must never repeat under the same key. |
| **BLAKE2b** | Cryptographic hash function. Used in BB84 privacy amplification as a universal hash (256-bit output). Faster than SHA-256 on 64-bit platforms. |

---

## Implementation Patterns

| Term | Definition |
|------|-----------|
| **MockMLKEM** | Software stub for ML-KEM (Kyber-768) used in simulation. Embeds the shared secret in the first 32 bytes of the ciphertext so decapsulate can recover it without a real secret key. Not cryptographically secure — for testing only. |
| **Key pool refill** | Background thread that restores the KME's available key count to the target when it drops below a trigger threshold. Avoids latency spikes on enc_keys requests. |
| **BB84 key pool** | Set of pre-generated BB84 keys held in the KME ready for issuance. Each entry: (key_ID, key_bytes, size_bits). |
| **Available pool** | Keys generated but not yet issued to any SAE. Moved to pending on enc_keys. |
| **Pending pool** | Keys issued to the master SAE (enc_keys was called) but not yet retrieved by the slave SAE (dec_keys). Keys are removed from pending on successful dec_keys. |
| **QBER threshold abort** | Protocol abort triggered when estimated QBER exceeds the security threshold (default 11% for BB84). Returns `BB84Result(secure=False, eavesdropper_detected=True)`. |
| **Intercept-resend attack** | Eve measures each qubit in a random basis and re-prepares. Introduces ~25% QBER (detectable). Simulated by `BB84Protocol(eavesdrop=True)`. |
| **ETSI 014 REST API** | `GET /enc_keys` → issues keys to master SAE. `POST /dec_keys` → retrieves key by key_ID for slave SAE. `GET /status` → pool and capability info. `POST /peer/sync_keys` → internal peer sync (dual-KME only). |
| **Flask test client** | In-process HTTP client for testing Flask apps without a network socket. Used in the pytest suite to test KME endpoints without starting a live server. Not thread-safe when shared across threads. |
| **Module-scoped fixture** | pytest fixture initialized once per test module rather than per test function. Used for the KME Flask client because BB84 pool initialization takes ~3 seconds. |
| **MetricsCollector** | Thread-safe class that records BB84Result per session and computes aggregate QBER, key rate, eavesdrop count, and pool level for dashboard display. |
| **QBER dashboard** | Text display showing average/peak QBER over the last 20 sessions, a bar chart scaled to the 11% abort threshold, total key bits generated, and uptime. |

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
| KEM | Key Encapsulation Mechanism |
| HKDF | HMAC-based Key Derivation Function |
| IKM | Input Key Material |
| PRK | Pseudorandom Key |
| AEAD | Authenticated Encryption with Associated Data |
| GCM | Galois/Counter Mode |
| OTP | One-Time Pad |
| BFS | Breadth-First Search |
| LDPC | Low-Density Parity-Check |
