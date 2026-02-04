# Vendor Analysis: IBM and Lockheed Martin

## 1. IBM

### Historical Contributions

IBM's involvement in quantum cryptography traces to the foundational work of the field:

| Contribution | Details |
|--------------|---------|
| **BB84 Protocol (1984)** | Charles Bennett (IBM) co-invented with Gilles Brassard |
| **First Experimental QKD (1992)** | IBM researchers demonstrated experimental quantum cryptography over 32cm free-space |
| **Theoretical Foundations** | Ongoing contributions to quantum information theory |

### Current Positioning

IBM's public security portfolio emphasizes **post-quantum cryptography (PQC)** over QKD for commercial deployments:

| Focus Area | IBM Stance |
|------------|-----------|
| Near-term quantum security | PQC (CRYSTALS-Kyber, CRYSTALS-Dilithium) |
| Long-term quantum networking | QKD in research context |
| Hybrid approaches | Combining classical, PQC, and quantum methods |

### IBM Quantum Resources

| Resource | URL | Description |
|----------|-----|-------------|
| IBM Think - Quantum Cryptography | https://www.ibm.com/think/topics/quantum-cryptography | Overview of quantum cryptography concepts |
| IBM Quantum Learning | https://learning.quantum.ibm.com/course/fundamentals-of-quantum-information/quantum-cryptography | Educational module on QKD basics |
| NIST QIS RFI Response (2018) | https://www.nist.gov/system/files/documents/2018/07/23/ibm_response_to_nist_qis_rfi.pdf | IBM's position on quantum information science |

### IBM Quantum Network

IBM operates the IBM Quantum Network, a global community of organizations using quantum computing:

- Access to IBM quantum systems
- Qiskit development framework
- Research collaborations

While focused on quantum computing rather than QKD, the network provides infrastructure relevant to quantum-safe cryptography research.

### Integration Relevance

For QKD integration projects:

| Asset | Applicability |
|-------|--------------|
| IBM's QKD research heritage | Theoretical grounding, protocol expertise |
| IBM Cloud Security | Potential future hybrid QKD+classical services |
| IBM Key Protect | Key management patterns (not QKD-native) |

### Limitations

- No commercial QKD hardware product line
- QKD not featured in current IBM Security portfolio
- Focus shifted to PQC for practical quantum-safe solutions

---

## 2. Lockheed Martin

### Documented Partnerships

| Partnership | Year | Details |
|-------------|------|---------|
| **QuintessenceLabs** | 2009 | Strategic investment in quantum cryptography company |

**Source:** [PRNewswire - Lockheed Martin Invests in Quantum Cryptography Company QuintessenceLabs](https://www.prnewswire.com/news-releases/lockheed-martin-invests-in-quantum-cryptography-company-quintessencelabs-62073047.html)

### Strategic Focus

Lockheed Martin's role in quantum security aligns with defense systems integration:

| Capability | Description |
|------------|-------------|
| Systems integration | Embedding quantum security into defense platforms |
| Ruggedization | Adapting quantum systems for operational environments |
| Platform integration | Aerospace, maritime, ground systems |
| Program management | Large-scale secure communication programs |

### QuintessenceLabs Partnership Details

QuintessenceLabs provides:

| Product/Technology | Description | URL |
|-------------------|-------------|-----|
| qOptica™ | QKD system | https://www.quintessencelabs.com/technology/quantum-key-distribution/ |
| qStream™ | Quantum random number generator | https://www.quintessencelabs.com/products/ |
| Trusted Security Foundation | Key management platform | https://www.quintessencelabs.com/products/ |

The Lockheed Martin investment signaled interest in quantum cryptography for defense applications.

### Defense and Government Context

| Initiative | Relevance |
|------------|-----------|
| NSA Commercial National Security Algorithm Suite | Transition guidance affecting defense contractors |
| CNSA 2.0 | Quantum-resistant algorithm requirements |
| Defense quantum initiatives | Multiple classified and unclassified programs |

### Integration Relevance

For QKD integration projects with defense/government requirements:

| Asset | Applicability |
|-------|--------------|
| QuintessenceLabs products | Evaluated QKD hardware option |
| Lockheed integration expertise | Complex system deployment |
| Defense accreditation experience | Security certification pathways |

### Limitations

- Specific deployments often classified
- Focus on defense/government, not commercial
- No direct QKD hardware manufacturing

---

## 3. Quantum Economic Development Consortium (QED-C)

Both IBM and Lockheed Martin participate in QED-C, the industry consortium coordinating quantum technology development in the US.

**URL:** https://quantumconsortium.org/

### QED-C Working Groups

| Working Group | Focus |
|---------------|-------|
| Standards | Quantum technology standardization |
| Use Cases | Application identification |
| Workforce | Training and education |
| Supply Chain | Component and system sourcing |

---

## 4. Other Relevant Vendors

While IBM and Lockheed Martin are anchor vendors, other QKD vendors merit consideration:

| Vendor | Headquarters | Product Focus |
|--------|--------------|---------------|
| ID Quantique | Switzerland | Commercial QKD systems, QRNGs |
| Toshiba | Japan/UK | QKD research and products |
| QuantumCTek | China | QKD infrastructure |
| MagiQ Technologies | USA | QKD systems |
| QuintessenceLabs | Australia | QKD, QRNG, key management |

### ID Quantique (Notable)

As market leader in commercial QKD:

| Product | Description |
|---------|-------------|
| Cerberis XG | QKD platform |
| Clavis XG | QKD link encryptor |
| Quantis | QRNG devices |

ID Quantique systems are deployed in commercial and government networks globally.

---

## 5. Vendor Selection Criteria

For QKD integration projects, evaluate vendors on:

| Criterion | Weight | Notes |
|-----------|--------|-------|
| Protocol compliance | High | ETSI GS QKD standards |
| Security certification | High | Common Criteria, FIPS where applicable |
| API compatibility | High | ETSI 014 REST API support |
| Range performance | Medium | Match deployment topology |
| Key generation rate | Medium | Meet consumption requirements |
| Integration support | Medium | Professional services availability |
| Ecosystem partnerships | Medium | Complementary vendors |
| Total cost of ownership | Medium | Hardware, fiber, operations |

---

## 6. Recommendation Summary

| Use Case | Primary Vendor Consideration |
|----------|------------------------------|
| Defense/Government | Lockheed Martin ecosystem (via QuintessenceLabs) |
| Research/Education | IBM Quantum resources, ID Quantique |
| Commercial deployment | ID Quantique, Toshiba, QuintessenceLabs |
| Hybrid QKD+PQC strategy | IBM (PQC) + QKD vendor |

## References

### IBM
- [IBM Think - Quantum Cryptography](https://www.ibm.com/think/topics/quantum-cryptography)
- [IBM Quantum Learning - QKD Module](https://learning.quantum.ibm.com/course/fundamentals-of-quantum-information/quantum-cryptography)
- [IBM NIST QIS RFI Response](https://www.nist.gov/system/files/documents/2018/07/23/ibm_response_to_nist_qis_rfi.pdf)

### Lockheed Martin / QuintessenceLabs
- [Lockheed Martin QuintessenceLabs Investment](https://www.prnewswire.com/news-releases/lockheed-martin-invests-in-quantum-cryptography-company-quintessencelabs-62073047.html)
- [QuintessenceLabs QKD Technology](https://www.quintessencelabs.com/technology/quantum-key-distribution/)

### Industry
- [QED-C Quantum Economic Development Consortium](https://quantumconsortium.org/)
