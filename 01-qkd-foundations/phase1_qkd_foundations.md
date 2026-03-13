# Phase 1: Foundational QKD Landscape

## 1.1 Core QKD Protocols

### BB84 (Bennett-Brassard, 1984)

**Mechanism:** Alice encodes random bits using one of two conjugate bases (rectilinear or diagonal polarization). Bob measures each photon in a randomly chosen basis. After transmission, they publicly compare basis choices and discard mismatched measurements (sifting). The remaining correlated bits undergo error correction and privacy amplification to yield a secure shared key.

**Security basis:** The no-cloning theorem prevents an eavesdropper from perfectly copying unknown quantum states. Any measurement by Eve introduces detectable disturbance in the Quantum Bit Error Rate (QBER). Security proofs hold against general coherent attacks in the asymptotic and finite-key regimes.

**Key generation rates:** Commercial systems achieve 1-10 Mbps at short metro distances (10-20 km), dropping to low kbps at 100+ km. Toshiba demonstrated 63+ Mbps using multi-pixel SNSPDs over short spans.

**Maximum demonstrated distances:** Standard BB84 variants reach approximately 200-250 km in fiber before key rates become impractical. The fundamental limit is the Pirandola-Laurenza-Ottaviani-Banchi (PLOB) bound of the repeaterless secret-key capacity.

**Known vulnerabilities:** Photon-number splitting (PNS) attacks exploit multi-photon emissions from weak coherent pulse sources. Mitigation: decoy-state BB84, which uses varying intensity levels to detect PNS. Detector blinding attacks manipulate single-photon detectors into classical linear mode. Trojan horse attacks inject light to probe internal states.

### E91 (Ekert, 1991)

**Mechanism:** An entangled photon pair source distributes one photon to Alice and one to Bob. Both measure in randomly chosen bases. Bell inequality violations confirm entanglement and detect eavesdropping. Correlated measurement outcomes form the raw key.

**Security basis:** Violations of Bell's inequality (specifically CHSH inequality) certify that the measured correlations cannot arise from classical local hidden variables or from an eavesdropper's intervention. Security is device-independent in principle — the protocol's guarantees hold regardless of the internal workings of the devices.

**Key generation rates:** Generally lower than BB84 due to the challenges of generating, distributing, and detecting entangled pairs with high fidelity. Typical rates are in the 100 bps to low kbps range at metropolitan distances.

**Maximum distances:** Comparable to BB84 in fiber. Entanglement-based QKD over satellite demonstrated by China's Micius satellite at 1,200 km (free-space).

**Known vulnerabilities:** Source imperfections (non-ideal entanglement), detector loopholes, and multi-pair emissions. Full device-independent security requires closing both detection and locality loopholes simultaneously, which remains experimentally challenging.

### B92 (Bennett, 1992)

**Mechanism:** A simplified protocol using only two non-orthogonal quantum states (rather than BB84's four). Alice sends one of two states; Bob performs an unambiguous state discrimination measurement. Conclusive results yield key bits.

**Security basis:** Non-orthogonality ensures that no measurement can perfectly distinguish the two states, preventing undetected eavesdropping.

**Key generation rates and distances:** Lower efficiency than BB84 due to the higher discard rate in sifting. Less commonly deployed commercially.

**Known vulnerabilities:** More susceptible to PNS attacks than BB84 because the two-state encoding provides Eve with more information per intercepted photon.

### SARG04 (Scarani-Acin-Ribordy-Gisin, 2004)

**Mechanism:** Uses the same four states as BB84 but a different sifting procedure. Instead of announcing measurement bases, Alice announces a pair of non-orthogonal states, one of which she sent. Bob's conclusive/inconclusive measurement determines whether the bit is kept.

**Security basis:** The modified sifting makes PNS attacks significantly less effective against weak coherent pulse implementations.

**Key generation rates:** Comparable to BB84 for single-photon sources but with improved robustness against multi-photon emissions, making it advantageous for practical lasers without decoy states.

### Continuous-Variable QKD (CV-QKD)

**Mechanism:** Encodes key information in the continuous quadratures (amplitude and phase) of coherent light states. Detection uses standard homodyne or heterodyne receivers rather than single-photon detectors.

**Security basis:** Heisenberg uncertainty principle prevents simultaneous precise measurement of conjugate quadratures. Security proofs exist against collective and general attacks in the asymptotic regime, with finite-size analyses maturing rapidly.

**Key generation rates:** At short distances (25 km), recent systems achieved composable key rates of 18.93 Mbps, surpassing previous CV-QKD systems by over an order of magnitude and becoming competitive with advanced DV-QKD. At longer distances, rates decrease but the 100-120 km barrier has been crossed.

**Maximum distances:** 100 km with local local oscillator achieved in 2024; 120 km coexisting with fully populated CWDM classical traffic demonstrated in 2025.

**Known vulnerabilities:** Local oscillator attacks (mitigated by locally generated LO designs), excess noise from the classical channel in co-propagation scenarios, and finite-size effects that reduce practical security margins.

**Commercial status:** LuxQuanta released its second-generation NOVA LQ CV-QKD system in March 2025. The DE-QOR project in Germany demonstrated a fully operational CV-QKD system with advanced LDPC codes. CV-QKD's compatibility with standard telecom components (coherent receivers, commercial lasers) gives it a strong cost and integration advantage for metro-scale networks.

### Measurement-Device-Independent QKD (MDI-QKD)

**Mechanism:** Both Alice and Bob send quantum states to an untrusted central relay node (Charlie) that performs a Bell-state measurement. Charlie's measurement results are publicly announced, but he never learns the key bits. The protocol removes all detector-side attacks by design.

**Security basis:** Security relies on the preparation of quantum states at Alice and Bob, not on the measurement apparatus. Even a fully compromised relay cannot extract key information.

**Key generation rates:** Lower than standard BB84 at equivalent distances due to the requirement for two-photon interference at the relay. However, multi-user MDI-QKD networks achieved 267 bps per user pair at ~30 dB attenuation using optical frequency combs (January 2025).

**Maximum distances:** MDI-QKD with flawed state preparation demonstrated over 303 km (2025).

**Deployment milestone:** Q*Bird deployed the first cross-border MDI-QKD link in Europe connecting Belgium and Luxembourg (132 km, four nodes) as part of EuroQCI in June 2025.

### Twin-Field QKD (TF-QKD)

**Mechanism:** A variant where Alice and Bob send phase-encoded weak coherent pulses to a central untrusted node that performs single-photon interference (rather than two-photon Bell measurement as in MDI-QKD). This enables key rates that scale as the square root of channel transmittance — overcoming the PLOB bound without quantum repeaters.

**Security basis:** Single-photon interference at the relay node; the untrusted node gains no key information. Security proofs cover the sending-or-not-sending (SNS) and phase-matching variants.

**Key generation rates:** At 1,002 km, the rate was 0.0034 bps (laboratory). At practical metro distances (<100 km), TF-QKD can achieve significantly higher rates than standard protocols at equivalent loss.

**Maximum distances:** Current world record for fiber-based QKD: 1,002 km (USTC, May 2023) using ultra-low-loss fiber (0.16 dB/km) and SNSPDs with dark count rates of ~0.02 cps. Previous record: 833.8 km (2022).

**Known vulnerabilities:** Practical security concerns include acousto-optic modulator vulnerabilities and wavelength-switching attacks (identified and mitigated in January 2025). Requires precise phase stabilization between Alice and Bob's lasers.

**Data Points:**

| Protocol | Max Distance (Fiber) | Typical Key Rate (Metro) | Security Model | Commercial Availability |
|----------|---------------------|-------------------------|----------------|------------------------|
| BB84 (decoy-state) | ~250 km | 1-10 Mbps @ 20 km | Computational + IT security | Widely available |
| E91 | ~1,200 km (satellite) | 100 bps - low kbps | Device-independent (theory) | Research/limited |
| CV-QKD | 120 km | 18.93 Mbps @ 25 km | IT security (proofs maturing) | Emerging (LuxQuanta, etc.) |
| MDI-QKD | 303 km | 267 bps @ 30 dB | Removes detector attacks | Q*Bird Falqon |
| TF-QKD | 1,002 km (lab) | Higher than BB84 at equiv. loss | Overcomes PLOB bound | Pre-commercial |

**Confidence Level:** High — based on peer-reviewed publications in Nature, PRL, and npj Quantum Information.
**Last Verified:** March 2026 (search results through early 2026)

---

## 1.2 QKD Hardware Components

### Single-Photon Sources

Practical QKD systems predominantly use attenuated laser pulses (weak coherent pulses) with decoy-state protocols rather than true single-photon sources. Quantum dot single-photon sources are progressing in research but are not yet standard in commercial QKD. Entangled photon pair sources based on spontaneous parametric down-conversion (SPDC) are used for entanglement-based protocols.

### Single-Photon Detectors

Two primary technologies dominate:

**Single-Photon Avalanche Diodes (SPADs):** Semiconductor-based, operating at telecom wavelengths (InGaAs/InP). Lower detection efficiency (~10-25%) but compact, no cryogenics required for gated operation, and lower cost. Used in most commercial QKD systems.

**Superconducting Nanowire Single-Photon Detectors (SNSPDs):** Offer detection efficiencies exceeding 90%, ultra-low dark count rates (~0.01-1 cps), and timing jitter below 15 ps. Require cryogenic cooling (~2.5 K). Critical for long-distance and high-rate QKD. The SNSPD market is projected to reach $45.39 million by 2030 (CAGR 8.66%).

**Key vendors:** ID Quantique (SPADs and SNSPDs, Geneva; acquired by IonQ for $250M in February 2025), Single Quantum (multi-channel SNSPDs, >90% efficiency), Pixel Photonics (waveguide-integrated SNSPDs for QKD). ID Quantique and University of Geneva achieved >1.5 GHz detection rates with multi-pixel SNSPDs enabling QKD at >63 Mbps.

### Quantum Random Number Generators (QRNGs)

QRNGs exploit quantum processes (vacuum fluctuations, photon arrival times, beam splitting) to produce certifiably random numbers. Essential for generating the random basis choices and bit values in QKD protocols. Commercial products include ID Quantique's (now IonQ) Quantis series and QuintessenceLabs' qStream.

### Optical Modulators and Components

Phase modulators, intensity modulators, polarization controllers, optical switches, and wavelength filters are standard telecom-grade components used in QKD transmitters and receivers. CV-QKD's ability to use entirely standard coherent telecom components is a significant cost advantage.

**Confidence Level:** High
**Last Verified:** March 2026

---

## 1.3 QKD Network Architectures

### Point-to-Point Links

The simplest architecture: a direct quantum channel (dark fiber or dedicated wavelength in DWDM) between two endpoints. Key rates depend on distance and channel loss. Most commercial deployments today are point-to-point metro links.

### Trusted-Node Networks

For distances exceeding single-link QKD range, intermediate nodes perform key relay. Each hop runs QKD independently; the intermediate (trusted) node decrypts the key from one link and re-encrypts it for the next. Security depends on physical security at every node — trusted nodes see plaintext key material during relay. This is the architecture of China's Beijing-Shanghai backbone and most current long-distance QKD networks.

### Quantum Repeater Architectures

True quantum repeaters would enable end-to-end entanglement distribution without trusted nodes, using quantum memories, entanglement swapping, and entanglement distillation. Two approaches are under development: memory-based repeaters (using matter-based quantum memories) and all-photonic repeaters (using cluster states). Neither is deployment-ready.

**Recent milestones:** AWS-Harvard demonstrated entanglement between two quantum memory nodes across 35 km of deployed fiber in Boston using silicon-vacancy centers in diamond, with storage exceeding one second (2024). Integrated quantum memories achieved 1.021 ms storage in europium-doped crystals.

**Timeline projection:** Local quantum networks demonstrating repeater functionality by ~2025-2027; metro-scale networks (hundreds of km, few repeater hops) by ~2030; national/international networks combining fiber repeaters, undersea quantum links, and satellites in the 2030s.

### Satellite-Based QKD

Overcomes fiber distance limitations using free-space optical links. LEO satellites can distribute keys to ground stations separated by thousands of kilometers.

**China's Micius:** Launched 2016. Demonstrated QKD at 1,200 km, entanglement distribution at 1,200 km, quantum teleportation, and a 7,600 km intercontinental video conference (Beijing-Vienna). By 2025, achieved a ~12,800 km Beijing-South Africa link — the first quantum-secure link crossing hemispheres. China aims for a global quantum communications satellite constellation by 2027.

**European programs:** Eagle-1 (ESA-backed, first European QKD satellite demonstrator) scheduled for launch in 2026. Part of the EuroQCI initiative.

**Canada QEYSSat:** ~100 kg microsatellite for ground-to-space QKD, launching late 2026. QEYnet received CA$1.4M to test low-cost quantum satellite links.

### Hybrid Classical-Quantum Networks

Practical deployments co-locate QKD equipment with existing classical network infrastructure. Key material from QKD is mixed with classically derived keys (PQC or ECDHE) through a KDF for defense-in-depth. Failover to classical-only key exchange when QKD links are unavailable. This is the recommended deployment model per the existing Avantheir documentation.

**Confidence Level:** High
**Last Verified:** March 2026

---

## 1.4 Current Global QKD Deployments

### China — National Quantum Backbone

China operates the world's largest QKD network, designated CN-QCN (China Quantum Communication Network):

- Fiber backbone spanning over 12,000 km combined with the Beijing-Shanghai backbone (BSBN), covering 17 provinces and 80 cities
- 145 fiber backbone nodes and 20 metropolitan networks
- Carrier-grade QKD deployment validated over 10,000 km
- Hefei hosts the world's most extensive metropolitan quantum communication network
- Platforms "Quantum Secret" and "Quantum Cloud Seal" serve hundreds of government agencies and state-owned enterprises
- China Telecom launched a hybrid QKD+PQC encryption system in May 2025, enabling 1,000 km quantum-encrypted phone calls between Beijing and Hefei, deployed across 16 cities
- In June 2025, a 300 km quantum secure direct communication (QSDC) network was demonstrated

### European Union — EuroQCI

The European Quantum Communication Infrastructure initiative involves all 27 EU Member States and ESA:

- **Terrestrial segment:** National QCI networks (NatQCIs) deployed across Member States; now interconnecting via cross-border links. IonQ delivered a nationwide QKD network in Romania spanning 36 quantum-secured links over 1,500 km connecting six metropolitan areas
- **Space segment:** Eagle-1 satellite launch planned for 2026; ground stations linking to the satellite in Greece, Cyprus, and the Netherlands
- **Cross-border milestones:** Q*Bird achieved the first cross-border MDI-QKD link in the Benelux region (Belgium-Luxembourg, 132 km, June 2025)
- **SEEWQCI project:** EUR 17.8 million budget for South-Eastern and Western European cross-border quantum links, officially launched February 2026
- **Operational target:** Pilot facility for European Quantum Internet in 2026; fully operational quantum-safe network by 2030

### United States — DOE and National Testbeds

- **Chicago Quantum Exchange:** 52-mile (84 km) fiber testbed between Argonne National Laboratory and suburban Bolingbrook — among the longest ground-based quantum communication channels in the country
- **IEQNET (Illinois-Express Quantum Network):** Multi-node network connecting Fermilab, Northwestern University, and Argonne via existing classical infrastructure (Starlight)
- **ESnet:** DOE's Energy Sciences Network operates a three-node quantum network testbed for applied research
- **AWS-Harvard:** Demonstrated entanglement between quantum memory nodes across 35 km of deployed Boston-area fiber (2024)

### Japan

- **QKD network testbed:** Tokyo area QKD network operated by NICT since 2010
- **Toshiba demonstrations:** Cross-state QKD over 21.8 km of live commercial fiber (Quantum Corridor, December 2025); KDDI-Toshiba multiplexed 33.4 Tbps with quantum keys over 80 km (March 2025)

### South Korea

- SK Telecom operates QKD-secured links and has integrated quantum security into commercial telecom infrastructure.

### United Kingdom

- **UK NQCC (National Quantum Computing Centre)** and Quantum Communications Hub at University of York
- BT has deployed QKD links and participated in European cross-border trials

**Data Points:**

| Network | Country/Region | Scale | Status (2025-26) |
|---------|---------------|-------|-------------------|
| CN-QCN + BSBN | China | 12,000+ km, 80 cities | Operational, carrier-grade |
| EuroQCI (terrestrial) | EU-27 | Cross-border links deploying | Transitioning to operational |
| Eagle-1 (satellite) | EU/ESA | LEO QKD demonstrator | Launch 2026 |
| Chicago QE | USA | 84 km testbed | Operational testbed |
| IEQNET | USA | Multi-node, Chicago area | Research operational |
| Romania QKD | Romania/EU | 1,500 km, 36 links | Operational |
| Tokyo QKD | Japan | Metro network | Operational testbed |

**Confidence Level:** High
**Last Verified:** March 2026

---

## Sources

1. [Experimental TF-QKD over 1000 km - Physical Review Letters](https://link.aps.org/doi/10.1103/PhysRevLett.130.210801)
2. [TF-QKD over 830-km fibre - Nature Photonics](https://www.nature.com/articles/s41566-021-00928-2)
3. [MDI-QKD network with optical frequency combs - npj Quantum Information](https://www.nature.com/articles/s41534-025-01052-7)
4. [MDI-QKD over 303 km with flawed state-preparation - EPJ Quantum Technology](https://link.springer.com/article/10.1140/epjqt/s40507-025-00408-4)
5. [Q*Bird cross-border MDI-QKD in Benelux](https://q-bird.com/press/fortifying-europes-quantum-communication-qbird-and-beqci-achieve-the-first-cross-border-mdi-qkd-link-in-benelux/)
6. [CV-QKD over 100 km with local LO - Science Advances](https://www.science.org/doi/10.1126/sciadv.adi9474)
7. [CV-QKD coexistence over 120 km - PRL](https://link.aps.org/doi/10.1103/zy2d-m3ch)
8. [Carrier-grade QKD over 10,000 km - npj Quantum Information](https://www.nature.com/articles/s41534-025-01089-8)
9. [EuroQCI initiative - European Commission](https://digital-strategy.ec.europa.eu/en/policies/european-quantum-communication-infrastructure-euroqci)
10. [EuroQCI 2026 operational status](https://wiot-group.com/think/en/news/think-wiot-euroqci-2026-quantum-secure-communications/)
11. [SEEWQCI project launch](https://grnet.gr/en/2026/03/06/pr-seewqci-building-crossborder-quantum-communication-infrastructure-2026/)
12. [IonQ Romania QKD network](https://quantumzeitgeist.com/ionq-quantum-key-distribution-qkd-network/)
13. [China Telecom hybrid QKD+PQC system](https://thequantuminsider.com/2025/05/20/china-telecom-launches-hybrid-quantum-safe-encryption-system-completes-1000-kilometer-secure-call/)
14. [AWS-Harvard quantum network](https://www.sdxcentral.com/news/chinese-researchers-demonstrate-scalable-quantum-repeater-for-fiber-networks/)
15. [ID Quantique quantum detection](https://www.idquantique.com/quantum-detection-systems/overview/)
16. [Single Quantum SNSPD](https://www.singlequantum.com/)
17. [Quantum Corridor / Toshiba cross-state QKD](https://news.toshiba.com/press-releases/press-release-details/2025/Quantum-Corridor-Toshiba-Demonstrate-First-Cross-State-Quantum-Key-Distribution-Over-Live-Commercial-Metro-Fiber-Network/default.aspx)
18. [Satellite QKD global race - SPIE](https://spie.org/news/photonics-focus/janfeb-2025/racing-for-quantum-supremacy-in-space)
19. [QEYSSat mission - Canadian Space Agency](https://www.asc-csa.gc.ca/eng/satellites/qeyssat.asp)
