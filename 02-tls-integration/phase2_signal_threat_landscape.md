# Phase 2: Signal Information — Threat Landscape & Requirements

## 2.1 What Constitutes "Signal Information"

Signal information encompasses any data transmitted via electromagnetic or optical means that requires confidentiality, integrity, or availability protection. The scope includes:

**Fiber-Optic Backbone Traffic:** The substrate of global telecommunications. Carries internet traffic, financial transactions, government communications, and cloud services. Data rates from 100 Gbps to multi-Tbps per fiber using DWDM. The primary target domain for QKD due to the shared physical medium (fiber) used by both quantum and classical channels.

**Satellite Uplink/Downlink:** Command and control signals to satellites, data downlinks from Earth observation and communications satellites, GPS/GNSS timing signals. Vulnerable to interception due to broadcast nature. Critical for military, intelligence, and global navigation systems.

**RF Signals and Tactical Military Communications:** VHF/UHF/SHF radio communications used by military forces, emergency services, and aviation. Includes tactical data links (Link 16, JTIDS), HF radio for beyond-line-of-sight, and microwave backhaul. Protected by TRANSEC (transmission security) and COMSEC (communications security) measures.

**5G/6G Signaling Planes:** Control-plane signaling between base stations, core network, and edge nodes. Fronthaul (RU to DU) and backhaul (DU to CU to core) links carry both user data and network control information. The signaling plane is a high-value target because compromising it enables traffic interception, network reconfiguration, and denial of service.

**SCADA/ICS Control Signals:** Supervisory Control and Data Acquisition systems for power grids, water treatment, oil and gas pipelines, manufacturing plants. Control signals are low-bandwidth but critically sensitive — unauthorized modification of control commands can cause physical damage or safety hazards. Legacy protocols (Modbus, DNP3) were designed without encryption.

**IoT/M2M Telemetry:** Sensor networks for environmental monitoring, smart cities, industrial IoT, and autonomous systems. High device counts, constrained compute resources, and often wireless last-mile connectivity. Data aggregation points are key security targets.

**Emergency Services Radio:** Police, fire, and EMS communications using standards like P25 (US), TETRA (Europe). Interception of these signals compromises operational security and can endanger lives.

**Confidence Level:** High — definitions based on established telecommunications and security standards.

---

## 2.2 Current Encryption Methods for Signal Information

### Data-at-Rest and Data-in-Transit

**Symmetric encryption:** AES-256 is the universal standard for encrypting data at rest and as the bulk cipher within transport protocols. AES-256 is considered quantum-resistant against Grover's algorithm (which would reduce its effective security to 128 bits — still considered sufficient).

**Transport Layer Security:** TLS 1.3 (RFC 8446) secures most internet traffic. Key exchange uses ECDHE (Elliptic Curve Diffie-Hellman Ephemeral) or, increasingly, hybrid ECDHE + ML-KEM for post-quantum protection. The handshake's key exchange is the vulnerable component — once the shared secret is established, symmetric AES encryption protects the data.

**IPsec/IKEv2:** Secures VPN tunnels for site-to-site and remote access connections. IKEv2 negotiates symmetric keys using Diffie-Hellman or ECDHE. RFC 8784 defines a mixed-PSK mechanism that allows injection of an additional pre-shared key (from QKD or other external source) into the IKE key derivation.

### Military and Government Communications

**NSA CNSA Suite 2.0:** Mandates transition to quantum-resistant algorithms for all National Security Systems. Key requirements: AES-256 for symmetric encryption, ML-KEM (CRYSTALS-Kyber) for key encapsulation, ML-DSA (CRYSTALS-Dilithium) for digital signatures. Transition deadlines: software signing by 2025 (preferred), web/cloud by 2025 (preferred) with exclusive use by 2033, all equipment by 2030.

**HAIPE (High Assurance Internet Protocol Encryptor):** NSA Type 1 encryption devices used across DoD networks. Future versions will incorporate CNSA 2.0 algorithms.

**TRANSEC/COMSEC:** Transmission security uses frequency hopping, spread spectrum, and burst transmission to prevent signal interception. Communications security uses encryption of content. These provide layered protection but depend on computational hardness of underlying key exchange.

### Physical-Layer Security

**Frequency hopping spread spectrum (FHSS):** Rapidly switches carrier frequency across a wide band. Provides low probability of intercept/detection but is not cryptographic — security depends on the secrecy of the hopping sequence.

**Direct-sequence spread spectrum (DSSS):** Spreads signal across a wider bandwidth using a pseudo-noise code. Provides processing gain against jamming and some intercept resistance.

These physical-layer measures complement but do not replace cryptographic protection.

**Confidence Level:** High
**Last Verified:** March 2026

---

## 2.3 Quantum Threats to Signal Security

### Shor's Algorithm Impact

Shor's algorithm, running on a sufficiently large quantum computer, would break all public-key cryptography currently in use:

| Algorithm | Problem | Impact |
|-----------|---------|--------|
| RSA-2048 | Integer factoring | Completely broken |
| ECDH/ECDSA (P-256, P-384) | Elliptic curve discrete log | Completely broken |
| Finite-field DH | Discrete logarithm | Completely broken |
| DSA | Discrete logarithm | Completely broken |

A cryptographically relevant quantum computer (CRQC) would need on the order of several thousand logical qubits, which translates to millions of physical qubits with current error rates. No CRQC exists as of 2026.

### Grover's Algorithm Impact

Grover's algorithm provides a quadratic speedup for brute-force search, effectively halving the security level of symmetric ciphers:

| Algorithm | Classical Security | Post-Quantum Security |
|-----------|-------------------|----------------------|
| AES-128 | 128 bits | 64 bits (insufficient) |
| AES-256 | 256 bits | 128 bits (still sufficient) |
| SHA-256 | 256 bits collision resistance | 128 bits (still sufficient) |

The practical impact is that AES-256 remains secure against quantum adversaries, but AES-128 should be phased out for long-term security.

### Harvest Now, Decrypt Later (HNDL)

This is the most immediate and practical quantum threat. Adversaries with sufficient storage capacity collect encrypted data today with the intent to decrypt it once CRQCs become available. The U.S. Department of Homeland Security, UK NCSC, ENISA, and the Australian Cyber Security Centre all base their post-quantum guidance on the premise that HNDL attacks are occurring now.

**Risk equation:** If the data's required confidentiality period exceeds the time until CRQCs emerge, the data is at risk today. For intelligence, defense, and financial data with 20-50 year confidentiality requirements, HNDL is an active concern.

### CRQC Timeline Estimates

No consensus exists on when CRQCs will emerge. Estimates range from 2030 to 2040+:

- Google's Willow chip (December 2024) demonstrated significant progress in quantum error correction, reducing error rates as system size increased
- Microsoft announced a topological qubit breakthrough in February 2025
- Most expert assessments cluster around 2035 as a central estimate for Q-Day
- The uncertainty is itself the risk — organizations with long-lived sensitive data cannot wait for certainty

**Confidence Level:** High for the threat characterization, Medium for timeline estimates
**Last Verified:** March 2026

---

## 2.4 Why QKD Specifically (vs. PQC Alone)

### Information-Theoretic vs. Computational Security

The fundamental distinction: PQC algorithms are believed to be hard for quantum computers to break, but this belief rests on mathematical conjectures (e.g., the hardness of lattice problems). If those conjectures prove wrong — due to algorithmic breakthroughs or flaws discovered years later — all data protected by PQC becomes retroactively vulnerable.

QKD, by contrast, derives its security from the laws of quantum physics. A correctly implemented QKD system provides information-theoretic security: no computational advance (classical or quantum) can compromise the key. This distinction matters most for data with very long confidentiality requirements or for adversaries with unknown future capabilities.

### Where QKD Adds Value Beyond PQC

QKD provides unique value in specific scenarios:

**Ultra-long confidentiality requirements:** Government secrets, nuclear weapon designs, intelligence sources and methods — data that must remain confidential for 50+ years. PQC provides security against known attacks, but cannot guarantee against unknown future mathematical breakthroughs. QKD's physics-based guarantees are not time-bounded.

**Eavesdropping detection:** QKD inherently detects interception attempts through QBER monitoring. PQC provides no mechanism to detect that an encrypted session's key exchange is being recorded for future decryption.

**Defense in depth:** Hybrid QKD+PQC approaches combine both security models. If either is compromised independently, the other maintains protection.

**Adversary model:** Against nation-state adversaries with both massive computational resources and long time horizons, the additive security of QKD+PQC is justified.

### Where PQC Is Sufficient

PQC alone is appropriate for most commercial and general-purpose applications:

- Data with confidentiality requirements shorter than the CRQC timeline
- Endpoints not connected by fiber (wireless, mobile, cloud)
- High-volume, low-cost deployments where QKD infrastructure cost is prohibitive
- Applications requiring only digital signatures (QKD does not address authentication directly)

### NSA Position

The NSA has explicitly stated that QKD is "not considered a practical solution" for National Security Systems and advises against QKD investment without direct consultation. The NSA's confidence is in CNSA 2.0 (PQC) algorithms. However, several allied nations (EU, UK, China, South Korea, Japan) are investing heavily in QKD infrastructure, creating a strategic divergence in approach.

**Confidence Level:** High
**Last Verified:** March 2026

---

## Sources

1. [NIST finalizes PQC standards](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards)
2. [FIPS 203 - ML-KEM](https://csrc.nist.gov/pubs/fips/203/final)
3. [FIPS 204 - ML-DSA](https://csrc.nist.gov/pubs/fips/204/final)
4. [NSA CNSA 2.0 announcement](https://www.nsa.gov/Press-Room/News-Highlights/Article/Article/3148990/nsa-releases-future-quantum-resistant-qr-algorithm-requirements-for-national-se/)
5. [NSA CNSA 2.0 FAQ (December 2024 v2.1)](https://media.defense.gov/2022/Sep/07/2003071836/-1/-1/0/CSI_CNSA_2.0_FAQ_.PDF)
6. [Harvest now, decrypt later - Wikipedia](https://en.wikipedia.org/wiki/Harvest_now,_decrypt_later)
7. [Federal Reserve HNDL paper](https://www.federalreserve.gov/econres/feds/harvest-now-decrypt-later-examining-post-quantum-cryptography-and-the-data-privacy-risks-for-distributed-ledger-networks.htm)
8. [RAND - US allied militaries and quantum threat](https://www.rand.org/pubs/commentary/2025/06/us-allied-militaries-must-prepare-for-the-quantum-threat.html)
9. [PQC Standardization 2025 Update](https://postquantum.com/post-quantum/cryptography-pqc-nist/)
10. [RFC 8446 - TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html)
11. [RFC 8784 - IKEv2 mixed-PSK](https://www.rfc-editor.org/rfc/rfc8784.html)
