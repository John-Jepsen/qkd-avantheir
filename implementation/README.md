# QKD Implementation

A runnable Python stack that emulates the QKD key delivery pipeline described
in the project documentation. No quantum hardware required — the BB84 protocol
is simulated in software.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      bb84_simulator.py                      │
│   Alice ──quantum channel──► Bob   (sifting, QBER, PA)      │
│                        │                                     │
│                  256-bit key out                             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      kme_server.py                          │
│   ETSI GS QKD 014 REST API  (Flask)                         │
│   GET  /enc_keys  →  key_ID + key_bytes  →  master SAE      │
│   POST /dec_keys  →  key_bytes (by ID)   →  slave SAE       │
└──────────┬──────────────────────────────────────┬───────────┘
           │ key_ID + key_bytes                   │ key_bytes (by ID)
           ▼                                      ▼
┌──────────────────┐                   ┌──────────────────────┐
│  Alice (client)  │── key_ID ────────►│  Bob (server)        │
│  tls_psk_demo.py │                   │  tls_psk_demo.py     │
│  AES-256-GCM enc │◄── encrypted ────►│  AES-256-GCM dec     │
└──────────────────┘                   └──────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `bb84_simulator.py` | BB84 protocol: qubit exchange, sifting, QBER, error correction, privacy amplification |
| `kme_server.py` | ETSI GS QKD 014 REST API backed by BB84 simulator |
| `tls_psk_demo.py` | End-to-end PSK demo: Alice and Bob fetch the same key, encrypt a message |
| `ikev2_ppk_config.md` | strongSwan IKEv2 configuration guide for RFC 8784 PPK |

## Requirements

```bash
pip install flask requests cryptography
```

Python 3.10+ required.

## Quick start

### 1 — Run the BB84 simulator standalone

```bash
python bb84_simulator.py
```

Output shows three scenarios: normal channel, noisy channel, and active
eavesdropper (which causes the protocol to abort).

### 2 — Run the KME server

```bash
python kme_server.py
```

The server starts on `http://127.0.0.1:5000` and pre-generates 50 keys from
the BB84 simulator. It refills automatically in the background as keys are
consumed.

```bash
# Check status
curl http://127.0.0.1:5000/api/v1/keys/sae-bob/status

# Fetch a key (master SAE)
curl http://127.0.0.1:5000/api/v1/keys/sae-bob/enc_keys
```

### 3 — Run the PSK demo

With the KME server running, open two additional terminals:

```bash
# Terminal 2 — Bob (server/responder)
python tls_psk_demo.py server

# Terminal 3 — Alice (client/initiator)
python tls_psk_demo.py client
```

Alice fetches a key from the KME, sends the key_ID to Bob, Bob retrieves
the matching key from the KME, and they exchange an AES-256-GCM encrypted
message. No Diffie-Hellman occurs anywhere in this flow.

### 4 — IKEv2 integration

See `ikev2_ppk_config.md` for step-by-step strongSwan configuration using
keys dispensed by the KME server.

---

## How it maps to production QKD

| This simulation | Real deployment |
|----------------|----------------|
| `bb84_simulator.py` | Physical QKD hardware (Toshiba, ID Quantique, etc.) |
| Single `kme_server.py` | Paired KMEs at each end, synchronized via quantum channel |
| `key_ID` sent over TCP | `key_ID` exchanged via management plane or IKE negotiation |
| AES-256-GCM channel | TLS 1.3 external PSK (RFC 8446), IKEv2 PPK (RFC 8784), or ETSI service mesh rekeying |

The ETSI GS QKD 014 API is identical in both cases — applications see the
same REST interface regardless of whether keys come from simulation or hardware.
