# TLS 1.3 and mTLS Integration

## 1. Integration Architecture

QKD-TLS integration bridges two channels:

| Channel | Function |
|---------|----------|
| **Quantum channel** | Generates shared raw key material (sifting, error correction, privacy amplification) |
| **Classical channel + protocol stack** | Authentication, negotiation, key derivation, record protection |

### Integration Models

1. **Out-of-band provisioning into PSK hooks** - Protocol consumes keys as pre-shared secrets
2. **Out-of-band key replacement/augmentation** - Key update/rekey after initial handshake

## 2. TLS 1.3 PSK Integration Flow

```
┌──────────────┐                           ┌──────────────┐
│  QKD System  │                           │  QKD System  │
│   (Alice)    │     Quantum Channel       │    (Bob)     │
└──────┬───────┘                           └──────┬───────┘
       │                                          │
       ▼                                          ▼
┌──────────────┐                           ┌──────────────┐
│     KME      │                           │     KME      │
│ (Key Manager)│                           │ (Key Manager)│
└──────┬───────┘                           └──────┬───────┘
       │ {key_bytes, key_id}                      │
       ▼                                          ▼
┌──────────────┐                           ┌──────────────┐
│  QKD Adapter │                           │  QKD Adapter │
│              │                           │              │
└──────┬───────┘                           └──────┬───────┘
       │ psk_identity, psk_bytes                  │
       ▼                                          ▼
┌──────────────┐     TLS 1.3 Handshake    ┌──────────────┐
│  TLS Client  │ ◄──────────────────────► │  TLS Server  │
│              │   pre_shared_key ext     │              │
└──────────────┘                           └──────────────┘
```

### Typical Flow

1. Client and server obtain fresh shared secret from QKD key manager (out-of-band)
2. TLS client advertises PSK usage via TLS 1.3 PSK extensions (`pre_shared_key` and related fields)
3. Both sides map PSK identity to same QKD-provided key material through local adapter

**Important:** TLS 1.3 PSK requires explicit signaling using existing extensions. No new protocol messages needed, but ClientHello does signal PSK usage.

## 3. TLS 1.3 Security Modes

### PSK-only Mode

```
Session secrets derive solely from PSK

Pros:
- Simpler key schedule
- No (EC)DHE computation

Cons:
- NO forward secrecy
- Compromised PSK compromises all sessions using it
- Requires strict key rotation

Recommendation: Use only when QKD key rotation is frequent and reliable
```

### PSK + (EC)DHE Mode (RECOMMENDED)

```
TLS mixes PSK into handshake AND runs ephemeral key agreement

Pros:
- Maintains forward secrecy
- QKD entropy augments classical security
- Defense in depth

Cons:
- Additional (EC)DHE computation
- More complex

Recommendation: Default choice for QKD-TLS integration
```

## 4. mTLS Considerations

mTLS adds certificate-based mutual authentication but **does not change the key schedule**.

| Feature | Impact on QKD Integration |
|---------|--------------------------|
| Client certificate | Provides identity assurance (orthogonal to key material) |
| Server certificate | Same as standard TLS |
| Key establishment | Still choose PSK-only or PSK+(EC)DHE |

## 5. QKD Adapter Implementation Pattern

```python
# Conceptual QKD-TLS adapter interface
class QKDAdapter:
    def __init__(self, kme_endpoint: str, credentials: AuthCredentials):
        self.kme = KMEClient(kme_endpoint, credentials)

    def get_psk_for_peer(self, peer_id: str) -> PSKMaterial:
        """
        Pull key material from QKD system
        Returns: {psk_identity, psk_bytes, metadata}
        """
        key_block = self.kme.get_key(
            peer_sae_id=peer_id,
            key_size=256  # bits
        )
        return PSKMaterial(
            psk_identity=key_block.key_id,
            psk_bytes=key_block.key_bytes,
            metadata={
                'expiry': key_block.expiry,
                'key_index': key_block.index
            }
        )

    def coordinate_identity(self, identity: bytes) -> bool:
        """
        Ensure peer can retrieve matching key by identity
        """
        # Identity coordination happens via authenticated channel
        pass

    def rotate_key(self, current_identity: bytes) -> PSKMaterial:
        """
        Rotation policy enforcement
        """
        pass
```

## 6. Implementation Checklist

### TLS Stack Configuration

- [ ] Enable PSK cipher suites in TLS 1.3
- [ ] Configure PSK identity callback to use QKD adapter
- [ ] Set PSK key exchange mode (psk_dhe_ke recommended)
- [ ] Configure session ticket handling for QKD key epochs

### QKD Adapter Requirements

- [ ] ETSI GS QKD 014 compliant KME client
- [ ] Secure credential storage for KME authentication
- [ ] Key caching with expiry enforcement
- [ ] Identity-to-key mapping table
- [ ] Rotation policy engine
- [ ] Audit logging for key usage

### Operational Requirements

- [ ] Key supply monitoring (alert if generation < consumption)
- [ ] Fallback policy (classical or PQC when QKD unavailable)
- [ ] Identity lifetime management
- [ ] Connection churn alignment with key rotation

## 7. Example: OpenSSL + QKD Integration

Reference implementation: [brunorijsman/openssl-qkd](https://github.com/brunorijsman/openssl-qkd)

Key modifications:
1. Custom PSK callback that queries KME
2. Identity encoding for ETSI key IDs
3. Key lifecycle tracking

## References

- [RFC 8446 - TLS 1.3](https://www.rfc-editor.org/rfc/rfc8446.html)
- [ITU-T Draft Y.QKD-TLS](https://www.itu.int/en/ITU-T/studygroups/2022-2024/13/Documents/QKD-TLS.pdf)
- [Prévost et al. (2025) - ETSI-compliant QKD-TLS](https://arxiv.org/abs/2501.01234)
- [OpenSSL + QKD Reference](https://github.com/brunorijsman/openssl-qkd)
