# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Technical documentation and working implementation for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure (TLS 1.3, IPsec/IKEv2, service mesh), part of the Avantheir initiative. This is a senior-led MSCS research deliverable. All five milestones are complete; the only remaining item is final presentation preparation.

## Structure

```
qkd-avantheir/
├── 01-qkd-foundations/         # BB84, CV-QKD, MDI-QKD, TF-QKD, global deployments
├── 02-tls-integration/         # TLS 1.3 PSK, hybrid QKD+PQC
├── 03-ipsec-ikev2-integration/ # IPsec RFC 8784, IKEv2 mixed-PSK
├── 04-service-mesh-auth/       # Symmetric rekeying, SDN-controlled allocation
├── 05-key-management/          # ETSI QKD 014 key management
├── 06-vendor-analysis/         # Toshiba, IDQ/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs, IBM, Lockheed
├── 07-operational-constraints/ # Operational constraints and limitations
├── 08-references/              # Full reference list
├── DOCS/
│   ├── capstone-outline.md     # Submission 2 outline with milestones and tech stack
│   ├── capstone-brief.md       # Concise project brief for submission
│   ├── vocab-study-guide.md    # QKD terminology reference (245 entries)
│   └── images/qkd-image.jpeg   # Architecture diagram
├── implementation/
│   ├── bb84_simulator.py       # BB84 protocol sim: sifting, QBER, Cascade, privacy amplification
│   ├── kme_server.py           # Flask ETSI GS QKD 014 REST API with thread-safe key pool
│   ├── tls_psk_demo.py         # End-to-end TLS PSK demo: Alice/Bob AES-256-GCM via KME
│   ├── ikev2_ppk_config.md     # strongSwan RFC 8784 PPK config guide
│   └── README.md               # Quick-start with three-terminal setup
└── research-outputs /          # Note: trailing space in directory name
    ├── qkd_signal_research_agent_prompt.md
    └── qkd_signal_research_complete.md
```

Each numbered directory (01–06) also contains a `phase*.md` supporting research file alongside the main document. Directories 07 and 08 have no phase file.

## Key Technical Context

- **Baseline protocol**: Discrete-Variable QKD (BB84-style); CV-QKD where cost/integration advantages apply; MDI-QKD for highest implementation security
- **Vendor coverage**: Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs (Tier 1-2 QKD vendors) plus IBM (PQC/research) and Lockheed Martin (defense integration)
- **Standards**: RFC 8446 (TLS 1.3), RFC 8784 (IKEv2 mixed-PSK), ETSI GS QKD 004/014/015/016, ETSI TS 104 015 (hybrid), IETF RFC 9794 (hybrid terminology), NIST FIPS 203/204/205 (PQC)
- **Strategic framing**: QKD vs PQC is not either/or — the docs map where each is appropriate. Hybrid QKD+PQC is the recommended architecture for highest-assurance deployments.
- **Implementation stack**: Python 3.10+, Flask, `cryptography` library, `requests`. QBER abort threshold: >11%.

## Writing Conventions

- Documents use tables for structured comparisons, ASCII diagrams for protocol flows
- Cross-references between documents are by filename (e.g., "see 05-key-management.md")
- Maintain the numbered prefix ordering when adding new documents
