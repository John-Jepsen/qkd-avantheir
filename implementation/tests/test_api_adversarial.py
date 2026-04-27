"""Tests for adversarial API endpoints."""

import pytest
from fastapi.testclient import TestClient
from api import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_evolution_status_idle(client):
    res = client.get("/evolution/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("idle", "evolving", "complete", "training")


def test_attack_tree_404_before_run(client):
    # Reset state
    import api
    api.evolution_state = {"status": "idle", "result": None, "generations": []}
    res = client.get("/attack-tree")
    assert res.status_code == 404


def test_adversarial_eval_endpoint(client):
    res = client.post("/adversarial-eval", json={"epsilon": 0.15, "n_trials": 2})
    assert res.status_code == 200
    data = res.json()
    assert "before" in data
    assert "after" in data
    assert "improvement" in data
    assert "hardening_effective" in data
    assert 0.0 <= data["before"]["evasion_rate"] <= 1.0
    assert 0.0 <= data["after"]["evasion_rate"] <= 1.0


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "models_loaded" in data
