"""
Tests for BB84 protocol simulator.

Covers the three core scenarios: clean channel, eavesdropper detection,
and high-noise channel. Also validates result field correctness.
"""

import pytest
from bb84_simulator import BB84Protocol, BB84Result


def test_normal_channel_produces_key():
    result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
    assert result.secure is True
    assert result.eavesdropper_detected is False
    assert len(result.final_key) == 32          # 256 bits
    assert result.key_length_bits == 256
    assert result.qber < 0.11


def test_normal_channel_key_is_bytes():
    result = BB84Protocol().run(n_bits=4096)
    assert isinstance(result.final_key, bytes)


def test_two_runs_produce_different_keys():
    proto = BB84Protocol(error_rate=0.01)
    r1 = proto.run(n_bits=4096)
    r2 = proto.run(n_bits=4096)
    assert r1.secure and r2.secure
    assert r1.final_key != r2.final_key   # random keys must differ


def test_eavesdropper_detected_and_aborts():
    result = BB84Protocol(eavesdrop=True).run(n_bits=4096)
    assert result.secure is False
    assert result.eavesdropper_detected is True
    assert result.final_key == b""
    assert result.key_length_bits == 0


def test_eavesdropper_raises_qber():
    result = BB84Protocol(eavesdrop=True).run(n_bits=4096)
    # Intercept-resend adds ~25% QBER; always above the 11% threshold
    assert result.qber > 0.11


def test_high_noise_aborts():
    # 30% error rate is far above the 11% QBER threshold — always aborts.
    # (12% error rate is too close to the threshold; QBER estimation sampling
    # can produce an estimate just below 11% due to statistical variance.)
    result = BB84Protocol(error_rate=0.30).run(n_bits=8192)
    assert result.secure is False


def test_result_raw_bits_match_input():
    n = 4096
    result = BB84Protocol().run(n_bits=n)
    assert result.raw_bits == n


def test_sifted_bits_roughly_half_of_raw():
    result = BB84Protocol().run(n_bits=4096)
    # Basis agreement probability is ~50%; allow 35–65% range
    ratio = result.sifted_bits / result.raw_bits
    assert 0.35 <= ratio <= 0.65


def test_custom_qber_threshold():
    # With threshold=0.20, even a 12% noisy channel should succeed
    result = BB84Protocol(error_rate=0.12, qber_threshold=0.20).run(n_bits=8192)
    assert result.secure is True


def test_invalid_error_rate_raises():
    with pytest.raises(ValueError):
        BB84Protocol(error_rate=0.9)   # > 0.5 is invalid
