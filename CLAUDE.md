# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Technical documentation for integrating Quantum Key Distribution (QKD) into enterprise security infrastructure (TLS 1.3, IPsec/IKEv2, service mesh), part of the Avantheir initiative. This is a senior-led MSCS research deliverable, not a software project.

## Structure

Eight numbered markdown documents form a sequential narrative:

- **01-03**: Theory (BB84/DV-QKD foundations) and protocol integration (TLS PSK, IPsec RFC 8784)
- **04-05**: Service mesh symmetric rekeying and ETSI QKD 014 key management
- **06-07**: Vendor analysis (IBM, Lockheed Martin) and operational constraints
- **08**: Full reference list

The README references an `implementation/` directory (ETSI KME client, TLS PSK adapter, IKEv2 PPK config) that does not yet exist.

## Key Technical Context

- **Baseline protocol**: Discrete-Variable QKD (BB84-style); CV-QKD only where it offers unique advantage
- **Vendor anchors**: IBM (foundational research) and Lockheed Martin (defense integration, QuintessenceLabs partnership)
- **Standards**: RFC 8446 (TLS 1.3), RFC 8784 (IKEv2 mixed-PSK), ETSI GS QKD 004/014
- IBM's commercial stance favors PQC (CRYSTALS-Kyber/Dilithium) over QKD; the docs acknowledge this tension

## Writing Conventions

- Documents use tables for structured comparisons, ASCII diagrams for protocol flows
- Cross-references between documents are by filename (e.g., "see 05-key-management.md")
- Maintain the numbered prefix ordering when adding new documents
