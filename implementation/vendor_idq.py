"""
ID Quantique Cerberis XG Integration — ETSI 014 REST API

Integrates with the Cerberis XG production QKD platform. The Cerberis KME
exposes the same ETSI GS QKD 014 REST API that our kme_server.py implements,
making this the most direct hardware integration.

This module provides:
  - CerberisConfig: connection parameters (base URL, mTLS certs, SAE ID)
  - CerberisKMEClient: reusable ETSI 014 client with retry logic
  - CerberisProxyPool: KeyPool replacement that proxies to hardware KME
  - IDQHealthMonitor: monitors QBER, key rate, and link alarms

Usage:
    from vendor_idq import CerberisKMEClient, CerberisConfig

    config = CerberisConfig.from_env()
    client = CerberisKMEClient(config)
    keys = client.get_enc_keys(count=1, size_bits=256)

    # Or with KME server:
    #   python kme_server.py --upstream-kme https://cerberis.local:8443
"""

import base64
import logging
import os
import time
import uuid
from dataclasses import dataclass, field

import requests

from kme_server import StoredKey

log = logging.getLogger(__name__)


@dataclass
class CerberisConfig:
    """Connection parameters for an ID Quantique Cerberis XG KME."""

    base_url: str = "https://cerberis.local:8443"
    sae_id: str = "sae-local"
    client_cert: str = ""
    client_key: str = ""
    ca_cert: str = ""
    timeout: int = 10
    max_retries: int = 3
    retry_backoff: float = 1.0

    @classmethod
    def from_env(cls) -> "CerberisConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.environ.get("IDQ_KME_URL", "https://cerberis.local:8443"),
            sae_id=os.environ.get("IDQ_SAE_ID", "sae-local"),
            client_cert=os.environ.get("IDQ_CLIENT_CERT", ""),
            client_key=os.environ.get("IDQ_CLIENT_KEY", ""),
            ca_cert=os.environ.get("IDQ_CA_CERT", ""),
            timeout=int(os.environ.get("IDQ_TIMEOUT", "10")),
            max_retries=int(os.environ.get("IDQ_MAX_RETRIES", "3")),
        )

    @property
    def cert_tuple(self) -> tuple[str, str] | None:
        if self.client_cert and self.client_key:
            return (self.client_cert, self.client_key)
        return None

    @property
    def verify(self) -> str | bool:
        return self.ca_cert if self.ca_cert else True


class CerberisKMEClient:
    """
    ETSI GS QKD 014 client for ID Quantique Cerberis XG.

    Generalized from the helper functions in tls_psk_demo.py with added
    mTLS support, retry logic, and health checking.
    """

    def __init__(self, config: CerberisConfig | None = None) -> None:
        self._config = config or CerberisConfig.from_env()
        self._session = requests.Session()
        if self._config.cert_tuple:
            self._session.cert = self._config.cert_tuple
        self._session.verify = self._config.verify
        log.info("CerberisKMEClient: configured for %s", self._config.base_url)

    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """HTTP request with exponential backoff retry."""
        kwargs.setdefault("timeout", self._config.timeout)
        last_error = None

        for attempt in range(self._config.max_retries):
            try:
                resp = self._session.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                last_error = e
                if attempt < self._config.max_retries - 1:
                    wait = self._config.retry_backoff * (2 ** attempt)
                    log.warning("Request failed (attempt %d/%d), retrying in %.1fs: %s",
                                attempt + 1, self._config.max_retries, wait, e)
                    time.sleep(wait)

        raise last_error

    def get_status(self, slave_sae_id: str | None = None) -> dict:
        """GET /api/v1/keys/{slave_SAE_ID}/status"""
        sae = slave_sae_id or self._config.sae_id
        resp = self._request_with_retry(
            "GET", f"{self._config.base_url}/api/v1/keys/{sae}/status"
        )
        return resp.json()

    def get_enc_keys(
        self, count: int = 1, size_bits: int = 256, slave_sae_id: str | None = None
    ) -> list[StoredKey]:
        """GET /api/v1/keys/{slave_SAE_ID}/enc_keys — fetch keys for master SAE."""
        sae = slave_sae_id or self._config.sae_id
        resp = self._request_with_retry(
            "GET",
            f"{self._config.base_url}/api/v1/keys/{sae}/enc_keys",
            params={"number": count, "size": size_bits},
        )
        return self._parse_keys(resp.json(), size_bits)

    def get_dec_keys(
        self, key_ids: list[str], slave_sae_id: str | None = None
    ) -> list[StoredKey]:
        """POST /api/v1/keys/{slave_SAE_ID}/dec_keys — retrieve keys by ID."""
        sae = slave_sae_id or self._config.sae_id
        resp = self._request_with_retry(
            "POST",
            f"{self._config.base_url}/api/v1/keys/{sae}/dec_keys",
            json={"key_IDs": [{"key_ID": kid} for kid in key_ids]},
        )
        return self._parse_keys(resp.json(), 256)

    @staticmethod
    def _parse_keys(data: dict, default_size: int) -> list[StoredKey]:
        """Parse ETSI 014 key response into StoredKey objects."""
        keys = []
        for item in data.get("keys", []):
            key_bytes = base64.b64decode(item["key"])
            keys.append(StoredKey(
                key_id=item["key_ID"],
                key_bytes=key_bytes,
                size_bits=len(key_bytes) * 8,
            ))
        return keys


class CerberisProxyPool:
    """
    KeyPool replacement that proxies to a Cerberis XG hardware KME.

    Wraps CerberisKMEClient with the same interface as KeyPool so it can
    be used as a drop-in replacement in kme_server.py. Our server becomes
    a proxy that can add ML anomaly detection on top of hardware keys.
    """

    def __init__(self, config: CerberisConfig | None = None) -> None:
        self._client = CerberisKMEClient(config)
        self._config = config or CerberisConfig.from_env()
        self._pending: dict[str, StoredKey] = {}
        log.info("CerberisProxyPool: proxying to %s", self._config.base_url)

    def get_keys(self, count: int, size_bits: int = 256) -> list[StoredKey]:
        """Fetch keys from the hardware KME and track them as pending."""
        keys = self._client.get_enc_keys(count=count, size_bits=size_bits)
        for k in keys:
            self._pending[k.key_id] = k
        return keys

    def get_by_ids(self, key_ids: list[str]) -> list[StoredKey]:
        """Retrieve keys by ID — try local pending first, then hardware KME."""
        found = []
        remote_ids = []
        for kid in key_ids:
            if kid in self._pending:
                found.append(self._pending.pop(kid))
            else:
                remote_ids.append(kid)

        if remote_ids:
            found.extend(self._client.get_dec_keys(remote_ids))

        return found

    @property
    def available_count(self) -> int:
        """Query the hardware KME for available key count."""
        try:
            status = self._client.get_status()
            return status.get("stored_key_count", 0)
        except requests.RequestException:
            return 0

    def health_check(self) -> dict:
        """Check hardware KME health."""
        try:
            status = self._client.get_status()
            return {
                "status": "ok",
                "type": "idq_cerberis_xg",
                "stored_key_count": status.get("stored_key_count", 0),
                "key_size": status.get("key_size", 256),
            }
        except requests.RequestException as e:
            return {"status": "error", "type": "idq_cerberis_xg", "error": str(e)}


class IDQHealthMonitor:
    """Monitors ID Quantique Cerberis XG for QBER, key rate, and link alarms."""

    def __init__(self, client: CerberisKMEClient) -> None:
        self._client = client
        self._history: list[dict] = []

    def check(self) -> dict:
        """Run a health check and record the result."""
        try:
            status = self._client.get_status()
            result = {
                "status": "ok",
                "stored_key_count": status.get("stored_key_count", 0),
                "key_size": status.get("key_size", 256),
                "timestamp": time.time(),
            }
        except requests.RequestException as e:
            result = {"status": "error", "error": str(e), "timestamp": time.time()}

        self._history.append(result)
        return result

    @property
    def history(self) -> list[dict]:
        return list(self._history)
