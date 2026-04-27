"""Tests for shared feature extraction module."""

import numpy as np
from bb84_simulator import BB84Protocol
from features import extract_features, FEATURE_NAMES


def test_feature_names_count():
    assert len(FEATURE_NAMES) == 8


def test_extract_returns_list_of_8():
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    feats = extract_features(r)
    assert isinstance(feats, list)
    assert len(feats) == 8


def test_all_features_are_float():
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    feats = extract_features(r)
    for f in feats:
        assert isinstance(f, (int, float))


def test_qber_in_valid_range():
    r = BB84Protocol(error_rate=0.02, backend="classical").run(n_bits=1024)
    feats = extract_features(r)
    assert 0.0 <= feats[0] <= 0.5


def test_sift_ratio_near_half():
    r = BB84Protocol(error_rate=0.01, backend="classical").run(n_bits=4096)
    feats = extract_features(r)
    assert 0.35 <= feats[1] <= 0.65


def test_eavesdrop_changes_features():
    clean = BB84Protocol(error_rate=0.01, backend="classical").run(n_bits=2048)
    eaved = BB84Protocol(error_rate=0.01, eavesdrop=True, backend="classical").run(n_bits=2048)
    f_clean = extract_features(clean)
    f_eaved = extract_features(eaved)
    # Eavesdrop should increase QBER
    assert f_eaved[0] > f_clean[0]
