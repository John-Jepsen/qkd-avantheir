# QKD System Architecture Diagram

Supplements `capstone-outline.md`. Shows the full key delivery pipeline from QKD physical layer through post-processing, key management, and application integration to the optional hybrid layer.

```mermaid
flowchart TD
    subgraph QKD_PHYS["QKD Physical Layer"]
        ALICE["Alice's QKD Node\n(photon source)"]
        BOB["Bob's QKD Node\n(photon detector)"]
        ALICE -- "quantum fiber\nBB84 protocol" --> BOB
    end

    subgraph POSTPROC["Post-Processing / Distillation Pipeline"]
        direction LR
        P1["Basis\nSifting"] --> P2["QBER\nEstimation"] --> P3["Error Correction\n(Cascade)"] --> P4["Privacy\nAmplification"] --> P5["256-bit\nSymmetric Key"]
    end

    QKD_PHYS -- "raw key bits" --> POSTPROC

    subgraph KME["Key Management Entity — ETSI GS QKD 014"]
        SIM["bb84_simulator.py\n(software emulation)"]
        STORE["Key Store"]
        API["REST API\nGET /enc_keys\nPOST /dec_keys\nGET /status"]
        SIM --> STORE --> API
    end

    POSTPROC -- "key material" --> KME

    subgraph APP_A["Application Layer A (Master SAE)"]
        TLS_A["TLS 1.3 PSK\n(RFC 8446 §2.2)"]
        IPSEC_A["IPsec/IKEv2 PPK\n(RFC 8784)"]
        MESH_A["Service Mesh mTLS\n(ETSI QKD 014)"]
    end

    subgraph APP_B["Application Layer B (Slave SAE)"]
        TLS_B["TLS 1.3 PSK\n(RFC 8446 §2.2)"]
        IPSEC_B["IPsec/IKEv2 PPK\n(RFC 8784)"]
        MESH_B["Service Mesh mTLS\n(ETSI QKD 014)"]
    end

    API -- "key_ID + key_bytes" --> APP_A
    API -- "key_bytes by ID" --> APP_B

    APP_A <-- "encrypted channel" --> APP_B

    subgraph HYBRID["Hybrid Layer (Optional)"]
        QKD_K["QKD Key\n(from KME)"]
        PQC_K["PQC Key\n(ML-KEM / FIPS 203)"]
        HKDF["HKDF\n(ETSI TS 104 015 / RFC 9794)"]
        COMBINED["Combined\nSecret"]
        QKD_K & PQC_K --> HKDF --> COMBINED
    end

    API -.-> HYBRID
```
