"""
pytest configuration and shared fixtures.

sys.path is extended so that all implementation modules (bb84_simulator,
kme_server, kme_dual, etc.) can be imported without installation.
"""

import os
import sys

# Add the implementation/ directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


@pytest.fixture(scope="module")
def kme_client():
    """
    Flask test client for kme_server (single-KME, port 5000 style).

    Module-scoped so the key pool is initialized once per test module,
    avoiding the ~3 second BB84 pool fill on every test function.
    """
    from kme_server import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="module")
def dual_kme_client():
    """
    Flask test client for kme_dual (dual-KME, peer sync disabled in tests).

    Peer sync is suppressed by setting pool._peer_url = None after import,
    so tests don't require a second KME to be running.
    """
    from kme_dual import app, pool
    app.config["TESTING"] = True
    original_peer_url = pool._peer_url
    pool._peer_url = None          # disable outbound sync during tests
    with app.test_client() as client:
        yield client
    pool._peer_url = original_peer_url
