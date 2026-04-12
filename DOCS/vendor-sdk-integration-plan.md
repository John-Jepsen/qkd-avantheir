# Vendor SDK/API Integration Plan

Plan for integrating each vendor SDK/API option into the existing QKD implementation stack.

---

## Existing Architecture Overview

The existing implementation has a layered architecture with well-defined integration points:

1. **Quantum Channel Layer** -- `bb84_simulator.py` provides `QiskitQuantumChannel` and `ClassicalQuantumChannel`, both conforming to the same `transmit()` interface.
2. **Protocol Layer** -- `BB84Protocol` selects a channel backend by name (`"qiskit"` or `"classical"`) and runs the full BB84 pipeline (sifting, QBER, error correction, privacy amplification).
3. **Key Management Layer** -- `kme_server.py` (`KeyPool`) and `kme_dual.py` (`DualKeyPool`) wrap `BB84Protocol` behind ETSI GS QKD 014 REST endpoints.
4. **Application Layer** -- `tls_psk_demo.py` and `ikev2_ppk_config.md` consume keys from the KME via its REST API.
5. **ML/Analytics Layer** -- `api.py` orchestrates the full pipeline with ML models.
6. **Hybrid Crypto Layer** -- `hybrid_kdf.py` combines QKD keys with ML-KEM via HKDF.

Vendors plug in at **two distinct levels**:

- **Simulation-level** (IBM Qiskit): replaces the quantum channel/protocol simulation
- **KME-level** (all hardware vendors): replaces the key pool's `_generate()` method with a call to a vendor KME's ETSI 014 REST API, turning our KME into a proxy/adapter

---

## Plan 1: IBM Qiskit -- Enhanced Quantum Simulation

**What it is:** Qiskit is already the primary simulation backend. This plan extends the Qiskit integration with IBM Quantum hardware access, advanced noise models, and Qiskit-native error correction.

### What to Build

New file: `implementation/qiskit_advanced.py`

| Class | Purpose |
|-------|---------|
| `IBMQuantumChannel` | Third channel class that connects to a real IBM Quantum backend via `qiskit-ibm-runtime`, executing BB84 circuits on actual quantum hardware (e.g., `ibm_sherbrooke`, `ibm_brisbane`) |
| `RealisticNoiseChannel` | Enhanced `QiskitQuantumChannel` that loads device-specific noise models from `FakeBackendV2` classes (real T1/T2 decoherence, readout errors, crosstalk) instead of the current single depolarizing error |
| `QiskitCascadeCorrector` | Multi-pass Cascade error correction replacing the simplified single-pass binary reconciliation |

### Integration Point

Register `"ibm_hardware"` and `"realistic_noise"` as new backends in `BB84Protocol.__init__()` at `bb84_simulator.py:281-289`. The existing dispatch is a simple `if/elif/else` on `backend`:

```python
# Current code at bb84_simulator.py:281-289
if backend == "qiskit":
    self.channel = QiskitQuantumChannel(...)
elif backend == "classical":
    self.channel = ClassicalQuantumChannel(...)
```

All channel classes share the same `transmit(alice_bits, alice_bases) -> (bob_bits, bob_bases)` interface. The `api.py` `AnalyzeRequest` model already accepts a `backend` string field, so the new backends are immediately accessible through the REST API.

### Dependencies

- `qiskit-ibm-runtime>=0.34` (add to `requirements.txt`)
- IBM Quantum API token (stored in environment variable `IBM_QUANTUM_TOKEN` or `~/.qiskit/qiskit-ibm.json`)
- Free IBM Quantum account sufficient for testing; premium plan for real hardware access

### Implementation Steps

1. Create `implementation/qiskit_advanced.py` with `IBMQuantumChannel` wrapping `qiskit_ibm_runtime.SamplerV2` to submit circuits to a real backend. The `transmit()` method builds the same circuit structure as `QiskitQuantumChannel._run_circuit()` but submits via `QiskitRuntimeService.backend()`.
2. Create `RealisticNoiseChannel` that instantiates `AerSimulator.from_backend(FakeSherbrooke())` to get hardware-calibrated noise instead of the synthetic depolarizing model.
3. Modify `bb84_simulator.py` lines 281-289 to add two new backend choices (`"ibm_hardware"` and `"realistic_noise"`), importing from `qiskit_advanced.py`.
4. Add `IBM_QUANTUM_TOKEN` to `.gitignore` and document the environment variable in `README.md`.
5. Write tests in `tests/test_qiskit_advanced.py` using `RealisticNoiseChannel` (no API token needed) and mocking the runtime service for `IBMQuantumChannel`.
6. Update `requirements.txt` to add `qiskit-ibm-runtime>=0.34`.

### Deliverable

Running `BB84Protocol(backend="realistic_noise").run(n_bits=4096)` uses hardware-calibrated noise. Running `BB84Protocol(backend="ibm_hardware").run(n_bits=512)` executes on a real IBM quantum processor. Both produce `BB84Result` objects identical in shape to the current output.

---

## Plan 2: QuintessenceLabs TSF (Trusted Security Foundation)

**What it is:** QuintessenceLabs TSF is a unified key management platform that manages keys from both QKD (qOptica) and QRNG (qStream) sources. TSF exposes a REST/KMIP API for key lifecycle management.

### What to Build

New file: `implementation/vendor_quintessence.py`

| Class | Purpose |
|-------|---------|
| `TSFKeySource` | Replaces the BB84 simulator as the key source inside `KeyPool`. Calls the TSF REST API to request keys; TSF manages qOptica and qStream internally |
| `TSFConfig` | Dataclass holding TSF connection parameters (base URL, client certificate paths, API key, key policy name) |
| `TSFHealthChecker` | Monitoring class that polls TSF's health/status endpoint and reports QRNG entropy levels, QKD link status, and key pool depth |

New file: `implementation/vendor_quintessence_config.md`

- TSF appliance provisioning steps
- Client certificate generation for mutual TLS
- Key policy configuration (key size, rotation interval, QKD vs QRNG source)

### Integration Point

`KeyPool._generate()` in `kme_server.py:89-109`. Create a `TSFBackedKeyPool` subclass that delegates to `TSFKeySource.fetch_key()` instead of `BB84Protocol().run()`. The ETSI 014 REST API surface of `kme_server.py` stays unchanged -- all downstream consumers (`tls_psk_demo.py`, `ikev2_ppk_config.md`) work without modification.

### Dependencies

- QuintessenceLabs TSF appliance (physical or VM) with network access
- Client TLS certificate issued by the TSF CA
- TSF API documentation (under NDA; general KMIP compatibility documented publicly)
- `requests` (already in requirements.txt) for REST calls
- `pykmip>=0.12` for KMIP-based integration (optional, alternative to REST)

### Implementation Steps

1. Create `implementation/vendor_quintessence.py` with `TSFConfig` dataclass, `TSFKeySource` class with methods `fetch_key(size_bits) -> StoredKey` and `check_health() -> dict`.
2. `TSFKeySource.fetch_key()` calls `POST {tsf_base_url}/api/v1/keys/generate` with mutual TLS using the configured client certificate. Response includes key bytes and a TSF-internal key ID.
3. Create `TSFBackedKeyPool(KeyPool)` subclass that overrides `_generate()` to call `TSFKeySource.fetch_key()` instead of running BB84.
4. Add a `--key-source` CLI flag to `kme_server.py` (`"simulator"` default, `"tsf"` for QuintessenceLabs) that selects which pool implementation to instantiate.
5. Create `implementation/vendor_quintessence_config.md` with provisioning instructions.
6. Write tests in `tests/test_vendor_quintessence.py` that mock the TSF API responses and verify the full `KeyPool` -> `enc_keys` -> `dec_keys` flow with vendor-sourced keys.
7. Add `pykmip>=0.12` to `requirements.txt` as an optional dependency.

### Deliverable

Running `python kme_server.py --key-source tsf` starts the KME with keys sourced from a TSF appliance. The ETSI 014 API is identical; `tls_psk_demo.py` and all downstream consumers work unchanged. When no TSF appliance is available, tests pass using mocked HTTP responses.

---

## Plan 3: ID Quantique Cerberis XG -- ETSI 014 REST API

**What it is:** The Cerberis XG is IDQ's production QKD platform that includes an integrated KME exposing the ETSI GS QKD 014 REST API. This is the most direct integration because the Cerberis KME speaks the same API our `kme_server.py` implements.

### What to Build

New file: `implementation/vendor_idq.py`

| Class | Purpose |
|-------|---------|
| `CerberisKMEClient` | Reusable ETSI 014 client generalized from the helper functions in `tls_psk_demo.py:47-73`, with mTLS support, retry logic, and health checking |
| `CerberisProxyPool` | `KeyPool` replacement that forwards ETSI 014 requests to the Cerberis hardware KME. Our `kme_server.py` becomes a proxy that adds ML anomaly detection |
| `IDQHealthMonitor` | Monitors the Cerberis status endpoint for QBER, key rate, and link alarms. Feeds data into `MetricsCollector` |

New file: `implementation/kme_proxy.py`

- Standalone Flask app that proxies ETSI 014 requests to a real hardware KME, adding the ML anomaly detection and metrics layers from `api.py`

### Integration Point

`CerberisKMEClient` is a cleaned-up, configurable version of the two helper functions already in `tls_psk_demo.py` (lines 47-73). `CerberisProxyPool` replaces `KeyPool` in `kme_server.py`. The ML pipeline in `api.py` wraps the proxy, so every key served also gets anomaly-scored by `KMEAnomalyDetector`.

### Dependencies

- ID Quantique Cerberis XG appliance with network-accessible KME endpoint
- mTLS client certificate from IDQ provisioning
- Cerberis management console access for initial SAE registration
- `requests` (already present) and `urllib3` for TLS configuration

### Implementation Steps

1. Create `implementation/vendor_idq.py` with `CerberisConfig` (base_url, client_cert, client_key, ca_cert, sae_id), `CerberisKMEClient` with methods `get_status()`, `get_enc_keys(n, size)`, `get_dec_keys(key_ids)`.
2. Implement `CerberisProxyPool` wrapping `CerberisKMEClient` with the same interface as `KeyPool`.
3. Create `implementation/kme_proxy.py` as a standalone Flask app combining proxy behavior with the ML analytics pipeline.
4. Add an `--upstream-kme` CLI flag to `kme_server.py` that switches from local generation to proxying.
5. Write `tests/test_vendor_idq.py` with mocked Cerberis responses using the same ETSI 014 contract.
6. Create `implementation/vendor_idq_config.md` documenting Cerberis provisioning, SAE registration, and certificate setup.

### Deliverable

Running `python kme_server.py --upstream-kme https://cerberis.local:8443 --client-cert cert.pem` proxies all ETSI 014 requests to real Cerberis XG hardware. `tls_psk_demo.py` and `ikev2_ppk_config.md` work without any changes. The ML anomaly detector scores every key request passing through the proxy.

---

## Plan 4: Toshiba ETSI GS QKD 014 KME API

**What it is:** Toshiba's QKD Key Manager exposes the same ETSI GS QKD 014 REST API. Since IDQ Cerberis (Plan 3) and Toshiba both speak ETSI 014, the integration shares the same proxy architecture. The differentiation is in Toshiba-specific extensions (high key rates, DWDM status, multiplexing metadata).

### What to Build

New file: `implementation/vendor_toshiba.py`

| Class | Purpose |
|-------|---------|
| `ToshibaKMEClient` | Extends `CerberisKMEClient` (from Plan 3) with Toshiba-specific status extensions (`key_generation_rate_mbps`, `dwdm_channel`, `classical_traffic_gbps`) |
| `ToshibaHighRatePool` | Pool optimized for Toshiba's high key rates (63+ Mbps). Bulk pre-fetches in configurable batch sizes with async background refill |
| `ToshibaDWDMMonitor` | Reads DWDM co-existence metrics and feeds QBER time series into `NoisePredictor` from `ml_noise_predictor.py` for adaptive parameter tuning |

### Integration Point

- Shares the base `CerberisKMEClient` from Plan 3 (both are ETSI 014 clients). If Plan 3 is implemented first, Plan 4 inherits from it.
- `ToshibaHighRatePool` plugs into `kme_server.py` the same way `CerberisProxyPool` does.
- `ToshibaDWDMMonitor` connects to `NoisePredictor.fit()` by feeding real QBER time series from the Toshiba KME's status endpoint, replacing synthetic training data.

### Dependencies

- Toshiba QKD Key Manager appliance with ETSI 014 API access
- mTLS certificates from Toshiba provisioning
- Toshiba QKD API documentation (extended status fields)
- `requests` (already present)

### Implementation Steps

1. Create `implementation/vendor_toshiba.py` with `ToshibaConfig`, `ToshibaKMEClient`, `ToshibaHighRatePool`, `ToshibaDWDMMonitor`.
2. `ToshibaKMEClient` either extends `CerberisKMEClient` (if Plan 3 exists) or implements the ETSI 014 client independently. The critical difference: Toshiba's status endpoint returns additional extension fields.
3. `ToshibaHighRatePool` implements batch pre-fetching: calls `enc_keys` with `number=20` (max per request) in a background thread whenever the local cache drops below `POOL_REFILL_TRIGGER`. This mirrors the existing `_maybe_refill()` pattern in `kme_server.py:117-119`.
4. `ToshibaDWDMMonitor` polls the status endpoint every 30 seconds, extracts QBER, and appends to a time series. Expose a method `get_noise_series()` returning a numpy array compatible with `NoisePredictor.fit()`.
5. Write `tests/test_vendor_toshiba.py` mocking the Toshiba API and verifying bulk fetch, DWDM monitoring, and ETSI 014 compatibility.
6. Create `implementation/vendor_toshiba_config.md` documenting Toshiba KME setup and DWDM integration.

### Deliverable

Running `python kme_server.py --upstream-kme https://toshiba-kme.local:8443 --vendor toshiba` enables high-rate bulk fetching and DWDM monitoring. The `/forecast` endpoint returns predictions based on real Toshiba QBER telemetry. All downstream consumers are unchanged.

---

## Plan 5: QuantumCTek QKD NMS -- Network Management Platform

**What it is:** QuantumCTek's NMS manages large-scale QKD networks (12,000+ km, 145 nodes in the Chinese national network). It provides proprietary management APIs alongside partial ETSI compliance, with emphasis on trusted-node relay orchestration.

### What to Build

New file: `implementation/vendor_quantumctek.py`

| Class | Purpose |
|-------|---------|
| `QCTekNMSClient` | Client for the proprietary NMS REST API: node management, relay path selection, key relay orchestration |
| `QCTekETSI014Adapter` | Normalizes proprietary response format to ETSI 014 JSON schema (`"keyId"` -> `"key_ID"`, `"keyValue"` -> `"key"`, etc.) |
| `QCTekRelayOrchestrator` | Replaces BB84 simulation in `relay_network.py` with real NMS link keys and relay paths |
| `QCTekNetworkTopologySync` | Polls NMS topology, builds/refreshes a live `QKDRelayNetwork` graph when links go up/down |

### Integration Point

`relay_network.py` is the primary integration point. The existing `QKDRelayNetwork.connect()` at line 107 runs BB84 to generate link keys. `QCTekRelayOrchestrator` replaces this with keys fetched from the NMS for each physical link. `QCTekNetworkTopologySync` calls `add_node()` and `connect()` based on the NMS's reported topology.

For point-to-point key delivery, `QCTekETSI014Adapter` plugs into the same `KeyPool._generate()` injection point as Plans 2-4.

### Dependencies

- QuantumCTek NMS appliance or API access (primarily available in China)
- NMS API documentation (proprietary; available under vendor agreement)
- Network access to the NMS management plane
- `requests` (already present)
- Potentially `zeep` or `suds` if SOAP endpoints are used

### Implementation Steps

1. Create `implementation/vendor_quantumctek.py` with `QCTekConfig` (nms_url, api_key, network_id), `QCTekNMSClient`, `QCTekETSI014Adapter`, `QCTekRelayOrchestrator`, `QCTekNetworkTopologySync`.
2. `QCTekNMSClient` implements: `get_nodes()`, `get_links()`, `get_link_key(node_a, node_b)`, `get_relay_path(source, dest)`, `get_key(sae_id, count, size)`.
3. `QCTekETSI014Adapter` maps proprietary response fields to ETSI 014 JSON:
   - `"keyId"` -> `"key_ID"`, `"keyValue"` -> `"key"` (base64), `"keyLength"` -> `"key_size"`
   - `"nodeStatus"` -> mapped to `"stored_key_count"` etc. in the status response
4. `QCTekRelayOrchestrator` wraps `QKDRelayNetwork`:
   - `build_from_nms()` calls `get_nodes()` and `get_links()`, then `add_node()`/`connect()` for each
   - Override `connect()` behavior: instead of running BB84, call `get_link_key()` from the NMS
   - `relay_key()` delegates path finding to the NMS or uses the existing BFS in `relay_network.py`
5. `QCTekNetworkTopologySync` with a polling loop (configurable interval) that refreshes the `QKDRelayNetwork` graph when links go up/down.
6. Write `tests/test_vendor_quantumctek.py` with comprehensive NMS API mocks.
7. Create `implementation/vendor_quantumctek_config.md` documenting NMS integration and relay path policies.

### Deliverable

Running `python relay_network.py --nms https://qctek-nms.local:9443 --network-id cn-metro-01` builds a live relay network from the QuantumCTek NMS topology. `relay_key("Beijing", "Shanghai")` routes through NMS-reported trusted nodes with real QKD link keys. For point-to-point: `python kme_server.py --upstream-kme https://qctek-nms.local:9443/etsi --vendor quantumctek`.

---

## Cross-Cutting: Shared KeySource Abstraction

Plans 2-5 all replace the key source inside `KeyPool._generate()`. A shared abstraction keeps this clean:

```python
# implementation/key_source.py
class KeySource(Protocol):
    def generate(self, size_bits: int = 256) -> StoredKey: ...
    def health_check(self) -> dict: ...
```

`BB84KeySource` wraps the existing simulator; each vendor implements its own `KeySource`. `KeyPool.__init__()` accepts a `KeySource` parameter.

### Configuration Pattern

Each vendor module uses a `dataclass`-based config with environment variable fallbacks and a `from_env()` class method, consistent with how the existing code uses constants at module level (e.g., `kme_server.py:48-55`).

### Testing Pattern

All vendor integrations mock HTTP responses using `unittest.mock.patch` on `requests.get`/`requests.post`, following the existing test patterns in `tests/test_kme.py` and `tests/test_integration.py`. No vendor hardware is required for the test suite to pass.

### File Organization

Each vendor gets two files:

| File | Purpose |
|------|---------|
| `implementation/vendor_{name}.py` | Python module with client, adapter, pool classes |
| `implementation/vendor_{name}_config.md` | Provisioning and configuration documentation |

---

## Summary

| Plan | Vendor | Integration Level | Key File | CLI Flag |
|------|--------|--------------------|----------|----------|
| 1 | IBM Qiskit | Simulation (channel backend) | `qiskit_advanced.py` | `--backend realistic_noise` / `--backend ibm_hardware` |
| 2 | QuintessenceLabs TSF | KME (key source) | `vendor_quintessence.py` | `--key-source tsf` |
| 3 | ID Quantique Cerberis XG | KME (proxy) | `vendor_idq.py` | `--upstream-kme <url>` |
| 4 | Toshiba KME | KME (proxy + DWDM) | `vendor_toshiba.py` | `--upstream-kme <url> --vendor toshiba` |
| 5 | QuantumCTek NMS | KME + Relay Network | `vendor_quantumctek.py` | `--nms <url>` |
