"""
QuintessenceLabs TSF (Trusted Security Foundation) Integration

Integrates with QuintessenceLabs' unified key management platform, which
manages keys from both QKD (qOptica) and QRNG (qStream) sources. TSF
exposes a REST API for key lifecycle management.

This module provides:
  - TSFConfig: connection parameters for the TSF appliance
  - TSFKeySource: KeySource implementation that fetches keys from TSF
  - TSFHealthChecker: monitors TSF health, entropy levels, and QKD link status

Usage:
    from vendor_quintessence import TSFKeySource, TSFConfig

    config = TSFConfig.from_env()
    source = TSFKeySource(config)
    key = source.generate(size_bits=256)

    # Or with KME server:
    #   python kme_server.py --key-source tsf
"""

import base64
import logging
import os
import uuid
from dataclasses import dataclass, field

import requests

from kme_server import StoredKey

log = logging.getLogger(__name__)


@dataclass
class TSFConfig:
    """Connection parameters for a QuintessenceLabs TSF appliance."""

    base_url: str = "https://tsf.local:8443"
    client_cert: str = ""
    client_key: str = ""
    ca_cert: str = ""
    api_key: str = ""
    key_policy: str = "default"
    timeout: int = 10

    @classmethod
    def from_env(cls) -> "TSFConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.environ.get("TSF_BASE_URL", "https://tsf.local:8443"),
            client_cert=os.environ.get("TSF_CLIENT_CERT", ""),
            client_key=os.environ.get("TSF_CLIENT_KEY", ""),
            ca_cert=os.environ.get("TSF_CA_CERT", ""),
            api_key=os.environ.get("TSF_API_KEY", ""),
            key_policy=os.environ.get("TSF_KEY_POLICY", "default"),
            timeout=int(os.environ.get("TSF_TIMEOUT", "10")),
        )

    @property
    def cert_tuple(self) -> tuple[str, str] | None:
        """Return (cert, key) tuple for requests mTLS, or None."""
        if self.client_cert and self.client_key:
            return (self.client_cert, self.client_key)
        return None

    @property
    def verify(self) -> str | bool:
        """Return CA cert path for verification, or True for system CA."""
        return self.ca_cert if self.ca_cert else True


class TSFKeySource:
    """
    KeySource implementation backed by QuintessenceLabs TSF.

    Fetches keys from the TSF REST API. TSF internally manages the QKD
    hardware (qOptica) and QRNG (qStream); the API consumer just requests
    keys by policy.
    """

    def __init__(self, config: TSFConfig | None = None) -> None:
        self._config = config or TSFConfig.from_env()
        self._session = requests.Session()
        if self._config.cert_tuple:
            self._session.cert = self._config.cert_tuple
        self._session.verify = self._config.verify
        if self._config.api_key:
            self._session.headers["Authorization"] = f"Bearer {self._config.api_key}"
        log.info("TSFKeySource: configured for %s", self._config.base_url)

    def generate(self, size_bits: int = 256) -> StoredKey:
        """Request a key from TSF."""
        size_bytes = size_bits // 8

        resp = self._session.post(
            f"{self._config.base_url}/api/v1/keys/generate",
            json={
                "size": size_bytes,
                "policy": self._config.key_policy,
                "source": "qkd_preferred",
            },
            timeout=self._config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        key_bytes = base64.b64decode(data["key"])
        key_id = data.get("key_id", str(uuid.uuid4()))

        log.info("TSFKeySource: generated %d-bit key %s", size_bits, key_id)
        return StoredKey(
            key_id=key_id,
            key_bytes=key_bytes[:size_bytes],
            size_bits=size_bits,
        )

    def health_check(self) -> dict:
        """Check TSF appliance health."""
        try:
            resp = self._session.get(
                f"{self._config.base_url}/api/v1/health",
                timeout=self._config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status", "ok"),
                "type": "quintessencelabs_tsf",
                "qkd_link_active": data.get("qkd_link_active", False),
                "qrng_entropy_bps": data.get("qrng_entropy_bps", 0),
                "key_pool_depth": data.get("key_pool_depth", 0),
            }
        except requests.RequestException as e:
            log.error("TSF health check failed: %s", e)
            return {"status": "error", "type": "quintessencelabs_tsf", "error": str(e)}


class TSFHealthChecker:
    """Periodic health monitor for QuintessenceLabs TSF."""

    def __init__(self, source: TSFKeySource) -> None:
        self._source = source
        self._history: list[dict] = []

    def check(self) -> dict:
        """Run a health check and record the result."""
        result = self._source.health_check()
        self._history.append(result)
        return result

    @property
    def last_status(self) -> str:
        if not self._history:
            return "unknown"
        return self._history[-1].get("status", "unknown")

    @property
    def history(self) -> list[dict]:
        return list(self._history)
