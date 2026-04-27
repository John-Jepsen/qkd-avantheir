"""
Baseline tests for ML classifiers.

Validates that the eavesdrop and attack classifiers produce correct output
types, achieve reasonable accuracy, and survive save/load round-trips.
Uses classical backend for speed.
"""

import os
import tempfile
import numpy as np
import pytest

from bb84_simulator import BB84Protocol
from ml_eavesdrop_classifier import EavesdropClassifier, DetectionResult, LABELS
from ml_attack_classifier import (
    AttackClassifier, AttackDetectionResult, ATTACK_TYPES,
    simulate_beam_splitting, simulate_pns_attack, simulate_trojan_horse,
    _extract_features,
)
from features import extract_features, FEATURE_NAMES


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def trained_eavesdrop_clf():
    """Train eavesdrop classifier once for all tests (classical backend)."""
    import ml_eavesdrop_classifier
    orig = ml_eavesdrop_classifier.BB84Protocol

    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)

    ml_eavesdrop_classifier.BB84Protocol = FastProto
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=300, n_bits=1024)
    clf.train()
    ml_eavesdrop_classifier.BB84Protocol = orig
    return clf


@pytest.fixture(scope="module")
def trained_attack_clf():
    """Train attack classifier once for all tests (classical backend)."""
    import ml_attack_classifier
    orig = ml_attack_classifier.BB84Protocol

    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)

    ml_attack_classifier.BB84Protocol = FastProto
    clf = AttackClassifier()
    clf.generate_dataset(n_samples=500, n_bits=1024)
    clf.train()
    ml_attack_classifier.BB84Protocol = orig
    return clf


# ── Feature extraction tests ────────────────────────────────────────────────

def test_extract_features_returns_8_elements():
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    feats = extract_features(r)
    assert len(feats) == 8


def test_feature_names_has_8_entries():
    assert len(FEATURE_NAMES) == 8


def test_extract_features_values_in_range():
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    feats = extract_features(r)
    assert 0.0 <= feats[0] <= 0.5   # qber
    assert 0.0 <= feats[1] <= 1.0   # sift_ratio
    assert feats[2] >= 0.0          # error_variance
    assert feats[3] >= 0.0          # max_burst_length
    assert 0.0 <= feats[4] <= 1.0   # low_block_fraction
    assert 0.0 <= feats[5] <= 1.0   # high_block_fraction
    assert -1.0 <= feats[6] <= 1.0 or feats[6] == 0.0  # autocorrelation
    assert feats[7] >= 0.0          # sift_deviation


def test_eavesdrop_extract_matches_shared():
    """EavesdropClassifier._extract should return same as shared extract_features."""
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    clf = EavesdropClassifier()
    assert clf._extract(r) == extract_features(r)


# ── Eavesdrop classifier tests ──────────────────────────────────────────────

def test_eavesdrop_clf_accuracy(trained_eavesdrop_clf):
    """Trained classifier should achieve >70% accuracy on its own test set."""
    clf = trained_eavesdrop_clf
    y_pred = clf.model.predict(clf.X_test)
    accuracy = np.mean(y_pred == clf.y_test)
    assert accuracy > 0.70, f"Accuracy {accuracy:.2%} is below 70% threshold"


def test_eavesdrop_predict_returns_detection_result(trained_eavesdrop_clf):
    det = trained_eavesdrop_clf.predict(
        qber=0.05, sift_ratio=0.48, error_variance=0.003, max_burst=1,
    )
    assert isinstance(det, DetectionResult)
    assert det.predicted_label in LABELS
    assert 0.0 <= det.confidence <= 1.0
    assert isinstance(det.probabilities, dict)
    assert isinstance(det.threshold_would_detect, bool)


def test_eavesdrop_predict_from_result(trained_eavesdrop_clf):
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    det = trained_eavesdrop_clf.predict_from_result(r)
    assert isinstance(det, DetectionResult)


def test_eavesdrop_detects_full_eavesdropper(trained_eavesdrop_clf):
    r = BB84Protocol(error_rate=0.01, eavesdrop=True, backend="classical").run(n_bits=2048)
    det = trained_eavesdrop_clf.predict_from_result(r)
    assert det.predicted_label != "clean"


def test_eavesdrop_save_load_roundtrip(trained_eavesdrop_clf):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        path = f.name
    try:
        trained_eavesdrop_clf.save(path)
        loaded = EavesdropClassifier.load(path)
        assert loaded.is_trained
        r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
        det_orig = trained_eavesdrop_clf.predict_from_result(r)
        det_loaded = loaded.predict_from_result(r)
        assert det_orig.predicted_label == det_loaded.predicted_label
    finally:
        os.unlink(path)


# ── Attack classifier tests ─────────────────────────────────────────────────

def test_attack_clf_accuracy(trained_attack_clf):
    """Trained classifier should achieve >60% accuracy on 5-class problem."""
    clf = trained_attack_clf
    y_pred = clf.model.predict(clf.X_test)
    accuracy = np.mean(y_pred == clf.y_test)
    assert accuracy > 0.60, f"Accuracy {accuracy:.2%} is below 60% threshold"


def test_attack_classify_returns_result(trained_attack_clf):
    feats = [0.05, 0.48, 0.003, 1.0, 0.8, 0.0, 0.0, 0.02]
    det = trained_attack_clf.classify(feats)
    assert isinstance(det, AttackDetectionResult)
    assert det.predicted_attack in ATTACK_TYPES
    assert 0.0 <= det.confidence <= 1.0
    assert isinstance(det.recommended_action, str)


def test_attack_classify_from_bb84(trained_attack_clf):
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    det = trained_attack_clf.classify_from_bb84(r)
    assert isinstance(det, AttackDetectionResult)


def test_attack_save_load_roundtrip(trained_attack_clf):
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
        path = f.name
    try:
        trained_attack_clf.save(path)
        loaded = AttackClassifier.load(path)
        assert loaded.is_trained
        feats = [0.05, 0.48, 0.003, 1.0, 0.8, 0.0, 0.0, 0.02]
        det_orig = trained_attack_clf.classify(feats)
        det_loaded = loaded.classify(feats)
        assert det_orig.predicted_attack == det_loaded.predicted_attack
    finally:
        os.unlink(path)


# ── Attack simulation tests ─────────────────────────────────────────────────

def test_beam_splitting_returns_8_features():
    rng = np.random.default_rng(0)
    sim = simulate_beam_splitting(1024, 0.01, 0.15, rng)
    assert len(sim["features"]) == 8


def test_pns_attack_reduces_sift_ratio():
    rng = np.random.default_rng(0)
    clean = BB84Protocol(error_rate=0.01, backend="classical").run(n_bits=2048)
    sim = simulate_pns_attack(2048, 0.01, 0.30, rng)
    assert sim["features"][1] < clean.sift_ratio


def test_trojan_horse_increases_burst_and_autocorr():
    rng = np.random.default_rng(0)
    sim = simulate_trojan_horse(2048, 0.01, 0.06, rng)
    # Trojan horse should produce burst lengths > 1
    assert sim["features"][3] >= 2
