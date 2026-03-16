# QKD System Architecture Diagram

Supplements `capstone-outline.md`. Shows the full key delivery pipeline including the dual-KME deployment, trusted-node relay network, hybrid QKD+ML-KEM key derivation, and metrics monitoring.

---

## Core Key Delivery Pipeline

```mermaid
flowchart TD
    subgraph QKD_PHYS["QKD Physical Layer"]
        ALICE["Alice's QKD Node\n(photon source)"]
        BOB["Bob's QKD Node\n(photon detector)"]
        ALICE -- "quantum fiber · BB84 protocol" --> BOB
    end

    subgraph POSTPROC["Post-Processing / Distillation Pipeline"]
        direction LR
        P1["Basis\nSifting"] --> P2["QBER\nEstimation"] --> P3["Error Correction\n(Cascade)"] --> P4["Privacy\nAmplification\n(BLAKE2b)"] --> P5["256-bit\nSymmetric Key"]
    end

    QKD_PHYS -- "raw key bits" --> POSTPROC

    subgraph KME_A["KME-Alice — ETSI GS QKD 014\nkme_dual.py --role alice  (port 5001)"]
        SIM_A["bb84_simulator.py"]
        POOL_A["Key Pool\n(available / pending)"]
        API_A["REST API\nGET /enc_keys\nGET /status"]
        METRICS["metrics.py\nMetricsCollector\n(QBER · key rate · pool)"]
        SIM_A --> POOL_A --> API_A
        POOL_A -. "records session" .-> METRICS
    end

    subgraph KME_B["KME-Bob — ETSI GS QKD 014\nkme_dual.py --role bob  (port 5002)"]
        POOL_B["Key Pool\n(pending / synced)"]
        API_B["REST API\nPOST /dec_keys\nPOST /peer/sync_keys"]
        POOL_B --> API_B
    end

    POSTPROC -- "key material" --> KME_A
    API_A -- "POST /peer/sync_keys\n(key_ID + key_bytes)\nbest-effort · background thread" --> KME_B

    subgraph APP_A["Application Layer — Master SAE (Alice)"]
        TLS_A["TLS 1.3 PSK\n(RFC 8446)"]
        IPSEC_A["IPsec/IKEv2 PPK\n(RFC 8784)"]
        MESH_A["Service Mesh mTLS\n(ETSI QKD 014)"]
    end

    subgraph APP_B["Application Layer — Slave SAE (Bob)"]
        TLS_B["TLS 1.3 PSK\n(RFC 8446)"]
        IPSEC_B["IPsec/IKEv2 PPK\n(RFC 8784)"]
        MESH_B["Service Mesh mTLS\n(ETSI QKD 014)"]
    end

    API_A -- "key_ID + key_bytes\n(enc_keys)" --> APP_A
    API_B -- "key_bytes by ID\n(dec_keys)" --> APP_B
    APP_A -- "key_ID sent\nout-of-band" --> APP_B
    APP_A <-- "AES-256-GCM\nencrypted channel" --> APP_B

    subgraph HYBRID["Hybrid Layer — hybrid_kdf.py (Optional)"]
        QKD_K["QKD Key\n(from KME)"]
        PQC_K["ML-KEM Ciphertext\n(MockMLKEM / Kyber-768\nFIPS 203)"]
        HKDF_BOX["HKDF-SHA256\nIKM = qkd_key ∥ kem_secret\n(ETSI TS 104 015 · RFC 9794)"]
        COMBINED["256-bit Combined\nSecret"]
        QKD_K & PQC_K --> HKDF_BOX --> COMBINED
    end

    API_A -.-> HYBRID
```

---

## Trusted-Node Relay Network

```mermaid
flowchart LR
    subgraph NET["QKDRelayNetwork — relay_network.py"]
        direction LR

        subgraph N0["Node: NYC"]
            NK0["KME\n(BB84 link keys)"]
        end
        subgraph N1["Node: Chicago\n(trusted relay)"]
            NK1["decode K_AB\nre-encode K_BC"]
        end
        subgraph N2["Node: Denver\n(trusted relay)"]
            NK2["decode K_BC\nre-encode K_CD"]
        end
        subgraph N3["Node: LA"]
            NK3["decode K_CD\n→ session_key"]
        end

        N0 -- "BB84 link key K_AB\n(connect)" --> N1
        N1 -- "BB84 link key K_BC\n(connect)" --> N2
        N2 -- "BB84 link key K_CD\n(connect)" --> N3

        N0 -- "payload = session_key ⊕ K_AB" --> N1
        N1 -- "session_key ⊕ K_BC" --> N2
        N2 -- "session_key ⊕ K_CD" --> N3
    end

    SRC(["relay_key('NYC','LA')\nsource generates\nfresh session_key"]) --> N0
    N3 --> DST(["recovered session_key\n= original ✓"])
```

> **Security note:** each trusted relay node transiently holds the session key in cleartext. End-to-end security requires physical security at every node. This is the same model used in the Beijing-Shanghai backbone (BSBN) and EuroQCI.

---

## Hybrid Key Exchange Flow

```mermaid
sequenceDiagram
    participant KME as KME (ETSI 014)
    participant Alice as Alice (HybridKeyExchange)
    participant Bob as Bob (HybridKeyExchange)

    KME-->>Alice: qkd_key (enc_keys)
    KME-->>Bob: qkd_key (dec_keys, same key_ID)

    Note over Alice: alice.initiate()
    Alice->>Alice: MockMLKEM.keygen() → (pk, sk)
    Alice->>Alice: MockMLKEM.encapsulate(pk) → (ct, kem_secret)
    Alice->>Alice: HKDF(qkd_key ∥ kem_secret) → combined_key

    Alice->>Bob: send (pk, ct) out-of-band

    Note over Bob: bob.respond(pk, ct)
    Bob->>Bob: MockMLKEM.decapsulate(sk, ct) → kem_secret
    Bob->>Bob: HKDF(qkd_key ∥ kem_secret) → combined_key

    Note over Alice,Bob: combined_key matches — secure if either QKD or ML-KEM is unbroken
```
