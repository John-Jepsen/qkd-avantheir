"""
Toshiba QKD Key Manager Integration — ETSI 014 + DWDM Extensions

Extends the ETSI 014 client from vendor_idq.py with Toshiba-specific
capabilities: high key rates (63+ Mbps), DWDM co-existence monitoring,
and bulk pre-fetching optimized for Toshiba's throughput.

This module provides:
  - ToshibaConfig: Toshiba-specific connection parameters
  - ToshibaKMEClient: ETSI 014 client with Toshiba status extensions
  - ToshibaHighRatePool: bulk pre-fetching pool for high key rates
  - ToshibaDWDMMonitor: DWDM channel monitoring and QBER time series

Usage:
    from vendor_toshiba import ToshibaKMEClient, ToshibaConfig

    config = ToshibaConfig.from_env()
    client = ToshibaKMEClient(config)
    status = client.get_status_extended()

    # Or with KME server:
    #   python kme_server.py --upstream-kme https://toshiba-kme.local:8443 --vendor toshiba
"""

import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass

import numpy as np
import requests

from kme_server import StoredKey
from vendor_idq import CerberisConfig, CerberisKMEClient

log = logging.getLogger(__name__)


@dataclass
class ToshibaConfig(CerberisConfig):
    """Toshiba-specific configuration extending the base ETSI 014 config."""

    batch_size: int = 20
    pool_refill_trigger: int = 10
    pool_target: int = 50
    dwdm_poll_interval: float = 30.0

    @classmethod
    def from_env(cls) -> "ToshibaConfig":
        """Load configuration from environment variables."""
        return cls(
            base_url=os.environ.get("TOSHIBA_KME_URL", "https://toshiba-kme.local:8443"),
            sae_id=os.environ.get("TOSHIBA_SAE_ID", "sae-local"),
            client_cert=os.environ.get("TOSHIBA_CLIENT_CERT", ""),
            client_key=os.environ.get("TOSHIBA_CLIENT_KEY", ""),
            ca_cert=os.environ.get("TOSHIBA_CA_CERT", ""),
            timeout=int(os.environ.get("TOSHIBA_TIMEOUT", "10")),
            max_retries=int(os.environ.get("TOSHIBA_MAX_RETRIES", "3")),
            batch_size=int(os.environ.get("TOSHIBA_BATCH_SIZE", "20")),
            pool_refill_trigger=int(os.environ.get("TOSHIBA_POOL_REFILL_TRIGGER", "10")),
            pool_target=int(os.environ.get("TOSHIBA_POOL_TARGET", "50")),
            dwdm_poll_interval=float(os.environ.get("TOSHIBA_DWDM_POLL_INTERVAL", "30.0")),
        )


@dataclass
class ToshibaExtendedStatus:
    """Toshiba-specific status fields beyond standard ETSI 014."""

    stored_key_count: int = 0
    key_size: int = 256
    key_generation_rate_mbps: float = 0.0
    dwdm_channel: int = 0
    classical_traffic_gbps: float = 0.0
    quantum_channel_loss_db: float = 0.0
    qber: float = 0.0
    link_distance_km: float = 0.0


class ToshibaKMEClient(CerberisKMEClient):
    """
    ETSI 014 client with Toshiba-specific status extensions.

    Extends CerberisKMEClient to parse additional fields from Toshiba's
    status endpoint: key generation rate, DWDM channel info, and
    classical traffic throughput.
    """

    def __init__(self, config: ToshibaConfig | None = None) -> None:
        cfg = config or ToshibaConfig.from_env()
        super().__init__(cfg)
        log.info("ToshibaKMEClient: Toshiba-specific extensions enabled")

    def get_status_extended(self, slave_sae_id: str | None = None) -> ToshibaExtendedStatus:
        """Get Toshiba extended status including DWDM and key rate info."""
        data = self.get_status(slave_sae_id)
        return ToshibaExtendedStatus(
            stored_key_count=data.get("stored_key_count", 0),
            key_size=data.get("key_size", 256),
            key_generation_rate_mbps=data.get("key_generation_rate_mbps", 0.0),
            dwdm_channel=data.get("dwdm_channel", 0),
            classical_traffic_gbps=data.get("classical_traffic_gbps", 0.0),
            quantum_channel_loss_db=data.get("quantum_channel_loss_db", 0.0),
            qber=data.get("qber", 0.0),
            link_distance_km=data.get("link_distance_km", 0.0),
        )


class ToshibaHighRatePool:
    """
    Key pool optimized for Toshiba's high key rates (63+ Mbps).

    Instead of fetching one key at a time, this does bulk pre-fetching
    in configurable batch sizes, maintaining a local cache that refills
    asynchronously when stock drops below the trigger level.
    """

    def __init__(self, config: ToshibaConfig | None = None) -> None:
        self._config = config or ToshibaConfig.from_env()
        self._client = ToshibaKMEClient(self._config)
        self._cache: deque[StoredKey] = deque()
        self._pending: dict[str, StoredKey] = {}
        self._lock = threading.Lock()
        self._refilling = False
        log.info("ToshibaHighRatePool: batch=%d, target=%d, trigger=%d",
                 self._config.batch_size, self._config.pool_target,
                 self._config.pool_refill_trigger)

    def _bulk_fetch(self, count: int, size_bits: int = 256) -> list[StoredKey]:
        """Fetch a batch of keys from the Toshiba KME."""
        return self._client.get_enc_keys(count=count, size_bits=size_bits)

    def _maybe_refill(self) -> None:
        """Trigger async refill if cache is below threshold."""
        if len(self._cache) < self._config.pool_refill_trigger and not self._refilling:
            self._refilling = True
            threading.Thread(target=self._refill, daemon=True).start()

    def _refill(self) -> None:
        """Background refill to pool target."""
        try:
            while len(self._cache) < self._config.pool_target:
                batch = min(
                    self._config.batch_size,
                    self._config.pool_target - len(self._cache),
                )
                keys = self._bulk_fetch(batch)
                with self._lock:
                    self._cache.extend(keys)
                log.info("ToshibaHighRatePool: refilled %d keys (total: %d)",
                         len(keys), len(self._cache))
        except requests.RequestException as e:
            log.error("ToshibaHighRatePool: refill failed: %s", e)
        finally:
            self._refilling = False

    def get_keys(self, count: int, size_bits: int = 256) -> list[StoredKey]:
        """Get keys from local cache, fetching on-demand if needed."""
        with self._lock:
            keys = []
            while len(keys) < count and self._cache:
                keys.append(self._cache.popleft())

        # Fetch remaining directly if cache was insufficient
        if len(keys) < count:
            remaining = self._client.get_enc_keys(
                count=count - len(keys), size_bits=size_bits
            )
            keys.extend(remaining)

        for k in keys:
            self._pending[k.key_id] = k

        self._maybe_refill()
        return keys

    def get_by_ids(self, key_ids: list[str]) -> list[StoredKey]:
        """Retrieve keys by ID from pending or remote KME."""
        found = []
        remote_ids = []
        with self._lock:
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
        return len(self._cache)

    def health_check(self) -> dict:
        try:
            ext = self._client.get_status_extended()
            return {
                "status": "ok",
                "type": "toshiba_kme",
                "cached_keys": len(self._cache),
                "remote_keys": ext.stored_key_count,
                "key_rate_mbps": ext.key_generation_rate_mbps,
                "dwdm_channel": ext.dwdm_channel,
            }
        except requests.RequestException as e:
            return {"status": "error", "type": "toshiba_kme", "error": str(e)}


class ToshibaDWDMMonitor:
    """
    Monitors Toshiba DWDM co-existence metrics and builds QBER time series.

    Polls the Toshiba KME status endpoint at a configurable interval and
    feeds QBER data into a numpy array compatible with NoisePredictor.fit().
    """

    def __init__(self, client: ToshibaKMEClient, poll_interval: float = 30.0) -> None:
        self._client = client
        self._poll_interval = poll_interval
        self._qber_history: list[float] = []
        self._dwdm_history: list[dict] = []
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background polling thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        log.info("ToshibaDWDMMonitor: started polling every %.0fs", self._poll_interval)

    def stop(self) -> None:
        """Stop the background polling thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._poll_interval + 1)

    def _poll_loop(self) -> None:
        """Continuously poll the Toshiba KME for DWDM metrics."""
        while self._running:
            try:
                status = self._client.get_status_extended()
                self._qber_history.append(status.qber)
                self._dwdm_history.append({
                    "timestamp": time.time(),
                    "qber": status.qber,
                    "dwdm_channel": status.dwdm_channel,
                    "classical_traffic_gbps": status.classical_traffic_gbps,
                    "quantum_channel_loss_db": status.quantum_channel_loss_db,
                    "key_rate_mbps": status.key_generation_rate_mbps,
                })
            except requests.RequestException as e:
                log.warning("DWDM poll failed: %s", e)

            time.sleep(self._poll_interval)

    def get_noise_series(self) -> np.ndarray:
        """Return QBER time series as numpy array for NoisePredictor.fit()."""
        return np.array(self._qber_history) if self._qber_history else np.array([])

    @property
    def qber_history(self) -> list[float]:
        return list(self._qber_history)

    @property
    def dwdm_history(self) -> list[dict]:
        return list(self._dwdm_history)
