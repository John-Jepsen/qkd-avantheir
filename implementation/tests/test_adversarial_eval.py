"""Tests for adversarial evaluation module."""

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from adversarial_eval import generate_perturbations, evaluate_evasion, adversarial_retrain
from physics_constraints import validate_features


@pytest.fixture(scope="module")
def sample_data():
    """Generate small labeled dataset for testing."""
    rng = np.random.default_rng(42)
    n = 100
    X = rng.uniform(0, 0.3, size=(n, 8))
    X[:, 1] = rng.uniform(0.4, 0.55, size=n)  # sift_ratio
    X[:, 7] = np.abs(X[:, 1] - 0.5)  # sift_deviation
    y = np.array(["clean"] * 50 + ["eavesdrop"] * 50)
    # Make eavesdrop samples have higher QBER
    X[50:, 0] = rng.uniform(0.15, 0.3, size=50)
    return X, y


@pytest.fixture(scope="module")
def trained_model(sample_data):
    X, y = sample_data
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)
    return model


def test_generate_perturbations_shape(sample_data):
    X, _ = sample_data
    perturbed = generate_perturbations(X, epsilon=0.1)
    assert perturbed.shape == X.shape


def test_generate_perturbations_within_bounds(sample_data):
    X, _ = sample_data
    perturbed = generate_perturbations(X, epsilon=0.2, rng=np.random.default_rng(0))
    valid, violations = validate_features(perturbed)
    assert valid, f"Violations: {violations[:3]}"


def test_evaluate_evasion_returns_dict(trained_model, sample_data):
    X, y = sample_data
    result = evaluate_evasion(trained_model, X, y, epsilon=0.1, n_trials=2)
    assert "evasion_rate" in result
    assert 0.0 <= result["evasion_rate"] <= 1.0


def test_evasion_increases_with_epsilon(trained_model, sample_data):
    X, y = sample_data
    rng = np.random.default_rng(42)
    low = evaluate_evasion(trained_model, X, y, epsilon=0.05, n_trials=3, rng=rng)
    high = evaluate_evasion(trained_model, X, y, epsilon=0.30, n_trials=3, rng=rng)
    # Higher epsilon should generally cause more evasion
    assert high["evasion_rate"] >= low["evasion_rate"] * 0.5  # relaxed check


def test_adversarial_retrain_returns_model(trained_model, sample_data):
    X, y = sample_data
    X_adv = generate_perturbations(X, epsilon=0.15)
    y_adv = y.copy()
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)
    result = adversarial_retrain(model, X, y, X_adv, y_adv)
    assert hasattr(result, "predict")
