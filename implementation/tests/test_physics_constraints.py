"""Tests for physics constraints module."""

import numpy as np
from physics_constraints import (
    validate_features, enforce_covariance, clip_to_bounds,
    random_within_bounds, FEATURE_BOUNDS, BOUNDS_LOW, BOUNDS_HIGH,
)


def test_bounds_arrays_match_dict():
    assert len(BOUNDS_LOW) == 8
    assert len(BOUNDS_HIGH) == 8


def test_clip_to_bounds_clips_high():
    bad = np.array([1.0, 1.0, 1.0, 100.0, 2.0, 2.0, 5.0, 1.0])
    clipped = clip_to_bounds(bad)
    assert all(clipped <= BOUNDS_HIGH)


def test_clip_to_bounds_clips_low():
    bad = np.array([-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -5.0, -1.0])
    clipped = clip_to_bounds(bad)
    assert all(clipped >= BOUNDS_LOW)


def test_validate_rejects_impossible_qber():
    feats = np.array([0.6, 0.5, 0.01, 1.0, 0.5, 0.0, 0.0, 0.0])
    valid, violations = validate_features(feats)
    assert not valid
    assert any("qber" in v for v in violations)


def test_validate_rejects_block_fractions_over_1():
    feats = np.array([0.05, 0.5, 0.01, 1.0, 0.8, 0.8, 0.0, 0.0])
    valid, violations = validate_features(feats)
    assert not valid


def test_enforce_covariance_fixes_sift_deviation():
    feats = np.array([0.05, 0.45, 0.01, 1.0, 0.5, 0.0, 0.0, 0.99])
    fixed = enforce_covariance(feats)
    expected_dev = abs(fixed[1] - 0.5)
    assert abs(fixed[7] - expected_dev) < 0.001


def test_enforce_covariance_fixes_block_fraction_sum():
    feats = np.array([0.05, 0.5, 0.01, 1.0, 0.7, 0.7, 0.0, 0.0])
    fixed = enforce_covariance(feats)
    assert fixed[4] + fixed[5] <= 1.01


def test_random_within_bounds_valid():
    samples = random_within_bounds(10, rng=np.random.default_rng(42))
    assert samples.shape == (10, 8)
    valid, violations = validate_features(samples)
    assert valid, f"Violations: {violations}"


def test_enforce_covariance_caps_variance():
    feats = np.array([0.05, 0.5, 0.5, 1.0, 0.5, 0.0, 0.0, 0.0])
    fixed = enforce_covariance(feats)
    max_var = fixed[0] * (1 - fixed[0])
    assert fixed[2] <= max_var + 0.001
