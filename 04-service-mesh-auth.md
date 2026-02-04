# Service-to-Service Authentication and Service Mesh Integration

## 1. Overview

For microservices and internal service meshes, QKD-derived keys fit symmetric authentication patterns with short-interval rekeying. This document covers integration patterns for service-to-service security using QKD key material.

## 2. Use Cases

| Pattern | Description | QKD Key Usage |
|---------|-------------|---------------|
| Session keys | QKD-derived PSKs for session setup and record protection | Per-session or per-epoch |
| Authentication secrets | Symmetric authenticators for message-level MAC | Per-message or per-window |
| Token wrapping | Encrypt/MAC service tokens | Per-token-generation |
| mTLS enhancement | Augment certificate-based auth with symmetric proof | Per-connection |

## 3. Architecture Patterns

### Pattern A: QKD-Enhanced Service Mesh

```
┌─────────────────────────────────────────────────────────────────┐
│                        Service Mesh                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Service A  │    │  Service B  │    │  Service C  │         │
│  │  ┌───────┐  │    │  ┌───────┐  │    │  ┌───────┐  │         │
│  │  │ Proxy │  │◄──►│  │ Proxy │  │◄──►│  │ Proxy │  │         │
│  │  └───┬───┘  │    │  └───┬───┘  │    │  └───┬───┘  │         │
│  └──────┼──────┘    └──────┼──────┘    └──────┼──────┘         │
│         │                  │                  │                 │
│         └──────────────────┼──────────────────┘                 │
│                            │                                    │
│                    ┌───────▼───────┐                           │
│                    │   QKD Key     │                           │
│                    │   Service     │                           │
│                    └───────┬───────┘                           │
└────────────────────────────┼────────────────────────────────────┘
                             │
                     ┌───────▼───────┐
                     │     KME       │
                     │  (per-site)   │
                     └───────────────┘
```

### Pattern B: Direct Service-to-Service QKD

```
┌─────────────────┐         QKD Link          ┌─────────────────┐
│   Service A     │ ◄───────────────────────► │   Service B     │
│   (Site 1)      │                           │   (Site 2)      │
│                 │                           │                 │
│  ┌───────────┐  │                           │  ┌───────────┐  │
│  │ Local KME │  │                           │  │ Local KME │  │
│  └───────────┘  │                           │  └───────────┘  │
└─────────────────┘                           └─────────────────┘
```

## 4. Key Distribution Models

### Pairwise Service Keys

```
                    ┌───────────────┐
                    │   QKD Key     │
                    │   Service     │
                    └───────┬───────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
     ┌──────────┐    ┌──────────┐    ┌──────────┐
     │ Service  │    │ Service  │    │ Service  │
     │    A     │    │    B     │    │    C     │
     └──────────┘    └──────────┘    └──────────┘

Key Matrix:
  A↔B: key_ab_001
  A↔C: key_ac_001
  B↔C: key_bc_001
```

### Group Service Keys (Shared Epoch Key)

```
All services in trust group share epoch key:

Epoch 1: key_group_e001
Epoch 2: key_group_e002
...

Pros: Simpler key distribution
Cons: Compromise affects all group services
```

## 5. Operational Constraints

### Identity-to-Key Mapping

Services need stable, verifiable identities mapped to keys:

```yaml
# Key mapping configuration
service_keys:
  - service_id: "payment-service.prod.cluster-1"
    peer_id: "order-service.prod.cluster-1"
    key_source: "kme://site-a.internal/link-001"
    rotation_interval: 300  # seconds

  - service_id: "payment-service.prod.cluster-1"
    peer_id: "inventory-service.prod.cluster-1"
    key_source: "kme://site-a.internal/link-001"
    rotation_interval: 300
```

### Key Rotation Alignment

| Factor | Consideration |
|--------|---------------|
| QKD key supply | Rotation interval × active connections ≤ key generation rate |
| Connection churn | New connections consume keys; plan for peak |
| Epoch synchronization | All peers must rotate together |
| Grace period | Support old + new key during transition |

### Rotation State Machine

```
┌─────────────┐
│   ACTIVE    │ Current key in use
└──────┬──────┘
       │ rotation_time - grace_period
       ▼
┌─────────────┐
│  PENDING    │ New key fetched, not yet active
└──────┬──────┘
       │ rotation_time
       ▼
┌─────────────┐
│ TRANSITION  │ Accept both old and new key
└──────┬──────┘
       │ rotation_time + grace_period
       ▼
┌─────────────┐
│   RETIRED   │ Old key no longer accepted
└─────────────┘
```

## 6. Implementation: Service Key Agent

```python
"""
QKD Service Key Agent
Manages QKD-derived keys for service-to-service authentication
"""

import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class KeyState(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    TRANSITION = "transition"
    RETIRED = "retired"

@dataclass
class ServiceKey:
    key_id: str
    key_bytes: bytes
    state: KeyState
    epoch: int
    created_at: float
    expires_at: float
    peer_service_id: str

class QKDServiceKeyAgent:
    def __init__(self,
                 service_id: str,
                 kme_client: 'KMEClient',
                 rotation_interval: int = 300,
                 grace_period: int = 30):
        self.service_id = service_id
        self.kme = kme_client
        self.rotation_interval = rotation_interval
        self.grace_period = grace_period

        self._keys: Dict[str, Dict[int, ServiceKey]] = {}
        self._lock = threading.RLock()
        self._rotation_thread = None

    def get_key_for_peer(self, peer_id: str) -> Optional[ServiceKey]:
        """Get current active key for authenticating with peer"""
        with self._lock:
            peer_keys = self._keys.get(peer_id, {})
            # Return key in ACTIVE or TRANSITION state
            for epoch in sorted(peer_keys.keys(), reverse=True):
                key = peer_keys[epoch]
                if key.state in (KeyState.ACTIVE, KeyState.TRANSITION):
                    return key
        return None

    def validate_key(self, peer_id: str, key_id: str) -> Optional[ServiceKey]:
        """Validate incoming key_id from peer"""
        with self._lock:
            peer_keys = self._keys.get(peer_id, {})
            for key in peer_keys.values():
                if key.key_id == key_id:
                    if key.state in (KeyState.ACTIVE, KeyState.TRANSITION):
                        return key
        return None

    def register_peer(self, peer_id: str):
        """Initialize key management for a peer service"""
        with self._lock:
            if peer_id not in self._keys:
                self._keys[peer_id] = {}
                self._fetch_initial_key(peer_id)

    def _fetch_initial_key(self, peer_id: str):
        """Fetch first key for peer from KME"""
        key_block = self.kme.get_key(
            source_sae_id=self.service_id,
            target_sae_id=peer_id,
            key_size=256
        )

        now = time.time()
        key = ServiceKey(
            key_id=key_block.key_id,
            key_bytes=key_block.key_bytes,
            state=KeyState.ACTIVE,
            epoch=1,
            created_at=now,
            expires_at=now + self.rotation_interval + self.grace_period,
            peer_service_id=peer_id
        )

        self._keys[peer_id][1] = key

    def _rotation_cycle(self):
        """Background rotation for all peer keys"""
        while True:
            time.sleep(self.rotation_interval - self.grace_period)
            self._rotate_all_keys()

    def _rotate_all_keys(self):
        """Rotate keys for all peers"""
        with self._lock:
            for peer_id in self._keys:
                self._rotate_peer_key(peer_id)

    def _rotate_peer_key(self, peer_id: str):
        """Rotate key for specific peer"""
        peer_keys = self._keys[peer_id]
        current_epoch = max(peer_keys.keys())
        current_key = peer_keys[current_epoch]

        # Fetch new key
        key_block = self.kme.get_key(
            source_sae_id=self.service_id,
            target_sae_id=peer_id,
            key_size=256
        )

        now = time.time()
        new_epoch = current_epoch + 1

        # Create new key in PENDING
        new_key = ServiceKey(
            key_id=key_block.key_id,
            key_bytes=key_block.key_bytes,
            state=KeyState.PENDING,
            epoch=new_epoch,
            created_at=now,
            expires_at=now + self.rotation_interval + self.grace_period,
            peer_service_id=peer_id
        )
        peer_keys[new_epoch] = new_key

        # Schedule state transitions
        threading.Timer(
            self.grace_period,
            self._transition_key,
            args=[peer_id, current_epoch, new_epoch]
        ).start()

    def _transition_key(self, peer_id: str, old_epoch: int, new_epoch: int):
        """Transition from old to new key"""
        with self._lock:
            peer_keys = self._keys[peer_id]

            # Old key enters TRANSITION (still accepted)
            if old_epoch in peer_keys:
                peer_keys[old_epoch].state = KeyState.TRANSITION

            # New key becomes ACTIVE
            if new_epoch in peer_keys:
                peer_keys[new_epoch].state = KeyState.ACTIVE

            # Schedule retirement of old key
            threading.Timer(
                self.grace_period,
                self._retire_key,
                args=[peer_id, old_epoch]
            ).start()

    def _retire_key(self, peer_id: str, epoch: int):
        """Retire and securely erase old key"""
        with self._lock:
            peer_keys = self._keys.get(peer_id, {})
            if epoch in peer_keys:
                key = peer_keys[epoch]
                # Secure erasure
                key.key_bytes = b'\x00' * len(key.key_bytes)
                key.state = KeyState.RETIRED
                del peer_keys[epoch]
```

## 7. Message-Level Authentication

### HMAC-Based Authentication

```python
import hmac
import hashlib
import struct
import time

def create_authenticated_message(
    payload: bytes,
    service_key: ServiceKey,
    sender_id: str
) -> bytes:
    """
    Create authenticated message with QKD-derived key

    Format:
    [version:1][key_id_len:1][key_id:var][timestamp:8][payload_len:4][payload:var][mac:32]
    """
    timestamp = struct.pack('>Q', int(time.time()))
    key_id_bytes = service_key.key_id.encode('utf-8')
    payload_len = struct.pack('>I', len(payload))

    # Construct message without MAC
    msg = (
        b'\x01' +  # version
        struct.pack('B', len(key_id_bytes)) +
        key_id_bytes +
        timestamp +
        payload_len +
        payload
    )

    # Compute HMAC-SHA256
    mac = hmac.new(
        service_key.key_bytes,
        msg,
        hashlib.sha256
    ).digest()

    return msg + mac

def verify_authenticated_message(
    message: bytes,
    key_agent: QKDServiceKeyAgent,
    sender_id: str,
    max_age_seconds: int = 60
) -> Optional[bytes]:
    """
    Verify and extract payload from authenticated message
    Returns payload if valid, None if invalid
    """
    if len(message) < 46:  # Minimum valid message size
        return None

    # Parse header
    version = message[0]
    if version != 1:
        return None

    key_id_len = message[1]
    key_id = message[2:2+key_id_len].decode('utf-8')

    offset = 2 + key_id_len
    timestamp = struct.unpack('>Q', message[offset:offset+8])[0]
    offset += 8

    payload_len = struct.unpack('>I', message[offset:offset+4])[0]
    offset += 4

    payload = message[offset:offset+payload_len]
    offset += payload_len

    received_mac = message[offset:offset+32]

    # Validate timestamp
    now = int(time.time())
    if abs(now - timestamp) > max_age_seconds:
        return None  # Replay or stale

    # Look up key
    key = key_agent.validate_key(sender_id, key_id)
    if key is None:
        return None

    # Verify MAC
    expected_mac = hmac.new(
        key.key_bytes,
        message[:offset],
        hashlib.sha256
    ).digest()

    if not hmac.compare_digest(received_mac, expected_mac):
        return None

    return payload
```

## 8. Integration with Service Mesh Proxies

### Envoy Proxy Integration Concept

```yaml
# Envoy filter for QKD authentication
http_filters:
- name: envoy.filters.http.qkd_auth
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.qkd_auth.v3.QKDAuth
    kme_cluster: qkd_key_service
    service_id: "my-service.prod"
    key_header: "X-QKD-Key-ID"
    mac_header: "X-QKD-MAC"
    rotation_interval: 300s

clusters:
- name: qkd_key_service
  type: STRICT_DNS
  lb_policy: ROUND_ROBIN
  load_assignment:
    cluster_name: qkd_key_service
    endpoints:
    - lb_endpoints:
      - endpoint:
          address:
            socket_address:
              address: kme.internal
              port_value: 8443
```

## 9. Monitoring and Observability

| Metric | Type | Description |
|--------|------|-------------|
| `qkd_service_key_rotations_total` | Counter | Total key rotations per peer |
| `qkd_service_key_age_seconds` | Gauge | Age of current active key |
| `qkd_service_auth_success_total` | Counter | Successful authentications |
| `qkd_service_auth_failure_total` | Counter | Failed authentications by reason |
| `qkd_service_key_buffer_count` | Gauge | Keys available in buffer |

## References

- [ETSI GS QKD 014 - Key Delivery API](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/014/01.01.01_60/gs_QKD014v010101p.pdf)
- [ETSI GS QKD 004 - Application Interface](https://www.etsi.org/deliver/etsi_gs/QKD/001_099/004/02.01.01_60/gs_QKD004v020101p.pdf)
