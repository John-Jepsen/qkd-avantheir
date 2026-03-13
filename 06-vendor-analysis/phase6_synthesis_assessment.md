# Phase 6: Synthesis & Strategic Assessment

## 6.1 Technology Readiness Assessment

Technology Readiness Levels (TRL) are assessed on a 1-9 scale, where TRL 1-3 represents research, TRL 4-6 represents development and demonstration, and TRL 7-9 represents deployment and operations.

| Signal Domain | QKD TRL | Rationale |
|---------------|---------|-----------|
| **Fiber-optic telecom (metro)** | **TRL 8-9** | Commercial products deployed, carrier-grade operations demonstrated over 10,000+ km in China, multi-Tbps co-existence validated |
| **Fiber-optic telecom (long-haul)** | **TRL 5-6** | Trusted-node relay operational but security-limiting; TF-QKD lab-demonstrated at 1,000+ km but not field-deployed |
| **Satellite C2 uplinks** | **TRL 4-5** | Micius demonstrated satellite QKD; Eagle-1 and QEYSSat launching 2026; operational C2 integration not yet demonstrated |
| **Military strategic comms** | **TRL 5-6** | DISCRETION project deploying CV-QKD for European defense; limited operational validation |
| **Military tactical comms** | **TRL 2-3** | Fundamental incompatibility with mobile RF; research on hybrid fiber+wireless architectures |
| **5G backhaul/fronthaul** | **TRL 4-5** | Lab demonstrations; SDN integration research; no carrier-scale deployment |
| **6G native quantum** | **TRL 2-3** | Vision papers and research frameworks only |
| **SCADA/ICS (power grid)** | **TRL 4-5** | Pilot deployments in China, research prototypes for smart grid authentication |
| **IoT gateway security** | **TRL 3-4** | Conceptual architectures; no field deployments of QKD-secured IoT gateways |
| **RF/wireless signal security** | **TRL 1-2** | QKD over RF is not physically feasible; hybrid approaches are theoretical |

**Confidence Level:** Medium — TRL assessments involve judgment and may vary by specific vendor/implementation

---

## 6.2 Gap Analysis

### Critical Gaps — Must Be Solved Before Scale Deployment

**Quantum repeaters:** The single most important missing technology. Without them, QKD is limited to metro distances (direct links) or requires trusted nodes (security compromise) or satellites (weather-dependent, limited bandwidth). Current timeline: earliest field-deployable repeaters by 2033-2035.

**Implementation security certification:** No FIPS 140-3 equivalent for QKD devices. Buyers cannot independently verify that a QKD system's implementation matches its theoretical security claims. ETSI GS QKD 016 provides a framework but adoption is minimal.

**Multi-vendor interoperability:** EuroQCI cross-border deployments are testing this in practice, but formal interoperability certification does not exist. Vendor lock-in is a real risk for early adopters.

**Cost reduction:** QKD remains 10-100x more expensive per secured link than PQC migration. CV-QKD using standard telecom components and photonic integrated circuits (PICs) offer the most promising cost reduction path, but are 3-5 years from mature commercialization.

### Important Gaps — Limit But Don't Prevent Deployment

**Key rate at distance:** Even for metro deployments, QKD key rates drop significantly beyond 50 km. For applications requiring high key consumption (many concurrent sessions, frequent rekeying), key supply management becomes operationally complex.

**Network management standards:** Managing multi-node QKD networks (routing, fault management, provisioning) lacks mature standards. Each vendor provides proprietary management interfaces.

**Workforce:** Operating QKD networks requires expertise in quantum optics, classical networking, and cryptographic key management — a rare skill combination.

### Gaps Being Actively Closed

**Fiber co-existence:** Demonstrated at 33.4 Tbps (Toshiba/KDDI, 2025). No longer a fundamental barrier.

**ETSI API standardization:** GS QKD 014 REST API is widely implemented. Key delivery is a solved problem at the API level.

**PQC standards:** NIST FIPS 203/204/205 finalized (August 2024). The classical side of hybrid QKD+PQC is now standardized.

**Confidence Level:** High

---

## 6.3 Five-Year Outlook (by 2030)

### What Will Be Deployable

**Metro QKD networks:** Mature, multi-vendor, commercially supported metro QKD networks will be available from multiple vendors. CV-QKD and DV-QKD will both be commercial. Costs will decrease but remain significantly above PQC alternatives. Deployment will be concentrated in: government/defense networks, financial sector backbone links, critical infrastructure control centers, and telecom operator core networks.

**Satellite QKD:** Eagle-1 (EU), QEYSSat (Canada), and Chinese constellation will provide satellite-to-ground QKD services. Coverage will be limited to ground stations at specific locations, not ubiquitous. Key rates from LEO satellites will be modest (kbps per pass) and weather-dependent.

**Hybrid QKD+PQC:** Standardized hybrid key exchange (ETSI, IETF) will be incorporated into commercial TLS and IPsec implementations. OpenSSL and other libraries will support QKD-KEM providers.

**EuroQCI operational:** Cross-border QKD links connecting EU member states will be operational for government and critical infrastructure users. National QCI networks in most EU countries.

**Chinese expansion:** China's QKD infrastructure will extend to 50+ cities with integrated satellite-ground networks available to commercial users.

### What Will Remain Challenging

**Long-distance without trusted nodes:** Quantum repeaters will still be in lab/early prototype stage. Operational long-distance QKD will still require trusted-node relay or satellite bridges.

**Mobile/tactical military:** QKD will not be directly applicable to mobile military communications. PQC (CNSA 2.0) will be the primary protection, with QKD securing only fixed backbone links.

**Universal QKD certification:** A universally accepted certification framework comparable to FIPS 140-3 is unlikely to be fully established by 2030, though progress through ETSI and national certification bodies is expected.

**Confidence Level:** Medium

---

## 6.4 Ten-Year Outlook (by 2035)

### What Changes with Quantum Repeaters and Satellite Constellations

**Quantum repeaters (early deployment):** If the AWS-Harvard and similar programs succeed in scaling, the first commercially deployable quantum repeaters may appear by 2033-2035. These would enable: metropolitan-to-regional QKD without trusted nodes (50-500 km per repeater chain), reduced security dependency on physical node security, and higher key rates at distance through entanglement distillation.

**Satellite constellations:** LEO QKD satellite constellations (China, possibly EU and others) will provide global coverage with multiple satellite passes per day per ground station. This enables intercontinental QKD key distribution without transoceanic trusted-node relay. Key rates will increase as satellite technology matures, but satellite QKD will remain weather-dependent and lower-bandwidth than fiber-based QKD.

**CRQC emergence:** If CRQCs emerge by 2035 (the central estimate of many expert assessments), the urgency for quantum-safe communications will become acute. Organizations that deployed QKD + PQC hybrid systems will be in a strong position. Those relying solely on pre-quantum cryptography will face immediate vulnerability. Even PQC-only deployments should be secure, assuming no algorithmic breakthroughs, but QKD provides an additional layer of assurance.

**QKD-native 6G networks:** If 6G standards incorporate quantum communication natively (as proposed in vision papers), QKD may become an integral component of next-generation telecom infrastructure rather than an add-on overlay.

**Confidence Level:** Low — ten-year projections are highly speculative

---

## 6.5 Recommendation Matrix

| Signal Domain | Recommendation | Rationale |
|---------------|---------------|-----------|
| **Fiber telecom — metro backbone (government/defense)** | **Deploy QKD now** | TRL 8-9, commercial products available, information-theoretic security justified for high-value government communications. Deploy hybrid QKD+PQC for defense-in-depth |
| **Fiber telecom — metro backbone (financial sector)** | **Deploy QKD now** | Justified for interbank settlement, trading backbone, regulatory compliance with quantum-safe mandates |
| **Fiber telecom — metro backbone (general enterprise)** | **Use PQC; monitor QKD** | Cost/benefit does not justify QKD for typical enterprise data. Deploy PQC (ML-KEM + ML-DSA) now. Re-evaluate as QKD costs decrease |
| **Fiber telecom — long-haul** | **Pilot QKD** | Use trusted-node relay for highest-priority links. Monitor quantum repeater and satellite progress for untrusted long-haul |
| **Satellite command & control** | **Pilot QKD** | Eagle-1 and QEYSSat results will determine feasibility. Plan for QKD-capable ground stations in new satellite program designs |
| **Military strategic communications** | **Deploy QKD now** (fixed infrastructure) | For fiber-connected strategic nodes (command centers, data centers). Hybrid QKD+CNSA 2.0 for layered protection |
| **Military tactical communications** | **Use PQC (CNSA 2.0)** | QKD not feasible for mobile/RF. Deploy CNSA 2.0 now per NSA timelines |
| **5G backhaul/core** | **Monitor QKD** | Deploy PQC for 5G security now. Pilot QKD for highest-security core network segments. Track 6G quantum integration standards |
| **SCADA/ICS critical infrastructure** | **Pilot QKD** | Pilot QKD on control center-to-substation fiber links for power grid, water, and pipeline systems. Low bandwidth requirements match QKD well |
| **IoT/sensor networks** | **Use PQC** | QKD not practical at device level. PQC-secured gateways are the right architecture. QKD at aggregation points is possible but rarely justified |
| **RF/wireless signals** | **Use PQC; QKD not applicable** | QKD cannot operate over RF. Use PQC-secured key exchange + AES-256 symmetric encryption |

---

## 6.6 Key Open Research Questions Worth Tracking

**Quantum repeater scaling:** Can quantum memories achieve the fidelity, bandwidth, and operational stability needed for field deployment? The AWS-Harvard silicon-vacancy center approach is the most advanced, but scaling from lab to production is a multi-year engineering challenge.

**CV-QKD security proofs in the finite-key regime:** CV-QKD offers significant cost advantages, but its security proofs against general attacks with finite data (as opposed to asymptotic limits) are less mature than DV-QKD. Closing this gap is essential for certification.

**Device-independent QKD at practical rates:** Fully device-independent QKD (requiring no trust in device construction) has been demonstrated in labs but at extremely low key rates. Achieving practical rates would make QKD security guarantees irrefutable.

**Photonic integrated circuit (PIC) QKD:** Chip-scale QKD transmitters and receivers could reduce costs by orders of magnitude. KETS Quantum Security (UK) and others are pursuing this. Track progress on integration density, loss, and yield.

**Quantum network protocols:** Routing, resource allocation, and network management for multi-node quantum networks are open problems. The analogy to early internet protocol development is apt — foundational protocols are still being defined.

**QKD certification frameworks:** Whether ETSI GS QKD 016 or an ISO/IEC framework achieves widespread adoption will determine whether QKD systems can be independently evaluated for government procurement.

**CRQC timeline compression:** Advances in quantum error correction (Google Willow, Microsoft topological qubits) may compress the timeline for CRQCs. Any significant announcement should trigger re-evaluation of the urgency for QKD deployment.

**Confidence Level:** High (for identifying the questions), Low (for predicting answers)
**Last Verified:** March 2026

---

## Sources

All sources from Phases 1-5 apply. Key additional references:

1. [EU Quantum Europe Strategy (July 2025)](https://qt.eu/media/pdf/Quantum_Europe_Strategy_July_2025.pdf)
2. [CEPS quantum-safe transition report (Dec 2025)](https://cdn.ceps.eu/2025/12/2025-12-Quantum-TF-report-formatted.pdf)
3. [QKD market growth projections](https://www.marketsandmarkets.com/Market-Reports/quantum-key-distribution-qkd-market-80654677.html)
4. [SIPRI military quantum technologies primer](https://www.sipri.org/sites/default/files/2025-07/0725_military_and_security_dimensions_of_quantum_technologies_0.pdf)
5. [Quantum repeater research review](https://www.researchgate.net/publication/391920874_Quantum_repeaters_current_research_directions_and_latest_achievements)
