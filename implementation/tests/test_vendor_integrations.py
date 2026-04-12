"""
Tests for vendor integrations — QuintessenceLabs, IDQ, Toshiba, QuantumCTek.

All tests mock HTTP responses so no vendor hardware is required.
"""

import base64
import json
import os
import uuid

import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Helper: mock ETSI 014 key response ──────────────────────────────────────

def _mock_key_response(count=1, size_bytes=32):
    """Build a mock ETSI 014 JSON response with random keys."""
    keys = []
    for _ in range(count):
        keys.append({
            "key_ID": str(uuid.uuid4()),
            "key": base64.b64encode(os.urandom(size_bytes)).decode(),
        })
    return {"keys": keys}


def _mock_response(json_data, status_code=200):
    """Create a mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


# ── QuintessenceLabs TSF ────────────────────────────────────────────────────

class TestTSFKeySource:
    def test_generate_key(self):
        from vendor_quintessence import TSFKeySource, TSFConfig

        key_bytes = os.urandom(32)
        mock_resp = _mock_response({
            "key": base64.b64encode(key_bytes).decode(),
            "key_id": "tsf-key-001",
        })

        config = TSFConfig(base_url="https://mock-tsf:8443")
        source = TSFKeySource(config)

        with patch.object(source._session, "post", return_value=mock_resp):
            key = source.generate(size_bits=256)
            assert key.key_bytes == key_bytes
            assert key.key_id == "tsf-key-001"
            assert key.size_bits == 256

    def test_health_check_ok(self):
        from vendor_quintessence import TSFKeySource, TSFConfig

        mock_resp = _mock_response({
            "status": "ok",
            "qkd_link_active": True,
            "qrng_entropy_bps": 1000000,
            "key_pool_depth": 500,
        })

        config = TSFConfig(base_url="https://mock-tsf:8443")
        source = TSFKeySource(config)

        with patch.object(source._session, "get", return_value=mock_resp):
            health = source.health_check()
            assert health["status"] == "ok"
            assert health["qkd_link_active"] is True
            assert health["type"] == "quintessencelabs_tsf"

    def test_health_check_failure(self):
        import requests
        from vendor_quintessence import TSFKeySource, TSFConfig

        config = TSFConfig(base_url="https://mock-tsf:8443")
        source = TSFKeySource(config)

        with patch.object(source._session, "get",
                          side_effect=requests.ConnectionError("refused")):
            health = source.health_check()
            assert health["status"] == "error"

    def test_config_from_env(self):
        from vendor_quintessence import TSFConfig

        with patch.dict(os.environ, {
            "TSF_BASE_URL": "https://mytsf:9443",
            "TSF_API_KEY": "secret123",
            "TSF_KEY_POLICY": "high_security",
        }):
            config = TSFConfig.from_env()
            assert config.base_url == "https://mytsf:9443"
            assert config.api_key == "secret123"
            assert config.key_policy == "high_security"


# ── ID Quantique Cerberis XG ───────────────────────────────────────────────

class TestCerberisKMEClient:
    def test_get_status(self):
        from vendor_idq import CerberisKMEClient, CerberisConfig

        mock_resp = _mock_response({
            "source_KME_ID": "cerberis-01",
            "stored_key_count": 42,
            "key_size": 256,
        })

        config = CerberisConfig(base_url="https://mock-cerberis:8443")
        client = CerberisKMEClient(config)

        with patch.object(client._session, "request", return_value=mock_resp):
            status = client.get_status()
            assert status["stored_key_count"] == 42

    def test_get_enc_keys(self):
        from vendor_idq import CerberisKMEClient, CerberisConfig

        mock_resp = _mock_response(_mock_key_response(count=3))

        config = CerberisConfig(base_url="https://mock-cerberis:8443")
        client = CerberisKMEClient(config)

        with patch.object(client._session, "request", return_value=mock_resp):
            keys = client.get_enc_keys(count=3, size_bits=256)
            assert len(keys) == 3
            assert all(len(k.key_bytes) == 32 for k in keys)

    def test_get_dec_keys(self):
        from vendor_idq import CerberisKMEClient, CerberisConfig

        kid = str(uuid.uuid4())
        key_bytes = os.urandom(32)
        mock_resp = _mock_response({
            "keys": [{"key_ID": kid, "key": base64.b64encode(key_bytes).decode()}]
        })

        config = CerberisConfig(base_url="https://mock-cerberis:8443")
        client = CerberisKMEClient(config)

        with patch.object(client._session, "request", return_value=mock_resp):
            keys = client.get_dec_keys([kid])
            assert len(keys) == 1
            assert keys[0].key_id == kid
            assert keys[0].key_bytes == key_bytes

    def test_retry_on_failure(self):
        import requests as req
        from vendor_idq import CerberisKMEClient, CerberisConfig

        config = CerberisConfig(
            base_url="https://mock-cerberis:8443",
            max_retries=3,
            retry_backoff=0.01,
        )
        client = CerberisKMEClient(config)

        success_resp = _mock_response({"stored_key_count": 10})
        with patch.object(
            client._session, "request",
            side_effect=[req.ConnectionError("fail"), success_resp]
        ):
            status = client.get_status()
            assert status["stored_key_count"] == 10


class TestCerberisProxyPool:
    def test_get_keys_and_retrieve(self):
        from vendor_idq import CerberisProxyPool, CerberisConfig

        key_data = _mock_key_response(count=2)
        mock_resp = _mock_response(key_data)

        config = CerberisConfig(base_url="https://mock-cerberis:8443")
        pool = CerberisProxyPool(config)

        with patch.object(pool._client._session, "request", return_value=mock_resp):
            keys = pool.get_keys(count=2)
            assert len(keys) == 2

        # Retrieve by ID from pending (no HTTP call needed)
        kid = keys[0].key_id
        found = pool.get_by_ids([kid])
        assert len(found) == 1
        assert found[0].key_id == kid


# ── Toshiba KME ─────────────────────────────────────────────────────────────

class TestToshibaKMEClient:
    def test_extended_status(self):
        from vendor_toshiba import ToshibaKMEClient, ToshibaConfig

        mock_resp = _mock_response({
            "stored_key_count": 100,
            "key_size": 256,
            "key_generation_rate_mbps": 63.5,
            "dwdm_channel": 34,
            "classical_traffic_gbps": 10.2,
            "quantum_channel_loss_db": 3.5,
            "qber": 0.023,
            "link_distance_km": 50.0,
        })

        config = ToshibaConfig(base_url="https://mock-toshiba:8443")
        client = ToshibaKMEClient(config)

        with patch.object(client._session, "request", return_value=mock_resp):
            ext = client.get_status_extended()
            assert ext.key_generation_rate_mbps == 63.5
            assert ext.dwdm_channel == 34
            assert ext.qber == 0.023
            assert ext.link_distance_km == 50.0


class TestToshibaHighRatePool:
    def test_get_keys_from_cache(self):
        from vendor_toshiba import ToshibaHighRatePool, ToshibaConfig

        mock_resp = _mock_response(_mock_key_response(count=5))

        config = ToshibaConfig(
            base_url="https://mock-toshiba:8443",
            pool_target=5,
            pool_refill_trigger=2,
        )
        pool = ToshibaHighRatePool(config)

        with patch.object(pool._client._session, "request", return_value=mock_resp):
            keys = pool.get_keys(count=3)
            assert len(keys) == 3

    def test_health_check(self):
        from vendor_toshiba import ToshibaHighRatePool, ToshibaConfig

        mock_resp = _mock_response({
            "stored_key_count": 200,
            "key_generation_rate_mbps": 63.5,
            "dwdm_channel": 34,
        })

        config = ToshibaConfig(base_url="https://mock-toshiba:8443")
        pool = ToshibaHighRatePool(config)

        with patch.object(pool._client._session, "request", return_value=mock_resp):
            health = pool.health_check()
            assert health["status"] == "ok"
            assert health["type"] == "toshiba_kme"
            assert health["key_rate_mbps"] == 63.5


class TestToshibaDWDMMonitor:
    def test_get_noise_series_empty(self):
        import numpy as np
        from vendor_toshiba import ToshibaDWDMMonitor, ToshibaKMEClient, ToshibaConfig

        config = ToshibaConfig(base_url="https://mock-toshiba:8443")
        client = ToshibaKMEClient(config)
        monitor = ToshibaDWDMMonitor(client)

        series = monitor.get_noise_series()
        assert len(series) == 0
        assert isinstance(series, np.ndarray)


# ── QuantumCTek NMS ─────────────────────────────────────────────────────────

class TestQCTekNMSClient:
    def test_get_nodes(self):
        from vendor_quantumctek import QCTekNMSClient, QCTekConfig

        mock_resp = _mock_response({
            "nodes": [
                {"nodeId": "beijing", "nodeName": "Beijing Hub",
                 "nodeType": "hub", "nodeStatus": "online"},
                {"nodeId": "shanghai", "nodeName": "Shanghai Endpoint",
                 "nodeType": "endpoint", "nodeStatus": "online"},
            ]
        })

        config = QCTekConfig(nms_url="https://mock-nms:9443")
        client = QCTekNMSClient(config)

        with patch.object(client._session, "get", return_value=mock_resp):
            nodes = client.get_nodes()
            assert len(nodes) == 2
            assert nodes[0].node_id == "beijing"
            assert nodes[0].node_type == "hub"

    def test_get_links(self):
        from vendor_quantumctek import QCTekNMSClient, QCTekConfig

        mock_resp = _mock_response({
            "links": [
                {"linkId": "link-001", "nodeA": "beijing", "nodeB": "jinan",
                 "linkStatus": "active", "qber": 0.018, "keyRateKbps": 50.0,
                 "distanceKm": 450.0},
            ]
        })

        config = QCTekConfig(nms_url="https://mock-nms:9443")
        client = QCTekNMSClient(config)

        with patch.object(client._session, "get", return_value=mock_resp):
            links = client.get_links()
            assert len(links) == 1
            assert links[0].node_a == "beijing"
            assert links[0].qber == 0.018
            assert links[0].distance_km == 450.0

    def test_get_link_key(self):
        from vendor_quantumctek import QCTekNMSClient, QCTekConfig

        key_bytes = os.urandom(32)
        mock_resp = _mock_response({
            "keys": [{
                "keyId": "lk-key-001",
                "keyValue": base64.b64encode(key_bytes).decode(),
            }]
        })

        config = QCTekConfig(nms_url="https://mock-nms:9443")
        client = QCTekNMSClient(config)

        with patch.object(client._session, "post", return_value=mock_resp):
            key = client.get_link_key("beijing", "jinan")
            assert key.key_bytes == key_bytes
            assert key.key_id == "lk-key-001"

    def test_health_check(self):
        from vendor_quantumctek import QCTekNMSClient, QCTekConfig

        mock_resp = _mock_response({
            "status": "ok",
            "nodeCount": 145,
            "activeLinkCount": 200,
        })

        config = QCTekConfig(nms_url="https://mock-nms:9443")
        client = QCTekNMSClient(config)

        with patch.object(client._session, "get", return_value=mock_resp):
            health = client.health_check()
            assert health["status"] == "ok"
            assert health["node_count"] == 145
            assert health["active_links"] == 200


class TestQCTekETSI014Adapter:
    def test_parse_proprietary_response(self):
        from vendor_quantumctek import QCTekETSI014Adapter

        key_bytes = os.urandom(32)
        data = {
            "keys": [{
                "keyId": "prop-001",
                "keyValue": base64.b64encode(key_bytes).decode(),
                "keyLength": 256,
            }]
        }

        keys = QCTekETSI014Adapter.parse_response(data)
        assert len(keys) == 1
        assert keys[0].key_id == "prop-001"
        assert keys[0].key_bytes == key_bytes

    def test_parse_etsi014_response(self):
        from vendor_quantumctek import QCTekETSI014Adapter

        key_bytes = os.urandom(32)
        data = {
            "keys": [{
                "key_ID": "etsi-001",
                "key": base64.b64encode(key_bytes).decode(),
                "key_size": 256,
            }]
        }

        keys = QCTekETSI014Adapter.parse_response(data)
        assert len(keys) == 1
        assert keys[0].key_id == "etsi-001"
        assert keys[0].key_bytes == key_bytes

    def test_to_etsi014_format(self):
        from vendor_quantumctek import QCTekETSI014Adapter
        from kme_server import StoredKey

        key_bytes = os.urandom(32)
        keys = [StoredKey(key_id="test-001", key_bytes=key_bytes, size_bits=256)]
        result = QCTekETSI014Adapter.to_etsi014(keys)

        assert "keys" in result
        assert result["keys"][0]["key_ID"] == "test-001"
        assert base64.b64decode(result["keys"][0]["key"]) == key_bytes

    def test_from_proprietary_status(self):
        from vendor_quantumctek import QCTekETSI014Adapter

        data = {
            "sourceKmeId": "kme-beijing",
            "targetKmeId": "kme-jinan",
            "storedKeyCount": 500,
            "keyLength": 256,
            "maxKeyPerRequest": 20,
        }
        result = QCTekETSI014Adapter.from_proprietary_status(data)
        assert result["source_KME_ID"] == "kme-beijing"
        assert result["stored_key_count"] == 500
        assert result["max_key_per_request"] == 20


# ── KeySource protocol ──────────────────────────────────────────────────────

class TestKeySourceProtocol:
    def test_bb84_key_source(self):
        from key_source import BB84KeySource, KeySource

        source = BB84KeySource(error_rate=0.01, backend="classical")
        assert isinstance(source, KeySource)

        key = source.generate(size_bits=256)
        assert len(key.key_bytes) == 32
        assert key.size_bits == 256

    def test_bb84_health_check(self):
        from key_source import BB84KeySource

        source = BB84KeySource(backend="classical")
        health = source.health_check()
        assert health["status"] == "ok"
        assert health["type"] == "bb84_simulator"
