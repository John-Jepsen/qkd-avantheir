# QKD & Signal Information Security — Complete Research Report

**Prepared:** March 2026
**Classification:** Unclassified — For Research Use
**Companion to:** Avantheir QKD Key Infrastructure Initiative (01-08 series)

---

## Executive Summary

Quantum Key Distribution has matured from laboratory curiosity to operational infrastructure in specific domains. China operates a carrier-grade QKD backbone exceeding 12,000 km across 80 cities. Europe is transitioning from national pilot networks to cross-border operational services under EuroQCI, with the first satellite QKD demonstrator (Eagle-1) launching in 2026. Commercial vendors (Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird) offer production-grade metro QKD systems that co-exist with multi-Tbps classical DWDM traffic.

However, QKD is not a universal replacement for classical cryptography. It is best understood as a specialized, high-assurance tool for protecting the highest-value signal information over fiber-connected infrastructure. For the vast majority of signal security needs — mobile communications, wireless networks, internet-scale services — Post-Quantum Cryptography (PQC), now standardized by NIST (FIPS 203/204/205, August 2024), is the appropriate solution.

The strategic choice is not QKD versus PQC, but where to deploy each. This report maps that choice across six signal domains: fiber-optic telecommunications, satellite communications, military/defense, 5G/6G, critical infrastructure, and RF/wireless.

---

## Key Findings by Phase

### Phase 1: QKD Technology Landscape

Seven major QKD protocol families exist, each with distinct characteristics. BB84 (decoy-state) and CV-QKD are commercially deployed. Twin-field QKD holds the distance record at 1,002 km (lab) and overcomes the repeaterless capacity bound. MDI-QKD eliminates all detector-side attacks and has achieved the first cross-border deployment in Europe. Quantum repeaters — the technology needed for long-distance QKD without trusted nodes — remain 5-10+ years from field deployment, with the AWS-Harvard 35 km entangled memory demonstration (2024) being the most advanced milestone.

**Full analysis:** [phase1_qkd_foundations.md](phase1_qkd_foundations.md)

### Phase 2: Signal Information Threat Landscape

The quantum threat to signal security is real but time-bounded. No cryptographically relevant quantum computer (CRQC) exists; expert estimates for Q-Day cluster around 2035. The immediate threat is harvest-now-decrypt-later (HNDL), acknowledged by DHS, NCSC, and ENISA. NIST finalized three PQC standards in August 2024 (ML-KEM, ML-DSA, SLH-DSA), and NSA mandates CNSA 2.0 transition for National Security Systems by 2030-2033. The NSA explicitly does not recommend QKD for NSS.

QKD's unique value over PQC lies in information-theoretic security (immune to future mathematical breakthroughs), eavesdropping detection, and defense-in-depth in hybrid architectures. PQC is sufficient for most applications; QKD is justified for ultra-long confidentiality requirements and the highest adversary models.

**Full analysis:** [phase2_signal_threat_landscape.md](phase2_signal_threat_landscape.md)

### Phase 3: Application Mapping

**Fiber-optic telecom (TRL 8-9):** The most mature application domain. QKD co-exists with 33.4 Tbps DWDM traffic. Commercial deployments by Toshiba, QuantumCTek, and ID Quantique/IonQ. ETSI GS QKD 014 standardizes key delivery. Integration into TLS 1.3 PSK and IPsec IKEv2 PPK is documented in the Avantheir initiative.

**Satellite communications (TRL 4-5):** Micius demonstrated 12,800 km satellite QKD. Eagle-1 (EU), QEYSSat (Canada) launching 2026. Operational satellite C2 security via QKD is 3-5 years away.

**Military/defense (TRL 2-6, domain-dependent):** QKD viable for fixed strategic backbone (fiber). Not feasible for tactical/mobile communications. NATO DISCRETION project deploys CV-QKD for European defense. NSA position favors PQC over QKD.

**5G/6G (TRL 3-5):** QKD applicable to securing highest-priority backhaul segments. 6G vision papers integrate quantum communications natively, but standardization is years away.

**SCADA/critical infrastructure (TRL 4-5):** Pilot deployments for smart grid authentication. Low bandwidth requirements match QKD well. Legacy protocol integration is the primary challenge.

**RF/wireless (TRL 1-2):** QKD over RF is physically infeasible. Hybrid fiber-QKD + PQC-wireless is the only viable architecture.

**Full analysis:** [phase3_application_mapping.md](phase3_application_mapping.md)

### Phase 4: Technical Challenges

Five critical barriers: (1) distance limitations without quantum repeaters, (2) side-channel and implementation attacks creating gaps between theoretical and practical security, (3) cost premium of 10-100x over PQC, (4) absence of mandatory security certification frameworks comparable to FIPS 140-3, and (5) multi-vendor interoperability gaps.

**Full analysis:** [phase4_challenges_limitations.md](phase4_challenges_limitations.md)

### Phase 5: Competitive Landscape

The QKD market is projected to grow from $0.48B (2024) to $2.63B by 2030 (CAGR 32.6%). IonQ's $250M acquisition of ID Quantique (February 2025) signals convergence between quantum computing and communications. ETSI and IETF are standardizing hybrid QKD+PQC key exchange. Government funding is substantial: EU Quantum Flagship (~EUR 1B), China (>$15B estimated), US NQI (~$3B+).

**Full analysis:** [phase5_competitive_landscape.md](phase5_competitive_landscape.md)

### Phase 6: Strategic Assessment

**Deploy QKD now:** Metro fiber backbone for government/defense and financial sector. Hybrid QKD+PQC architecture for defense-in-depth.

**Pilot QKD:** Long-haul fiber (trusted-node), satellite C2, SCADA/critical infrastructure.

**Monitor QKD:** 5G backhaul, enterprise telecom, IoT gateways.

**Use PQC instead:** Military tactical, RF/wireless, general enterprise, mobile/cloud.

**Full analysis:** [phase6_synthesis_assessment.md](phase6_synthesis_assessment.md)

---

## Recommendation Matrix (Summary)

| Domain | Now | 2028 | 2030+ |
|--------|-----|------|-------|
| Gov/defense metro fiber | QKD + PQC hybrid | Scale QKD coverage | Mature QKD infrastructure |
| Financial metro fiber | QKD + PQC hybrid | Expand to more links | Cost-driven expansion |
| Enterprise metro fiber | PQC only | Evaluate QKD cost | Deploy if cost-justified |
| Long-haul fiber | Trusted-node QKD pilot | Satellite bridge pilot | Quantum repeater pilot |
| Satellite C2 | Plan for QKD-capable ground stations | Eagle-1/QEYSSat results inform design | QKD-native satellite systems |
| Military strategic | QKD on fixed backbone | Expand with CNSA 2.0 hybrid | Integrate repeater tech |
| Military tactical | CNSA 2.0 (PQC) | CNSA 2.0 (PQC) | Evaluate QKD if mobile platforms emerge |
| 5G/6G | PQC for 5G | QKD pilot for core | 6G quantum-native design |
| SCADA/ICS | QKD pilot on critical links | Expand to more substations | Standardized QKD-SCADA integration |
| IoT | PQC gateways | PQC gateways | QKD at aggregation if cost-justified |
| RF/wireless | PQC + AES-256 | PQC + AES-256 | No change expected |

---

## Where to Look for More Information

### Standards Bodies

- **ETSI QKD ISG:** https://www.etsi.org/technologies/quantum-key-distribution — Primary QKD standards suite
- **ITU-T SG13/SG17:** Y.3800 series — QKD network architecture and security
- **IETF:** RFC 9794 (hybrid terminology), drafts on hybrid TLS key exchange
- **NIST:** FIPS 203/204/205 (PQC), NISTIR 8547 (PQC transition guidance)
- **ISO/IEC JTC1 SC27:** Quantum-safe security evaluation criteria

### Research Groups

- **USTC (China):** Pan Jian-Wei group — TF-QKD distance records, satellite QKD
- **Toshiba Cambridge Research Laboratory:** High-rate QKD, DWDM co-existence
- **University of Geneva:** CV-QKD theory, SNSPD development (ID Quantique origins)
- **University of Waterloo / IQC:** QEYSSat, QKD security proofs
- **AWS Center for Quantum Networking / Harvard:** Quantum repeater development
- **University of York Quantum Communications Hub:** UK QKD research coordination

### Vendors

- **ID Quantique / IonQ:** https://www.idquantique.com — Commercial DV-QKD market leader
- **Toshiba:** https://www.toshiba.eu/quantum — High-performance QKD systems
- **QuantumCTek:** https://www.quantumctek.com — Chinese QKD infrastructure
- **LuxQuanta:** https://luxquanta.com — CV-QKD systems
- **Q*Bird:** https://q-bird.com — MDI-QKD solutions
- **QuintessenceLabs:** https://www.quintessencelabs.com — QKD + key management + QRNG

### Government/Policy

- **NSA CNSA 2.0:** https://media.defense.gov — Quantum-resistant algorithm requirements
- **EuroQCI:** https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci
- **US National Quantum Initiative:** https://www.quantum.gov
- **QED-C:** https://quantumconsortium.org — US quantum industry consortium

---

## Document Index

| File | Contents |
|------|----------|
| phase1_qkd_foundations.md | QKD protocols, hardware, architectures, global deployments |
| phase2_signal_threat_landscape.md | Signal information scope, current encryption, quantum threats, QKD vs PQC |
| phase3_application_mapping.md | QKD application to six signal domains |
| phase4_challenges_limitations.md | Distance, cost, side-channels, certification, repeater timeline |
| phase5_competitive_landscape.md | QKD vs PQC, hybrid approaches, vendors, government programs |
| phase6_synthesis_assessment.md | TRL assessment, gap analysis, 5/10-year outlook, recommendation matrix |
| qkd_signal_research_complete.md | This consolidated report |

---

*This research was conducted using peer-reviewed publications, government/standards body documents, and verified vendor announcements as primary sources. Claims are cross-referenced where possible. Timeline projections beyond 2028 carry inherent uncertainty and should be revisited annually.*
