"""
Tests for the trusted-node QKD relay network.

Covers: node/link construction, BFS path finding, 2-hop and 3-hop relay,
OTP integrity, and failure cases.
"""

import pytest
from relay_network import QKDRelayNetwork


@pytest.fixture
def linear_3():
    """3-node chain: A — B — C"""
    net = QKDRelayNetwork(error_rate=0.01)
    for n in ["A", "B", "C"]:
        net.add_node(n)
    net.connect("A", "B")
    net.connect("B", "C")
    return net


@pytest.fixture
def linear_4():
    """4-node chain: A — B — C — D"""
    net = QKDRelayNetwork(error_rate=0.01)
    for n in ["A", "B", "C", "D"]:
        net.add_node(n)
    net.connect("A", "B")
    net.connect("B", "C")
    net.connect("C", "D")
    return net


# ── Graph construction ─────────────────────────────────────────────────────────

def test_add_node():
    net = QKDRelayNetwork()
    net.add_node("X")
    assert "X" in net._nodes


def test_connect_unknown_node_raises():
    net = QKDRelayNetwork()
    net.add_node("A")
    with pytest.raises(ValueError):
        net.connect("A", "Z")   # Z not registered


def test_link_is_active_on_clean_channel(linear_3):
    from relay_network import _canon
    link = linear_3._links[_canon("A", "B")]
    assert link.active is True
    assert len(link.link_key) == 32
    assert link.qber < 0.11


# ── Path finding ───────────────────────────────────────────────────────────────

def test_find_path_direct(linear_3):
    path = linear_3.find_path("A", "C")
    assert path == ["A", "B", "C"]


def test_find_path_same_node_returns_none(linear_3):
    assert linear_3.find_path("A", "A") is None


def test_find_path_no_connection():
    net = QKDRelayNetwork()
    net.add_node("X")
    net.add_node("Y")
    # No connect() call — no path
    assert net.find_path("X", "Y") is None


def test_find_path_4_nodes(linear_4):
    path = linear_4.find_path("A", "D")
    assert path == ["A", "B", "C", "D"]


# ── Relay correctness ──────────────────────────────────────────────────────────

def test_two_hop_relay_succeeds(linear_3):
    result = linear_3.relay_key("A", "C")
    assert result.success is True
    assert result.session_key is not None
    assert len(result.session_key) == 32
    assert result.hops == 2


def test_three_hop_relay_succeeds(linear_4):
    result = linear_4.relay_key("A", "D")
    assert result.success is True
    assert len(result.session_key) == 32
    assert result.hops == 3


def test_relay_returns_different_keys_each_call(linear_4):
    r1 = linear_4.relay_key("A", "D")
    r2 = linear_4.relay_key("A", "D")
    assert r1.success and r2.success
    assert r1.session_key != r2.session_key   # fresh session key each time


def test_relay_path_in_result(linear_4):
    result = linear_4.relay_key("A", "D")
    assert result.path == ["A", "B", "C", "D"]


def test_relay_no_path_fails():
    net = QKDRelayNetwork()
    net.add_node("X")
    net.add_node("Y")
    result = net.relay_key("X", "Y")
    assert result.success is False
    assert result.session_key is None


def test_relay_partial_network():
    """A can reach B but not C (no B-C link)."""
    net = QKDRelayNetwork(error_rate=0.01)
    for n in ["A", "B", "C"]:
        net.add_node(n)
    net.connect("A", "B")
    # No A-C or B-C link
    result = net.relay_key("A", "C")
    assert result.success is False


# ── OTP relay integrity ────────────────────────────────────────────────────────

def test_otp_xor_symmetry():
    """Verify that XOR relay recovers the original session key mathematically."""
    from relay_network import _xor
    key  = b"\xde\xad\xbe\xef" * 8
    lk1  = b"\x01" * 32
    lk2  = b"\x02" * 32
    lk3  = b"\x03" * 32

    # Simulate 3-hop relay manually
    step1   = _xor(key, lk1)            # source encodes
    decoded = _xor(step1, lk1)          # relay 1 decodes
    step2   = _xor(decoded, lk2)        # relay 1 re-encodes
    decoded = _xor(step2, lk2)          # relay 2 decodes
    step3   = _xor(decoded, lk3)        # relay 2 re-encodes
    recovered = _xor(step3, lk3)        # dest decodes

    assert recovered == key
