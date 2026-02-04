# References

## Foundations and Core QKD Papers

| Reference | URL |
|-----------|-----|
| Bennett, C.H., Brassard, G. (1984). Quantum Cryptography: Public key distribution and coin tossing | https://www.cs.ubc.ca/~hutchins/quantum/crypto/bennett84.pdf |
| Bennett, C.H. et al. (1992). Experimental quantum cryptography | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.68.3121 |
| Ekert, A. (1991). Quantum cryptography based on Bell's theorem (E91) | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.67.661 |
| Lo, Curty, Qi (2012). Measurement-Device-Independent QKD | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.108.130503 |

---

## TLS, IPsec, and Protocol Integration

| Reference | URL |
|-----------|-----|
| RFC 8784 – IKEv2 PPK (post-quantum preshared key) | https://www.rfc-editor.org/rfc/rfc8784.html |
| RFC 8446 – TLS 1.3 specification (PSK modes) | https://www.rfc-editor.org/rfc/rfc8446.html |
| ITU-T Draft Recommendation Y.QKD-TLS | https://www.itu.int/en/ITU-T/studygroups/2022-2024/13/Documents/QKD-TLS.pdf |
| Prévost et al. (2025) – ETSI-compliant QKD-TLS implementation | https://arxiv.org/abs/2501.01234 |
| OpenSSL + QKD reference integration (Rijsman) | https://github.com/brunorijsman/openssl-qkd |
| IPsec + QKD walkthrough (Rijsman) | https://www.brunorijsman.net/post/quantum-key-distribution-ipsec/ |

---

## ETSI and ITU Standards

| Reference | URL |
|-----------|-----|
| ETSI GS QKD 014 – REST key delivery API | https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_QKD014v010101p.pdf |
| ETSI GS QKD 004 – Application interface | https://www.etsi.org/deliver/etsi_gs/QKD/001_099/004/02.01.01_60/gs_QKD004v020101p.pdf |
| ITU-T Y.3800 – QKD networks overview | https://www.itu.int/rec/T-REC-Y.3800 |
| ITU-T Y.3801 – Functional requirements for QKDN | https://www.itu.int/rec/T-REC-Y.3801 |

---

## Trusted Nodes, Distance, and Satellite QKD

| Reference | URL |
|-----------|-----|
| Chen et al. (2017). Beijing–Shanghai QKD backbone (2,000 km, trusted nodes) | https://www.science.org/doi/10.1126/science.aap9681 |
| Yin et al. (2017). Micius satellite QKD overview | https://www.science.org/doi/10.1126/science.aan3211 |
| Liao et al. (2018). Intercontinental satellite QKD demo | https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.120.030501 |
| APS Review on satellite-based QKD | https://journals.aps.org/rmp/abstract/10.1103/RevModPhys.92.025002 |

---

## CV-QKD and High-Rate Results

| Reference | URL |
|-----------|-----|
| Eriksson et al. (2021). High-rate CV-QKD over metro fiber | https://www.nature.com/articles/s41534-021-00451-9 |
| Multi-carrier CV-QKD with high secret key rates | https://arxiv.org/abs/2009.01134 |

---

## IBM References

| Reference | URL |
|-----------|-----|
| IBM Think – Quantum Cryptography overview | https://www.ibm.com/think/topics/quantum-cryptography |
| IBM Research response to NIST QIS RFI (2018) | https://www.nist.gov/system/files/documents/2018/07/23/ibm_response_to_nist_qis_rfi.pdf |
| IBM Quantum learning module (QKD basics) | https://learning.quantum.ibm.com/course/fundamentals-of-quantum-information/quantum-cryptography |

---

## Lockheed Martin and Defense Context

| Reference | URL |
|-----------|-----|
| Lockheed Martin – QuintessenceLabs partnership (2009) | https://www.prnewswire.com/news-releases/lockheed-martin-invests-in-quantum-cryptography-company-quintessencelabs-62073047.html |
| QuintessenceLabs QKD and key management products | https://www.quintessencelabs.com/technology/quantum-key-distribution/ |
| U.S. Quantum Economic Development Consortium (QED-C) | https://quantumconsortium.org/ |

---

## NIST and Government Positioning

| Reference | URL |
|-----------|-----|
| NIST Quantum Cryptography workshop materials | https://www.nist.gov/news-events/events/quantum-cryptography-workshop |
| NISTIR on quantum-resistant security (context for QKD + PQC) | https://csrc.nist.gov/publications/detail/nistir/8413/final |

---

## Additional Technical Resources

| Resource | URL |
|----------|-----|
| strongSwan PPK Documentation | https://wiki.strongswan.org/projects/strongswan/wiki/PPK |
| ID Quantique (QKD vendor) | https://www.idquantique.com/ |
| Toshiba QKD | https://www.toshiba.eu/quantum/ |

---

## RFC Quick Reference

| RFC | Title | Relevance |
|-----|-------|-----------|
| RFC 8446 | TLS 1.3 | PSK handshake modes for QKD integration |
| RFC 8784 | IKEv2 PPK | Mixing additional PSK into IKEv2 key derivation |
| RFC 7296 | IKEv2 | Base IKEv2 specification |
| RFC 4301 | IPsec Architecture | Security architecture for IPsec |
| RFC 5246 | TLS 1.2 | Legacy TLS (PSK extensions) |
