"""
Trusted-Node QKD Relay Network

Simulates a multi-hop QKD network using the trusted-node relay pattern.
This is the architecture used in the Beijing-Shanghai backbone, Tokyo QKD
network, and the EuroQCI (European Quantum Communication Infrastructure).

Architecture:

  Each pair of adjacent nodes shares a BB84-generated link key.
  To relay a session key from source to destination through one or more
  trusted intermediate nodes, each hop XOR-encrypts the payload with its
  outgoing link key after decrypting it with the incoming link key.
  This is equivalent to re-encryption with a one-time pad at each hop.

Security model:
  - End-to-end security requires trusting ALL intermediate nodes.
    Each relay node necessarily learns the session key in cleartext.
  - Each link key is used ONCE per relay operation (OTP semantics).
  - QBER from the BB84 session is recorded per link for monitoring.
  - If any link's BB84 run exceeded the QBER threshold, that link is
    marked inactive and relay through it will be refused.

See: 04-service-mesh-auth/04-service-mesh-auth.md §3 (trusted relay)

Usage:
  from relay_network import QKDRelayNetwork

  net = QKDRelayNetwork()
  for node in ["NYC", "Chicago", "Denver", "LA"]:
      net.add_node(node)
  net.connect("NYC", "Chicago")
  net.connect("Chicago", "Denver")
  net.connect("Denver", "LA")

  session_key = net.relay_key("NYC", "LA")
  print(session_key.hex())   # 32-byte shared secret at destination

  net.print_topology()
"""

import secrets
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from bb84_simulator import BB84Protocol


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class QKDLink:
    """
    A quantum link between two adjacent nodes backed by a BB84 session.

    link_key is a 32-byte symmetric key shared between node_a and node_b.
    It is generated once at connect() time and consumed by relay operations.
    """
    node_a:   str
    node_b:   str
    link_key: bytes
    key_id:   str
    qber:     float
    active:   bool   # False if BB84 aborted (QBER exceeded threshold)

    def __str__(self) -> str:
        status = "active" if self.active else "ABORTED (QBER exceeded)"
        return f"QKDLink({self.node_a} ↔ {self.node_b}, QBER={self.qber:.3f}, {status})"


@dataclass
class RelayResult:
    success:     bool
    session_key: Optional[bytes]   # Non-None on success
    path:        list[str]
    hops:        int
    message:     str


# ── Network ────────────────────────────────────────────────────────────────────

class QKDRelayNetwork:
    """
    A graph of QKD-connected trusted nodes.

    Each edge in the graph corresponds to a QKDLink with a BB84-generated
    key. relay_key() routes a fresh session key from source to destination
    using the OTP-relay pattern.
    """

    def __init__(self, error_rate: float = 0.01) -> None:
        self._nodes: set[str] = set()
        self._links: dict[tuple[str, str], QKDLink] = {}   # canonical (a,b) → link
        self._graph: dict[str, list[str]] = {}              # adjacency list
        self._proto = BB84Protocol(error_rate=error_rate)

    # ── Graph construction ─────────────────────────────────────────────────────

    def add_node(self, node_id: str) -> None:
        """Register a node. Must be called before connect()."""
        self._nodes.add(node_id)
        if node_id not in self._graph:
            self._graph[node_id] = []

    def connect(self, node_a: str, node_b: str) -> QKDLink:
        """
        Establish a QKD link between node_a and node_b by running BB84.

        If BB84 aborts (QBER > threshold), the link is created but marked
        inactive. Relay operations will refuse to use it.
        """
        for n in (node_a, node_b):
            if n not in self._nodes:
                raise ValueError(f"Unknown node '{n}'. Call add_node() first.")

        result = self._proto.run(n_bits=4096)
        link = QKDLink(
            node_a=node_a,
            node_b=node_b,
            link_key=result.final_key if result.secure else b"\x00" * 32,
            key_id=str(uuid.uuid4()),
            qber=result.qber,
            active=result.secure,
        )

        canonical = _canon(node_a, node_b)
        self._links[canonical] = link
        if node_b not in self._graph[node_a]:
            self._graph[node_a].append(node_b)
        if node_a not in self._graph[node_b]:
            self._graph[node_b].append(node_a)

        return link

    # ── Routing ────────────────────────────────────────────────────────────────

    def find_path(self, source: str, dest: str) -> Optional[list[str]]:
        """
        BFS shortest path from source to dest through active links only.
        Returns None if no path exists or if source == dest.
        """
        if source == dest:
            return None
        if source not in self._nodes or dest not in self._nodes:
            return None

        visited = {source}
        queue: deque[list[str]] = deque([[source]])

        while queue:
            path = queue.popleft()
            current = path[-1]
            if current == dest:
                return path
            for neighbor in self._graph.get(current, []):
                if neighbor not in visited:
                    link = self._links.get(_canon(current, neighbor))
                    if link and link.active:
                        visited.add(neighbor)
                        queue.append(path + [neighbor])

        return None

    def relay_key(self, source: str, dest: str) -> RelayResult:
        """
        Relay a fresh 256-bit session key from source to dest.

        OTP relay algorithm (for path [N0, N1, N2, ..., Nk]):

          1. Source (N0) generates session_key (32 random bytes).
          2. Source XOR-encrypts with link_key(N0, N1):
               payload = session_key XOR link_key(N0, N1)
          3. Each intermediate node Ni (1 ≤ i ≤ k-1):
               decoded  = payload XOR link_key(N(i-1), Ni)   # decrypt incoming
               payload  = decoded  XOR link_key(Ni, N(i+1))  # re-encrypt outgoing
             At each step decoded == session_key (XORs cancel), so each
             trusted node transiently holds session_key in plaintext.
          4. Destination (Nk) decodes:
               recovered = payload XOR link_key(N(k-1), Nk)
             recovered == session_key.

        Returns RelayResult with session_key on success, None on failure.
        """
        path = self.find_path(source, dest)

        if path is None:
            return RelayResult(
                success=False,
                session_key=None,
                path=[],
                hops=0,
                message=f"No active path from '{source}' to '{dest}'",
            )

        # Verify all links are available (find_path already filters, but double-check)
        for i in range(len(path) - 1):
            link = self._links.get(_canon(path[i], path[i + 1]))
            if link is None or not link.active:
                return RelayResult(
                    success=False, session_key=None, path=path, hops=i,
                    message=f"Link {path[i]} ↔ {path[i+1]} is inactive",
                )

        # Step 1: source generates session key
        session_key = secrets.token_bytes(32)

        # Step 2: source XOR-encrypts with first link key
        payload = _xor(session_key, self._get_link_key(path[0], path[1]))

        # Step 3: each intermediate trusted node decodes and re-encodes
        for i in range(1, len(path) - 1):
            decoded = _xor(payload, self._get_link_key(path[i - 1], path[i]))
            payload = _xor(decoded, self._get_link_key(path[i], path[i + 1]))

        # Step 4: destination decodes final hop
        recovered = _xor(payload, self._get_link_key(path[-2], path[-1]))

        if recovered != session_key:
            return RelayResult(
                success=False, session_key=None, path=path,
                hops=len(path) - 1,
                message="Relay integrity check failed — XOR mismatch",
            )

        return RelayResult(
            success=True,
            session_key=session_key,
            path=path,
            hops=len(path) - 1,
            message=" → ".join(path),
        )

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _get_link_key(self, a: str, b: str) -> bytes:
        return self._links[_canon(a, b)].link_key

    def print_topology(self) -> None:
        """Print the network topology with QBER and link status."""
        print()
        print("QKD Network Topology")
        print("=" * 52)
        seen: set[tuple[str, str]] = set()
        for node_id in sorted(self._nodes):
            for neighbor in self._graph.get(node_id, []):
                key = _canon(node_id, neighbor)
                if key not in seen:
                    seen.add(key)
                    link = self._links[key]
                    status = "OK" if link.active else "ABORTED"
                    print(
                        f"  {node_id:<15} ──── {neighbor:<15}"
                        f"  QBER={link.qber:.3f}  [{status}]"
                    )
        print()


# ── Utilities ──────────────────────────────────────────────────────────────────

def _canon(a: str, b: str) -> tuple[str, str]:
    """Canonical (sorted) edge key so (A,B) and (B,A) map to the same link."""
    return (a, b) if a < b else (b, a)


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Trusted-Node QKD Relay Network Demo")
    print("=" * 52)

    # Build a 4-node chain: NYC → Chicago → Denver → LA
    net = QKDRelayNetwork(error_rate=0.01)
    nodes = ["NYC", "Chicago", "Denver", "LA"]
    for n in nodes:
        net.add_node(n)

    print("\nEstablishing QKD links...")
    links = [
        net.connect("NYC", "Chicago"),
        net.connect("Chicago", "Denver"),
        net.connect("Denver", "LA"),
    ]
    for link in links:
        print(f"  {link}")

    net.print_topology()

    print("Relaying session key: NYC → LA (3 hops via Chicago, Denver)")
    result = net.relay_key("NYC", "LA")

    if result.success:
        print(f"  Path:        {result.message}")
        print(f"  Hops:        {result.hops}")
        print(f"  Session key: {result.session_key.hex()}")
    else:
        print(f"  FAILED: {result.message}")

    # Also demo a 2-hop relay
    print()
    print("Relaying session key: NYC → Denver (2 hops)")
    result2 = net.relay_key("NYC", "Denver")
    if result2.success:
        print(f"  Path:        {result2.message}")
        print(f"  Session key: {result2.session_key.hex()}")
    else:
        print(f"  FAILED: {result2.message}")
