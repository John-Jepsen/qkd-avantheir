# IPsec/IKEv2 VPN Integration

## 1. Overview

IPsec uses IKEv2 to establish Security Associations (SAs). QKD integration uses IKEv2's ability to mix an additional shared secret into key derivation via the **Post-quantum Preshared Key (PPK)** mechanism defined in RFC 8784.

## 2. RFC 8784 PPK Mechanism

RFC 8784 defines how to incorporate an additional preshared key into IKEv2 key derivation without modifying the core protocol.

### Key Properties

| Property | Description |
|----------|-------------|
| Backwards compatible | Works with existing IKEv2 implementations |
| Defense in depth | PPK augments, doesn't replace, existing key exchange |
| Key ID based | Uses identifiers to coordinate key material |
| Quantum-resistant goal | Originally designed for PQC keys, equally applicable to QKD |

## 3. Integration Architecture

```
┌─────────────────┐                    ┌─────────────────┐
│   QKD System    │   Quantum Link     │   QKD System    │
│   (Site A)      │ ─────────────────► │   (Site B)      │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│      KME        │                    │      KME        │
│  (Key Manager)  │                    │  (Key Manager)  │
└────────┬────────┘                    └────────┬────────┘
         │ {key_bytes, key_id}                  │
         ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│   PPK Plugin    │                    │   PPK Plugin    │
│                 │                    │                 │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────┐   IKEv2 + PPK      ┌─────────────────┐
│  VPN Gateway    │ ◄────────────────► │  VPN Gateway    │
│  (Initiator)    │                    │  (Responder)    │
└─────────────────┘                    └─────────────────┘
```

## 4. IKEv2 + QKD Flow

### Phase 1: IKE_SA_INIT

```
Initiator                              Responder
    │                                      │
    │  IKE_SA_INIT Request                 │
    │  - SAi1 (crypto proposals)           │
    │  - KEi (DH public value)             │
    │  - Ni (nonce)                        │
    │ ────────────────────────────────────►│
    │                                      │
    │  IKE_SA_INIT Response                │
    │  - SAr1 (selected crypto)            │
    │  - KEr (DH public value)             │
    │  - Nr (nonce)                        │
    │ ◄────────────────────────────────────│
    │                                      │
```

### Phase 2: IKE_AUTH with PPK

```
Initiator                              Responder
    │                                      │
    │  IKE_AUTH Request                    │
    │  - IDi (identity)                    │
    │  - AUTH (authentication)             │
    │  - SAi2 (child SA proposals)         │
    │  - TSi, TSr (traffic selectors)      │
    │  - N(PPK_IDENTITY) ◄─── QKD key ID   │
    │  - N(USE_PPK)                        │
    │ ────────────────────────────────────►│
    │                                      │
    │            ┌─────────────────────────┤
    │            │ Responder looks up      │
    │            │ QKD key by PPK_IDENTITY │
    │            │ via local KME           │
    │            └─────────────────────────┤
    │                                      │
    │  IKE_AUTH Response                   │
    │  - IDr (identity)                    │
    │  - AUTH (authentication)             │
    │  - SAr2 (selected child SA)          │
    │  - TSi, TSr (traffic selectors)      │
    │  - N(PPK_IDENTITY)                   │
    │ ◄────────────────────────────────────│
    │                                      │
```

### Key Derivation with PPK

Standard IKEv2 key derivation:
```
SKEYSEED = prf(Ni | Nr, g^ir)
```

With PPK, additional step:
```
SKEYSEED = prf(PPK, SKEYSEED_standard)
```

This mixes the QKD-derived key into all subsequent IKE and Child SA keys.

## 5. Notification Payloads

### PPK_IDENTITY (Notify Type 16435)

```
                     1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
| Next Payload  |C|  RESERVED   |         Payload Length        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  Protocol ID  |   SPI Size    |      Notify Message Type      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                                                               |
~                PPK_ID (QKD Key Identifier)                    ~
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### USE_PPK (Notify Type 16436)

Indicates willingness/requirement to use PPK.

### PPK_SUPPORTED (Notify Type 16437)

Sent in IKE_SA_INIT to indicate PPK capability.

## 6. Configuration Example (strongSwan)

```conf
# /etc/swanctl/swanctl.conf

connections {
    qkd-vpn {
        version = 2
        local_addrs = 10.1.1.1
        remote_addrs = 10.2.2.1

        local {
            auth = pubkey
            certs = site-a.crt
            id = site-a.example.com
        }

        remote {
            auth = pubkey
            id = site-b.example.com
        }

        children {
            secure-tunnel {
                local_ts = 192.168.1.0/24
                remote_ts = 192.168.2.0/24
                esp_proposals = aes256gcm16-prfsha384-ecp384
            }
        }

        # PPK configuration for QKD
        ppk_id = qkd-link-001
        ppk_required = yes
    }
}

secrets {
    ppk-qkd {
        id = qkd-link-001
        secret = <retrieved from KME>
    }
}
```

## 7. Dynamic PPK with QKD Key Manager

For dynamic key retrieval, implement a PPK plugin:

```c
// Conceptual strongSwan PPK plugin structure
typedef struct {
    ppk_provider_t public;
    kme_client_t *kme;
} qkd_ppk_provider_t;

METHOD(ppk_provider_t, get_ppk, bool,
    qkd_ppk_provider_t *this, identification_t *ppk_id,
    chunk_t *ppk, bool *required)
{
    char *key_id = ppk_id->get_encoding(ppk_id);

    // Retrieve key from QKD Key Management Entity
    kme_key_t *key = this->kme->get_key_by_id(this->kme, key_id);

    if (key == NULL) {
        return FALSE;
    }

    *ppk = chunk_clone(key->key_bytes);
    *required = TRUE;  // Fail if PPK unavailable

    // Mark key as used (one-time or limited-use)
    this->kme->mark_used(this->kme, key_id);

    return TRUE;
}
```

## 8. Rekey and Key Rotation

### IKE SA Rekey

```
- IKE SA has limited lifetime
- Rekey creates new SA with fresh keys
- QKD integration: fetch new PPK for each rekey
- Coordinate key ID in CREATE_CHILD_SA exchange
```

### Child SA Rekey

```
- More frequent than IKE SA rekey
- Can incorporate new PPK if supported
- Consider QKD key consumption rate
```

### Key Consumption Budget

| Traffic Profile | AES-256-GCM Keys/Hour | QKD Key Required |
|-----------------|----------------------|------------------|
| Light (rekey 1h) | 1 | 256 bits/hour |
| Medium (rekey 10min) | 6 | 1.5 Kbits/hour |
| Heavy (rekey 1min) | 60 | 15 Kbits/hour |

Ensure QKD key generation rate exceeds consumption.

## 9. Operational Considerations

### Failover Policy

```
When QKD key unavailable:
1. Buffer: Use cached keys if within validity window
2. Degrade: Fall back to classical IKEv2 (lose QKD benefit)
3. Fail-closed: Reject connection (security over availability)

Recommendation: Implement policy-based decision per connection criticality
```

### Monitoring

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| QKD key buffer level | < 10 keys | Warn |
| QKD key buffer level | < 3 keys | Critical |
| Key retrieval latency | > 100ms | Investigate |
| PPK mismatch errors | Any | Investigate sync |

## 10. Security Analysis

### What PPK + QKD Provides

- **Defense in depth**: Even if DH is broken, PPK protects
- **Quantum resistance**: QKD key not vulnerable to Shor's
- **Forward secrecy**: Maintained via ephemeral DH + key rotation

### What It Does Not Provide

- Protection against endpoint compromise
- Protection if QKD system itself is compromised
- Protection against classical channel MITM (still need authentication)

## References

- [RFC 8784 - IKEv2 PPK](https://www.rfc-editor.org/rfc/rfc8784.html)
- [IPsec + QKD Walkthrough (Rijsman)](https://www.brunorijsman.net/post/quantum-key-distribution-ipsec/)
- [strongSwan PPK Documentation](https://wiki.strongswan.org/projects/strongswan/wiki/PPK)
