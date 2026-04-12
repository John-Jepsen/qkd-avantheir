"""
QuantumCTek QKD NMS Integration — Network Management Platform

Integrates with QuantumCTek's proprietary NMS which manages large-scale
QKD networks (12,000+ km, 145 nodes in the Chinese national network).
Provides proprietary management APIs alongside partial ETSI compliance,
with emphasis on trusted-node relay orchestration.

This module provides:
  - QCTekConfig: NMS connection parameters
  - QCTekNMSClient: client for the proprietary NMS REST API
  - QCTekETSI014Adapter: normalizes proprietary responses to ETSI 014 JSON
  - QCTekRelayOrchestrator: integrates with relay_network.py for multi-hop relay
  - QCTekNetworkTopologySync: syncs live NMS topology to QKDRelayNetwork

Usage:
    from vendor_quantumctek import QCTekNMSClient, QCTekConfig

    config = QCTekConfig.from_env()
    client = QCTekNMSClient(config)
    nodes = client.get_nodes()

    # Or with relay network:
    #   python relay_network.py --nms https://qctek-nms.local:9443
"""

import base64
import logging
import os
import threading
import time
import uuid
from dataclasses import dataclass, field

import requests

from kme_server import StoredKey

log = logging.getLogger(__name__)


@dataclass
class QCTekConfig:
    """Connection parameters for a QuantumCTek NMS."""

    nms_url: str = "https://qctek-nms.local:9443"
    api_key: str = ""
    network_id: str = "default"
    client_cert: str = ""
    client_key: str = ""
    ca_cert: str = ""
    timeout: int = 15
    topology_poll_interval: float = 60.0

    @classmethod
    def from_env(cls) -> "QCTekConfig":
        """Load configuration from environment variables."""
        return cls(
            nms_url=os.environ.get("QCTEK_NMS_URL", "https://qctek-nms.local:9443"),
            api_key=os.environ.get("QCTEK_API_KEY", ""),
            network_id=os.environ.get("QCTEK_NETWORK_ID", "default"),
            client_cert=os.environ.get("QCTEK_CLIENT_CERT", ""),
            client_key=os.environ.get("QCTEK_CLIENT_KEY", ""),
            ca_cert=os.environ.get("QCTEK_CA_CERT", ""),
            timeout=int(os.environ.get("QCTEK_TIMEOUT", "15")),
            topology_poll_interval=float(
                os.environ.get("QCTEK_TOPOLOGY_POLL_INTERVAL", "60.0")
            ),
        )

    @property
    def cert_tuple(self) -> tuple[str, str] | None:
        if self.client_cert and self.client_key:
            return (self.client_cert, self.client_key)
        return None

    @property
    def verify(self) -> str | bool:
        return self.ca_cert if self.ca_cert else True


@dataclass
class QCTekNode:
    """A node in the QuantumCTek QKD network."""

    node_id: str
    name: str
    node_type: str  # "endpoint", "relay", "hub"
    status: str  # "online", "offline", "degraded"
    location: str = ""


@dataclass
class QCTekLink:
    """A QKD link between two nodes in the QuantumCTek network."""

    link_id: str
    node_a: str
    node_b: str
    status: str  # "active", "inactive", "degraded"
    qber: float = 0.0
    key_rate_kbps: float = 0.0
    distance_km: float = 0.0


class QCTekNMSClient:
    """
    Client for the QuantumCTek proprietary NMS REST API.

    Handles node management, link status, key retrieval, and relay path
    selection. Unlike pure ETSI 014 vendors, QuantumCTek's NMS has a
    proprietary layer for network-wide operations.
    """

    def __init__(self, config: QCTekConfig | None = None) -> None:
        self._config = config or QCTekConfig.from_env()
        self._session = requests.Session()
        if self._config.cert_tuple:
            self._session.cert = self._config.cert_tuple
        self._session.verify = self._config.verify
        if self._config.api_key:
            self._session.headers["X-API-Key"] = self._config.api_key
        self._session.headers["Content-Type"] = "application/json"
        log.info("QCTekNMSClient: configured for %s (network: %s)",
                 self._config.nms_url, self._config.network_id)

    def _url(self, path: str) -> str:
        return f"{self._config.nms_url}/api/v1/networks/{self._config.network_id}{path}"

    def get_nodes(self) -> list[QCTekNode]:
        """List all nodes in the network."""
        resp = self._session.get(
            self._url("/nodes"), timeout=self._config.timeout
        )
        resp.raise_for_status()
        return [
            QCTekNode(
                node_id=n["nodeId"],
                name=n.get("nodeName", n["nodeId"]),
                node_type=n.get("nodeType", "endpoint"),
                status=n.get("nodeStatus", "unknown"),
                location=n.get("location", ""),
            )
            for n in resp.json().get("nodes", [])
        ]

    def get_links(self) -> list[QCTekLink]:
        """List all QKD links in the network."""
        resp = self._session.get(
            self._url("/links"), timeout=self._config.timeout
        )
        resp.raise_for_status()
        return [
            QCTekLink(
                link_id=lk["linkId"],
                node_a=lk["nodeA"],
                node_b=lk["nodeB"],
                status=lk.get("linkStatus", "unknown"),
                qber=lk.get("qber", 0.0),
                key_rate_kbps=lk.get("keyRateKbps", 0.0),
                distance_km=lk.get("distanceKm", 0.0),
            )
            for lk in resp.json().get("links", [])
        ]

    def get_link_key(self, node_a: str, node_b: str) -> StoredKey:
        """Fetch a link key between two adjacent nodes."""
        resp = self._session.post(
            self._url("/keys/link"),
            json={"nodeA": node_a, "nodeB": node_b, "count": 1, "size": 256},
            timeout=self._config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        key_data = data["keys"][0]
        key_bytes = base64.b64decode(key_data["keyValue"])
        return StoredKey(
            key_id=key_data.get("keyId", str(uuid.uuid4())),
            key_bytes=key_bytes,
            size_bits=len(key_bytes) * 8,
        )

    def get_relay_path(self, source: str, dest: str) -> list[str]:
        """Ask the NMS to compute the optimal relay path."""
        resp = self._session.post(
            self._url("/routing/path"),
            json={"source": source, "destination": dest},
            timeout=self._config.timeout,
        )
        resp.raise_for_status()
        return resp.json().get("path", [])

    def get_key(
        self, sae_id: str, count: int = 1, size_bits: int = 256
    ) -> list[StoredKey]:
        """ETSI 014-style key retrieval via the NMS compatibility layer."""
        resp = self._session.get(
            f"{self._config.nms_url}/etsi/api/v1/keys/{sae_id}/enc_keys",
            params={"number": count, "size": size_bits},
            timeout=self._config.timeout,
        )
        resp.raise_for_status()
        return QCTekETSI014Adapter.parse_response(resp.json())

    def health_check(self) -> dict:
        """Check NMS health."""
        try:
            resp = self._session.get(
                f"{self._config.nms_url}/api/v1/health",
                timeout=self._config.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": data.get("status", "ok"),
                "type": "quantumctek_nms",
                "network_id": self._config.network_id,
                "node_count": data.get("nodeCount", 0),
                "active_links": data.get("activeLinkCount", 0),
            }
        except requests.RequestException as e:
            return {"status": "error", "type": "quantumctek_nms", "error": str(e)}


class QCTekETSI014Adapter:
    """
    Normalizes QuantumCTek proprietary response format to ETSI 014 JSON.

    Field mapping:
      "keyId"     -> "key_ID"
      "keyValue"  -> "key" (base64)
      "keyLength" -> "key_size"
    """

    @staticmethod
    def parse_response(data: dict) -> list[StoredKey]:
        """Parse a QuantumCTek response into StoredKey objects."""
        keys = []
        for item in data.get("keys", []):
            # Handle both proprietary and ETSI field names
            key_id = item.get("keyId", item.get("key_ID", str(uuid.uuid4())))
            key_b64 = item.get("keyValue", item.get("key", ""))
            key_bytes = base64.b64decode(key_b64)
            size = item.get("keyLength", item.get("key_size", len(key_bytes) * 8))

            keys.append(StoredKey(
                key_id=key_id,
                key_bytes=key_bytes,
                size_bits=size,
            ))
        return keys

    @staticmethod
    def to_etsi014(keys: list[StoredKey]) -> dict:
        """Convert StoredKey objects to ETSI 014 response format."""
        return {
            "keys": [
                {
                    "key_ID": k.key_id,
                    "key": base64.b64encode(k.key_bytes).decode(),
                }
                for k in keys
            ]
        }

    @staticmethod
    def from_proprietary_status(data: dict) -> dict:
        """Convert QuantumCTek status to ETSI 014 status format."""
        return {
            "source_KME_ID": data.get("sourceKmeId", ""),
            "target_KME_ID": data.get("targetKmeId", ""),
            "master_SAE_ID": data.get("masterSaeId", ""),
            "slave_SAE_ID": data.get("slaveSaeId", ""),
            "key_size": data.get("keyLength", 256),
            "stored_key_count": data.get("storedKeyCount", 0),
            "max_key_count": data.get("maxKeyCount", 0),
            "max_key_per_request": data.get("maxKeyPerRequest", 20),
            "max_key_size": data.get("maxKeyLength", 1024),
            "min_key_size": data.get("minKeyLength", 64),
        }


class QCTekRelayOrchestrator:
    """
    Relay orchestrator that integrates QuantumCTek NMS with relay_network.py.

    Instead of running BB84 simulations for each link, this fetches real
    link keys from the NMS and can delegate path finding to the NMS
    which has global topology knowledge.
    """

    def __init__(self, client: QCTekNMSClient) -> None:
        self._client = client
        self._network = None

    def build_from_nms(self) -> "QCTekRelayOrchestrator":
        """Build a QKDRelayNetwork from the live NMS topology."""
        from relay_network import QKDRelayNetwork, QKDLink

        nodes = self._client.get_nodes()
        links = self._client.get_links()

        net = QKDRelayNetwork.__new__(QKDRelayNetwork)
        net._nodes = set()
        net._links = {}
        net._graph = {}
        net._proto = None  # Not used — keys come from NMS

        for node in nodes:
            if node.status != "offline":
                net._nodes.add(node.node_id)
                net._graph[node.node_id] = []

        for link in links:
            if link.node_a in net._nodes and link.node_b in net._nodes:
                canonical = (
                    (link.node_a, link.node_b)
                    if link.node_a < link.node_b
                    else (link.node_b, link.node_a)
                )
                # Placeholder link key — real keys fetched on-demand during relay
                net._links[canonical] = QKDLink(
                    node_a=link.node_a,
                    node_b=link.node_b,
                    link_key=b"\x00" * 32,
                    key_id=link.link_id,
                    qber=link.qber,
                    active=link.status == "active",
                )
                if link.node_b not in net._graph[link.node_a]:
                    net._graph[link.node_a].append(link.node_b)
                if link.node_a not in net._graph[link.node_b]:
                    net._graph[link.node_b].append(link.node_a)

        self._network = net
        log.info("QCTekRelayOrchestrator: built network with %d nodes, %d links",
                 len(net._nodes), len(net._links))
        return self

    def relay_key(self, source: str, dest: str) -> dict:
        """
        Relay a session key from source to dest using NMS-provided link keys.

        Uses the NMS for path computation and fetches real link keys for
        each hop instead of using simulated BB84 keys.
        """
        if self._network is None:
            self.build_from_nms()

        # Get optimal path from NMS
        try:
            path = self._client.get_relay_path(source, dest)
        except requests.RequestException:
            # Fall back to local BFS
            path = self._network.find_path(source, dest)

        if not path:
            return {
                "success": False,
                "session_key": None,
                "path": [],
                "message": f"No path from {source} to {dest}",
            }

        # Fetch real link keys for each hop and perform OTP relay
        import secrets
        session_key = secrets.token_bytes(32)
        payload = session_key

        for i in range(len(path) - 1):
            link_key_obj = self._client.get_link_key(path[i], path[i + 1])
            payload = bytes(a ^ b for a, b in zip(payload, link_key_obj.key_bytes))

        # At the destination, the last XOR recovers the session key
        # (In a real deployment, the destination fetches the final link key
        # from the NMS independently)

        return {
            "success": True,
            "session_key": session_key,
            "path": path,
            "hops": len(path) - 1,
            "message": " -> ".join(path),
        }

    @property
    def network(self):
        return self._network


class QCTekNetworkTopologySync:
    """
    Polls the QuantumCTek NMS and refreshes the QKDRelayNetwork topology
    when links go up/down or new nodes are added.
    """

    def __init__(
        self, orchestrator: QCTekRelayOrchestrator, poll_interval: float = 60.0
    ) -> None:
        self._orchestrator = orchestrator
        self._poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._last_sync: float = 0.0

    def start(self) -> None:
        """Start the background topology sync thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        log.info("QCTekNetworkTopologySync: started (interval=%.0fs)",
                 self._poll_interval)

    def stop(self) -> None:
        """Stop the background sync thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._poll_interval + 1)

    def _sync_loop(self) -> None:
        """Continuously refresh topology from the NMS."""
        while self._running:
            try:
                self._orchestrator.build_from_nms()
                self._last_sync = time.time()
                log.info("QCTekNetworkTopologySync: topology refreshed")
            except requests.RequestException as e:
                log.warning("Topology sync failed: %s", e)

            time.sleep(self._poll_interval)

    @property
    def last_sync_time(self) -> float:
        return self._last_sync
