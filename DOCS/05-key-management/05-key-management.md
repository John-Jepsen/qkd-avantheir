# Key Management for QKD-Derived Keys

## 1. Overview

QKD shifts the key problem from "agree by computation" to "deliver and track." A compatible key management model requires:

| Function | Description |
|----------|-------------|
| Buffering | Hold distilled secret bits from QKD engine |
| Key formatting | Carve buffers into keys of requested length (256-bit, 384-bit, etc.) |
| Key issuance | Serve keys to applications via authenticated interface |
| Key indexing | Attach identifiers and enforce one-time/limited-use rules |
| Key lifecycle | Expiration, erasure, audit, and replay prevention |

## 2. ETSI Key Delivery Architecture

### Core Components (ETSI GS QKD 014 Terminology)

```
┌─────────────────────────────────────────────────────────────────┐
│                         QKD Network                              │
│                                                                  │
│  ┌─────────────┐       Quantum       ┌─────────────┐            │
│  │  QKD Node   │      Channel        │  QKD Node   │            │
│  │   (Alice)   │◄────────────────────►│   (Bob)     │            │
│  └──────┬──────┘                     └──────┬──────┘            │
│         │                                   │                   │
│         │ Raw Key                           │ Raw Key           │
│         ▼                                   ▼                   │
│  ┌─────────────┐                     ┌─────────────┐            │
│  │    KME      │                     │    KME      │            │
│  │ (Key Mgmt   │                     │ (Key Mgmt   │            │
│  │  Entity)    │                     │  Entity)    │            │
│  └──────┬──────┘                     └──────┬──────┘            │
│         │                                   │                   │
└─────────┼───────────────────────────────────┼───────────────────┘
          │ ETSI REST API                     │ ETSI REST API
          ▼                                   ▼
   ┌─────────────┐                     ┌─────────────┐
   │    SAE      │                     │    SAE      │
   │ (Secure     │                     │ (Secure     │
   │  App        │◄───────────────────►│  App        │
   │  Entity)    │   Application       │  Entity)    │
   └─────────────┘   Protocol          └─────────────┘
```

### Terminology

| Term | Definition |
|------|------------|
| **KME** | Key Management Entity — holds key material from QKD link, serves to applications |
| **SAE** | Secure Application Entity — consumes keys for TLS/IPsec/applications |
| **Key ID** | Identifier for key block; enables coordination between peers |
| **Key size** | Requested key length in bits |

### Key ID Security Note

Key IDs do not reveal key bits, but remain metadata requiring integrity protection:
- Leak usage patterns
- Correlate sessions
- Enable traffic analysis

Always transmit key IDs over authenticated channels.

## 3. ETSI REST API (GS QKD 014)

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/keys/{slave_SAE_ID}/enc_keys` | GET | Get key(s) for encrypting to target SAE |
| `/api/v1/keys/{master_SAE_ID}/dec_keys` | POST | Get key(s) by ID for decrypting from source SAE |
| `/api/v1/keys/{slave_SAE_ID}/status` | GET | Get key availability status |

### Get Key Request

```http
GET /api/v1/keys/sae-bob-001/enc_keys?number=1&size=256 HTTP/1.1
Host: kme.site-a.internal
Authorization: Bearer <token>
Accept: application/json
```

### Get Key Response

```json
{
  "keys": [
    {
      "key_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "key": "base64-encoded-key-material"
    }
  ]
}
```

### Get Key by ID Request (Peer Side)

```http
POST /api/v1/keys/sae-alice-001/dec_keys HTTP/1.1
Host: kme.site-b.internal
Authorization: Bearer <token>
Content-Type: application/json
Accept: application/json

{
  "key_IDs": [
    {"key_ID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
  ]
}
```

### Status Response

```json
{
  "source_KME_ID": "kme-site-a-001",
  "target_KME_ID": "kme-site-b-001",
  "master_SAE_ID": "sae-alice-001",
  "slave_SAE_ID": "sae-bob-001",
  "key_size": 256,
  "stored_key_count": 1547,
  "max_key_count": 10000,
  "max_key_per_request": 128,
  "max_key_size": 4096,
  "min_key_size": 64,
  "max_SAE_ID_count": 0
}
```

## 4. Key Lifecycle Management

### State Machine

```
┌──────────────┐
│   CREATED    │  Key distilled from QKD, stored in KME buffer
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   INDEXED    │  Key assigned ID, available for issuance
└──────┬───────┘
       │ GET request from SAE
       ▼
┌──────────────┐
│   ISSUED     │  Key delivered to requesting SAE
└──────┬───────┘
       │ Matching GET/POST from peer SAE
       ▼
┌──────────────┐
│  CONFIRMED   │  Both SAEs have retrieved key
└──────┬───────┘
       │ TTL expiry or explicit revoke
       ▼
┌──────────────┐
│   EXPIRED    │  Key no longer valid for new uses
└──────┬───────┘
       │ Secure erasure
       ▼
┌──────────────┐
│   ERASED     │  Key material securely destroyed
└──────────────┘
```

### Lifecycle Policies

| Policy | Description | Typical Value |
|--------|-------------|---------------|
| Max age | Time from creation to forced expiry | 24 hours |
| Max uses | Number of times key can be retrieved | 1 (one-time) or N |
| Grace period | Time after expiry before erasure | 5 minutes |
| Audit retention | Duration to keep usage logs | 90 days |

## 5. Key Management Models

### Pairwise Link Key Store (Point-to-Point)

```
┌─────────────┐       QKD Link        ┌─────────────┐
│   Site A    │◄─────────────────────►│   Site B    │
│             │                       │             │
│  ┌───────┐  │                       │  ┌───────┐  │
│  │ KME A │  │                       │  │ KME B │  │
│  │       │  │                       │  │       │  │
│  │Buffer │  │                       │  │Buffer │  │
│  │[][][]…│  │                       │  │[][][]…│  │
│  └───────┘  │                       │  └───────┘  │
└─────────────┘                       └─────────────┘
```

**Use cases:**
- Two data centers on metro fiber
- Two VPN gateways with dedicated link
- High-security point-to-point communication

### Trusted-Node Networks (Multi-Hop)

```
┌───────┐      ┌───────┐      ┌───────┐      ┌───────┐
│ End A │◄────►│Trust 1│◄────►│Trust 2│◄────►│ End B │
└───────┘      └───────┘      └───────┘      └───────┘
    │              │              │              │
    │   QKD Link   │   QKD Link   │   QKD Link   │
    └──────────────┴──────────────┴──────────────┘
                        │
                        ▼
         Each hop runs QKD independently
         Intermediate nodes see secrets during relay
```

**Security model:**
- Security depends on physical security at each node
- Audit logging for all key operations
- NOT "zero knowledge" — nodes process secrets during relay
- This is the model used by China's 12,000+ km backbone (QuantumCTek infrastructure)

### Hybrid Classical-Quantum Model (RECOMMENDED)

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│   QKD Layer (where available)                                   │
│   ┌─────────┐             ┌─────────┐                           │
│   │ QKD A   │◄───────────►│ QKD B   │                           │
│   └────┬────┘             └────┬────┘                           │
│        │                       │                                │
├────────┼───────────────────────┼────────────────────────────────┤
│        │                       │                                │
│   Key Mixing Layer                                              │
│   ┌────▼────┐             ┌────▼────┐                           │
│   │ Hybrid  │             │ Hybrid  │                           │
│   │ KMS     │             │ KMS     │                           │
│   └────┬────┘             └────┬────┘                           │
│        │                       │                                │
├────────┼───────────────────────┼────────────────────────────────┤
│        │                       │                                │
│   Classical Layer (fallback)                                    │
│   ┌────▼────┐             ┌────▼────┐                           │
│   │ PQC KEM │◄───────────►│ PQC KEM │                           │
│   └─────────┘   Internet  └─────────┘                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key derivation with mixing:**
```
Final_Key = KDF(QKD_Key || PQC_Key || Classical_Key || Context)
```

**Benefits:**
- Defense in depth (security holds if any single component is compromised)
- Graceful degradation when QKD unavailable
- CNSA 2.0 compliance via PQC layer
- Information-theoretic guarantees via QKD layer

## 6. Vendor Key Management Platforms

| Vendor | Platform | Key Management Capabilities |
|--------|----------|----------------------------|
| **ID Quantique / IonQ** | Cerberis XG | ETSI 014 compliant KME, integrated key lifecycle |
| **Toshiba** | Multiplexed QKD System | KME integrated, supports 33.4 Tbps co-existence |
| **QuantumCTek** | QKD Infrastructure Suite | Full KMS for China's backbone, carrier-grade key relay |
| **QuintessenceLabs** | Trusted Security Foundation | Unified key management for QKD + classical keys |
| **LuxQuanta** | NOVA LQ | KME for CV-QKD, standard telecom component integration |
| **Q*Bird** | Falqon Series | MDI-QKD with multi-user key management |

## 7. KME Client Implementation

```python
"""
ETSI GS QKD 014 Compliant KME Client
"""

import requests
import base64
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urljoin

@dataclass
class QKDKey:
    key_id: str
    key_bytes: bytes

@dataclass
class KMEStatus:
    source_kme_id: str
    target_kme_id: str
    stored_key_count: int
    max_key_count: int
    key_size: int

class ETSIKMEClient:
    """
    Client for ETSI GS QKD 014 compliant Key Management Entity
    """

    def __init__(self,
                 kme_base_url: str,
                 sae_id: str,
                 auth_token: str,
                 verify_ssl: bool = True):
        self.base_url = kme_base_url.rstrip('/')
        self.sae_id = sae_id
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {auth_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.session.verify = verify_ssl

    def get_key(self,
                target_sae_id: str,
                key_size: int = 256,
                count: int = 1) -> List[QKDKey]:
        """
        Request new key(s) for communication with target SAE
        """
        url = urljoin(
            self.base_url,
            f'/api/v1/keys/{target_sae_id}/enc_keys'
        )

        params = {
            'number': count,
            'size': key_size
        }

        response = self.session.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        keys = []

        for key_data in data.get('keys', []):
            keys.append(QKDKey(
                key_id=key_data['key_ID'],
                key_bytes=base64.b64decode(key_data['key'])
            ))

        return keys

    def get_key_by_id(self,
                      source_sae_id: str,
                      key_ids: List[str]) -> List[QKDKey]:
        """
        Retrieve key(s) by ID (for receiving side)
        """
        url = urljoin(
            self.base_url,
            f'/api/v1/keys/{source_sae_id}/dec_keys'
        )

        payload = {
            'key_IDs': [{'key_ID': kid} for kid in key_ids]
        }

        response = self.session.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        keys = []

        for key_data in data.get('keys', []):
            keys.append(QKDKey(
                key_id=key_data['key_ID'],
                key_bytes=base64.b64decode(key_data['key'])
            ))

        return keys

    def get_status(self, target_sae_id: str) -> KMEStatus:
        """
        Get key availability status for target SAE
        """
        url = urljoin(
            self.base_url,
            f'/api/v1/keys/{target_sae_id}/status'
        )

        response = self.session.get(url)
        response.raise_for_status()

        data = response.json()

        return KMEStatus(
            source_kme_id=data.get('source_KME_ID', ''),
            target_kme_id=data.get('target_KME_ID', ''),
            stored_key_count=data.get('stored_key_count', 0),
            max_key_count=data.get('max_key_count', 0),
            key_size=data.get('key_size', 256)
        )

    def check_key_supply(self,
                         target_sae_id: str,
                         min_keys: int = 10) -> bool:
        """
        Check if sufficient keys are available
        """
        status = self.get_status(target_sae_id)
        return status.stored_key_count >= min_keys
```

## 8. Key Supply Monitoring

### Metrics to Track

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `qkd_key_buffer_count` | Keys in KME buffer | < 10% capacity |
| `qkd_key_generation_rate` | Keys/second from QKD | Below consumption |
| `qkd_key_consumption_rate` | Keys/second used by SAEs | Above generation |
| `qkd_key_expiry_rate` | Keys expiring unused | > 5% of generated |
| `qkd_link_qber` | Quantum bit error rate | > 5% |

### Capacity Planning

```
Required Key Buffer =
    (Peak Consumption Rate x Max Outage Duration) +
    (Normal Consumption Rate x Key Lifetime)

Example:
- Peak: 10 keys/second
- Max outage: 60 seconds
- Normal: 2 keys/second
- Lifetime: 300 seconds

Buffer = (10 x 60) + (2 x 300) = 600 + 600 = 1200 keys minimum
```

## 9. ETSI Standards Suite

| Standard | Title | Status |
|----------|-------|--------|
| GS QKD 004 | Application Interface | Published |
| GS QKD 008 | Quality of Service | Published |
| GS QKD 014 | REST Key Delivery API | Published (primary interface) |
| GS QKD 015 | Security Proofs | Published |
| GS QKD 016 | Security Evaluation Methodology | Published (adoption limited) |

## References

- [ETSI GS QKD 014 - REST Key Delivery API](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_QKD014v010101p.pdf)
- [ETSI GS QKD 004 - Application Interface](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/004/02.01.01_60/gs_QKD004v020101p.pdf)
- [ITU-T Y.3800 - QKD Networks Overview](https://www.itu.int/rec/T-REC-Y.3800)
- [ITU-T Y.3801 - Functional Requirements for QKDN](https://www.itu.int/rec/T-REC-Y.3801)
- [ETSI QKD ISG Standards Suite](https://www.etsi.org/technologies/quantum-key-distribution)
