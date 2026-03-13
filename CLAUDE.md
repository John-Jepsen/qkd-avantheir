# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Technical documentation for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure (TLS 1.3, IPsec/IKEv2, service mesh), part of the Avantheir initiative. This is a senior-led MSCS research deliverable, not a software project.

## Structure

Eight numbered markdown documents form a sequential narrative:

- **01-03**: QKD foundations (BB84, CV-QKD, MDI-QKD, TF-QKD, global deployments) and protocol integration (TLS PSK, IPsec RFC 8784, hybrid QKD+PQC)
- **04-05**: Service mesh symmetric rekeying (incl. SDN-controlled allocation) and ETSI QKD 014 key management
- **06-07**: Vendor analysis (Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs, IBM, Lockheed Martin) and operational constraints
- **08**: Full reference list

Phase research files (phase1-6, qkd_signal_research_complete.md) contain supporting research that informed the main documents.

The README references an `implementation/` directory (ETSI KME client, TLS PSK adapter, IKEv2 PPK config) that does not yet exist.

## Key Technical Context

- **Baseline protocol**: Discrete-Variable QKD (BB84-style); CV-QKD where cost/integration advantages apply; MDI-QKD for highest implementation security
- **Vendor coverage**: Toshiba, ID Quantique/IonQ, QuantumCTek, LuxQuanta, Q*Bird, QuintessenceLabs (Tier 1-2 QKD vendors) plus IBM (PQC/research) and Lockheed Martin (defense integration)
- **Standards**: RFC 8446 (TLS 1.3), RFC 8784 (IKEv2 mixed-PSK), ETSI GS QKD 004/014/015/016, ETSI TS 104 015 (hybrid), IETF RFC 9794 (hybrid terminology), NIST FIPS 203/204/205 (PQC)
- **Strategic framing**: QKD vs PQC is not either/or — the docs map where each is appropriate. Hybrid QKD+PQC is the recommended architecture for highest-assurance deployments.

## Writing Conventions

- Documents use tables for structured comparisons, ASCII diagrams for protocol flows
- Cross-references between documents are by filename (e.g., "see 05-key-management.md")
- Maintain the numbered prefix ordering when adding new documents
