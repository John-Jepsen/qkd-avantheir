# Phase 3: Application Mapping — QKD x Signal Information

## 3A. Fiber-Optic Telecommunications

### QKD Integration with Existing DWDM Infrastructure

The co-existence of quantum and classical signals on the same fiber is the critical enabler for cost-effective QKD deployment. Without this capability, QKD requires dedicated dark fiber — a significant cost barrier. Recent demonstrations have proven this co-existence is viable:

Toshiba and Orange demonstrated QKD alongside high-volume DWDM traffic at 400 Gbps over 184 km in February 2024. The quantum channel occupied a single wavelength within the DWDM grid while classical traffic filled the remaining channels. Cross-talk from classical channels (Raman scattering, four-wave mixing) was managed through wavelength isolation and filtering.

In December 2025, Quantum Corridor and Toshiba demonstrated quantum-secured communication over 21.8 km of live commercial fiber with 800G encrypted transport, maintaining full line-rate performance with zero packet loss over 48 continuous hours. KDDI and Toshiba multiplexed 33.4 Tbps of data with quantum keys over 80 km in March 2025, tripling the capacity of earlier approaches.

For CV-QKD specifically, the 120 km co-existence demonstration with fully populated CWDM traffic (2025) validated that CV-QKD can function as a plug-and-play addition to existing 80-100 km long-haul optical networks.

### Key Management and Key Relay

Metro networks typically use point-to-point QKD links feeding into ETSI GS QKD 014 compliant Key Management Entities (KMEs). For long-haul connections, trusted-node relay extends reach at the cost of requiring physical security at intermediate nodes. The ETSI REST API standardizes key delivery to Secure Application Entities (SAEs) — the applications consuming keys for TLS, IPsec, or other protocols (see existing Avantheir docs 02-tls-integration.md and 05-key-management.md).

### Commercial Products and Deployments

| Vendor | Product | Type | Notable Capability |
|--------|---------|------|-------------------|
| ID Quantique | Cerberis XG QKD | DV-QKD platform | ETSI 014 compliant, metro range |
| Toshiba | Multiplexed QKD System | DV-QKD | 33.4 Tbps co-existence, 80 km |
| QuantumCTek | QKD Infrastructure Suite | DV-QKD | Powers China's 12,000+ km backbone |
| LuxQuanta | NOVA LQ (2nd gen) | CV-QKD | Standard telecom components |
| Q*Bird | Falqon Series | MDI-QKD | Multi-user, cross-border capable |

### Standards

ETSI QKD ISG maintains the primary standards: GS QKD 004 (application interface), GS QKD 014 (REST-based key delivery), GS QKD 008 (quality of service), GS QKD 015 (security proofs). ITU-T SG13 (Y.3800 series) and SG17 define the functional architecture and security requirements for quantum key distribution networks.

**Confidence Level:** High
**Last Verified:** March 2026

---

## 3B. Satellite & Free-Space Optical Communications

### Satellite QKD Programs

**Micius (China, 2016-present):** The pathfinder mission. Key results include QKD at 1,200 km, entanglement distribution at 1,200 km, quantum teleportation from ground to satellite, a 7,600 km Vienna-Beijing secure video conference (2017), and a ~12,800 km Beijing-South Africa link (2025). China plans a global quantum communications satellite constellation by 2027, targeting BRICS partners for coverage.

**Eagle-1 (EU/ESA, launching 2026):** The first European in-orbit QKD demonstrator. Will validate satellite-to-ground QKD links and connect to EuroQCI ground stations in Greece, Cyprus, and the Netherlands. Part of the IRIS² secure communications constellation roadmap.

**QEYSSat (Canada, launching late 2026):** A ~100 kg microsatellite for ground-to-space QKD, designed by Honeywell and led by the Institute for Quantum Computing at the University of Waterloo. Will be the first Canadian demonstration of quantum key exchange from orbit. The Canadian Space Agency also funded QEYnet (CA$1.4M) to test low-cost quantum satellite links.

### Atmospheric Channel Challenges

Free-space optical QKD through the atmosphere faces: turbulence-induced beam wandering and scintillation (refractive index fluctuations), weather attenuation (clouds, rain, fog can completely block optical links), background noise from sunlight (limits daytime operation; night-only or narrow spectral/temporal filtering required), and pointing/tracking requirements (satellite moves at ~7 km/s in LEO, requiring sub-microradian tracking accuracy).

### Applications to Securing Satellite Command & Control

Satellite command uplinks are among the highest-value targets for quantum-secured key distribution. Unauthorized commands could disable, redirect, or weaponize satellites. QKD-secured uplinks would provide: authentication of ground-to-satellite commands using QKD-derived symmetric keys, detection of any interception attempt on the key exchange channel, and key refresh capability on each satellite pass (LEO: ~10-minute window per pass).

This remains a forward-looking application — current satellites do not carry QKD receivers, but next-generation programs (Eagle-1, QEYSSat, China's constellation) are building toward this capability.

**Confidence Level:** High for demonstrated results, Medium for forward-looking programs
**Last Verified:** March 2026

---

## 3C. Military & Defense Signal Security

### QKD for Tactical Communications — Feasibility and Limitations

Tactical military communications present the most challenging environment for QKD deployment. The requirements — mobile platforms, ad-hoc network topology, operation in contested electromagnetic environments, and extreme environmental conditions — are fundamentally at odds with current QKD technology, which requires stable optical paths (fiber or clear-sky line-of-sight).

**Current feasibility:** QKD cannot secure tactical radio or mobile wireless communications directly. QKD can secure the fiber backbone that connects tactical operations centers, command posts, and strategic communications nodes. The practical model is QKD for backbone/strategic links with PQC-secured symmetric keys distributed to tactical endpoints via conventional key management.

### NSA CNSA 2.0 and HAIPE Integration

The NSA does not recommend QKD for National Security Systems and has not included it in CNSA 2.0 requirements. However, the existing Avantheir documentation notes that RFC 8784 (IKEv2 mixed-PSK) provides a mechanism to inject QKD-derived keys into IPsec VPN tunnels, which is the primary mechanism used by HAIPE encryptors. A hybrid approach using CNSA 2.0 algorithms augmented with QKD-derived PSKs could satisfy both the NSA mandate and provide an additional security layer.

### QKD in Submarine Fiber-Optic Cables

Submarine cables carry ~99% of intercontinental data traffic and are priority intelligence targets. QKD over submarine fiber faces distance limitations (transoceanic cables span 6,000-15,000 km, far beyond single-span QKD range). Trusted-node relay within submarine cable repeater housings is theoretically possible but operationally extremely challenging — these housings are on the ocean floor and serviced only by cable ships. Satellite QKD relay is more plausible for intercontinental key distribution.

### Airborne and Mobile QKD Platforms

Free-space QKD from aircraft is in early research stages. Challenges include vibration, platform motion, atmospheric turbulence at altitude, and the requirement for precise pointing. No operational airborne QKD system exists. Vehicular (ground mobile) QKD has been demonstrated in limited lab/testbed scenarios but is not field-deployable.

### NATO and Five Eyes Quantum Programs

NATO published its first Quantum Technologies Strategy in January 2024, outlining plans for a "quantum-ready" alliance. The strategy covers sensing, PNT (positioning, navigation, timing), computing, and communications. For communications, the focus is on both PQC transition and QKD for strategic links.

The DISCRETION project, co-funded by the European Defence Industrial Development Programme, deploys CV-QKD systems in Austria, Italy, Portugal, and Spain. The consortium has provided QKD services to Portuguese military clients. The project integrates QKD with software-defined networking (SDN) and analyzes software-defined radio (SDR) integration for tactical radio network segments.

SIPRI (Stockholm International Peace Research Institute) published a comprehensive primer on military and security dimensions of quantum technologies in July 2025, cataloging programs across Five Eyes and allied nations.

**Confidence Level:** Medium — military programs are partially classified; open-source information is incomplete
**Last Verified:** March 2026

---

## 3D. 5G/6G Network Infrastructure

### QKD for Securing 5G Fronthaul/Backhaul

5G network architecture separates the Radio Unit (RU), Distributed Unit (DU), and Centralized Unit (CU), connected by fronthaul and backhaul links that are typically fiber-based metro connections of 10-80 km — well within QKD operating range. These links carry both user data and network control signaling.

QKD can secure the fronthaul/backhaul by providing quantum-derived symmetric keys for link encryption. The key rates achievable over metro fiber (Mbps range) are sufficient for encrypting the signaling plane. The challenge is scaling to the density of 5G small cell deployments — each fiber link would require QKD equipment, and the cost per link makes this impractical for all but the highest-security segments (e.g., core network interconnects, connections to data centers).

### Quantum-Secured Network Slicing

5G network slicing creates logically isolated virtual networks over shared physical infrastructure. A quantum-secured slice could offer premium security guarantees for government, defense, or financial customers. QKD-derived keys would protect the slice's control plane and inter-slice isolation boundaries.

### Integration with SDN and NFV

Software-defined networking enables dynamic reconfiguration of QKD key routing and allocation. The QKD network can be managed as an SDN-controlled overlay, with a central controller allocating key resources based on application priority and security requirements. This is the approach taken by the DISCRETION project for military applications.

### 6G Vision Papers

Multiple 6G vision papers from Samsung Research, NGMN Alliance, and academic groups incorporate quantum communication natively into the 6G architecture. 3GPP has not yet standardized quantum integration, but GSMA introduced Post-Quantum Cryptography Guidelines in 2024 and is investigating QKD. The ITU-T Focus Group on Quantum Information Technology for Networks (FG-QIT4N) is developing recommendations. Research envisions quantum-safe 6G networks combining PQC for ubiquitous protection with QKD for high-security backbone segments.

**Confidence Level:** Medium — this domain is largely research/vision with limited deployments
**Last Verified:** March 2026

---

## 3E. Critical Infrastructure (SCADA/ICS/IoT)

### QKD for Securing SCADA Control Signals

SCADA systems controlling power grids, water systems, and pipelines represent high-value targets where the consequences of compromise are physical (equipment damage, safety hazards, environmental disasters). Legacy SCADA protocols (Modbus, DNP3) were designed without encryption. Even modern implementations using TLS or IPsec rely on key exchange mechanisms vulnerable to quantum attacks.

QKD integration into SCADA requires securing the communication links between control centers and substations/field devices. These links are often fiber-based metro connections — suitable for QKD. The bandwidth requirements for SCADA control signals are low (kbps), so even modest QKD key rates are more than sufficient.

### Demonstrated Deployments

The first use of QKD keys in smart grid authentication was demonstrated on a deployed electric utility fiber network. Researchers prototyped software to manage and utilize cryptographic keys for authenticating machine-to-machine SCADA communications. A system in Beijing has been deployed for high-voltage grid control, reportedly improving data security.

Research published in IEEE journals (2024) proposes integrating QKD with blockchain for smart grid authentication, combining QKD's key distribution with blockchain's tamper-evident logging to strengthen both integrity and authentication.

### Challenges

**Legacy systems:** Many SCADA/ICS devices cannot be upgraded to support new cryptographic protocols. QKD would need to be integrated at the network gateway level, encrypting traffic between zones rather than at individual device endpoints.

**Geographic distribution:** Some critical infrastructure spans large geographic areas (pipelines, power transmission lines). Point-to-point QKD links to every substation may be cost-prohibitive; a hub-and-spoke model with QKD securing the most critical central links and PQC protecting peripheral connections may be more practical.

**Low bandwidth, high criticality:** SCADA control signals are small but their integrity is paramount. QKD key rates, even at low levels, far exceed SCADA bandwidth requirements.

### QKD-Secured IoT Gateways

IoT devices themselves are too resource-constrained for QKD receivers. The practical model is QKD-secured gateways: IoT devices communicate with a local gateway using conventional (PQC or symmetric) encryption, and the gateway-to-cloud or gateway-to-control-center link is secured with QKD-derived keys. This concentrates the cost of QKD equipment at aggregation points.

**Confidence Level:** Medium — limited pilot deployments, mostly research
**Last Verified:** March 2026

---

## 3F. RF & Wireless Signal Security

### Quantum-Secured RF Key Distribution — Feasibility

QKD over RF (radio frequency) channels is not feasible with current technology. QKD requires either single-photon-level optical signals in fiber or free-space optical line-of-sight paths. The RF spectrum does not support the quantum states used in QKD protocols.

### Hybrid Approaches: QKD over Fiber + Symmetric Key Use over RF

The practical architecture is: QKD establishes shared symmetric keys between fixed infrastructure nodes over fiber, and those keys are then used to encrypt RF communications. This requires a key distribution infrastructure that bridges the fiber-connected QKD backbone to the wireless endpoints. Key pre-loading (distributing QKD-derived keys to mobile devices before deployment) or PQC-secured key transport over wireless links are the primary mechanisms.

### Quantum Radar and Quantum Sensing

While not QKD, quantum radar (quantum illumination) and quantum sensing are adjacent technologies relevant to RF signal security:

**Quantum illumination:** Uses entangled photon pairs to detect objects in noisy environments with improved signal-to-noise ratios compared to classical radar. Theoretical advantages exist but practical implementations are extremely limited. Not deployable for decades in operational military systems.

**Quantum sensing:** Highly sensitive magnetometers, gravimeters, and atomic clocks with applications in submarine detection, navigation without GPS, and spectrum monitoring. More mature than quantum radar and with nearer-term military applications.

### Electronic Warfare Implications

Quantum technologies may eventually impact electronic warfare: quantum communications channels resistant to jamming (though not immune), quantum-enhanced spectrum sensing for signal intelligence, and quantum random number generators for more unpredictable frequency hopping sequences. These remain speculative and are not deployable in the near term.

**Confidence Level:** Low to Medium — this domain is primarily theoretical/speculative for QKD
**Last Verified:** March 2026

---

## Sources

1. [Toshiba-Orange QKD over DWDM](https://www.telecomstechnews.com/news/2024/feb/22/toshiba-orange-demo-quantum-secure-fibre-data-transmission/)
2. [Quantum Corridor/Toshiba cross-state QKD](https://news.toshiba.com/press-releases/press-release-details/2025/Quantum-Corridor-Toshiba-Demonstrate-First-Cross-State-Quantum-Key-Distribution-Over-Live-Commercial-Metro-Fiber-Network/default.aspx)
3. [PacketLight-Toshiba QKD over DWDM](https://www.packetlight.com/about/press-releases/packetlight-announce-successful-demonstration-of-qkd-over-dwdm-links-with-toshiba)
4. [NATO Quantum Technologies Strategy](https://www.nato.int/cps/en/natohq/official_texts_221777.htm)
5. [DISCRETION project - NATO STO](https://www.sto.nato.int/document/discretion-quantum-secure-communications-for-european-defence/)
6. [SIPRI quantum technologies primer](https://www.sipri.org/sites/default/files/2025-07/0725_military_and_security_dimensions_of_quantum_technologies_0.pdf)
7. [Smart grid QKD authentication - Scientific Reports](https://www.nature.com/articles/s41598-022-16090-w)
8. [QKD + blockchain for smart grid - IEEE](https://ieeexplore.ieee.org/document/10591785/)
9. [Quantum-safe networks for 6G survey](https://www.scifiniti.com/3104-4719/2/2025.0016)
10. [Quantum technologies for beyond 5G/6G](https://arxiv.org/html/2504.17133v1)
11. [Samsung Research quantum security for future networks](https://research.samsung.com/blog/Quantum-Security-for-Future-Communication-Networks-Standards-Perspective)
12. [5G Americas quantum preparedness](https://www.5gamericas.org/preparing-wireless-networks-for-the-quantum-computing-era/)
13. [CV-QKD coexistence 120 km - PRL](https://link.aps.org/doi/10.1103/zy2d-m3ch)
14. [Satellite QKD global race - SPIE](https://spie.org/news/photonics-focus/janfeb-2025/racing-for-quantum-supremacy-in-space)
15. [QEYSSat - Canadian Space Agency](https://www.asc-csa.gc.ca/eng/satellites/qeyssat.asp)
16. [Micius Beijing-South Africa link](https://spie.org/news/photonics-focus/janfeb-2025/racing-for-quantum-supremacy-in-space)
