"""
Tests for qiskit_advanced.py — RealisticNoiseChannel and QiskitCascadeCorrector.

IBMQuantumChannel tests use mocks (no API token required).
RealisticNoiseChannel tests use the Aer fallback if qiskit-ibm-runtime is
not installed.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestRealisticNoiseChannel:
    def test_transmit_returns_correct_length(self):
        from qiskit_advanced import RealisticNoiseChannel

        channel = RealisticNoiseChannel(eavesdrop=False)
        alice_bits = [0, 1, 0, 1, 1, 0, 1, 0]
        alice_bases = [0, 1, 1, 0, 0, 1, 0, 1]
        bob_bits, bob_bases = channel.transmit(alice_bits, alice_bases)
        assert len(bob_bits) == len(alice_bits)
        assert len(bob_bases) == len(alice_bases)

    def test_transmit_values_are_binary(self):
        from qiskit_advanced import RealisticNoiseChannel

        channel = RealisticNoiseChannel(eavesdrop=False)
        alice_bits = [0, 1, 0, 1] * 10
        alice_bases = [0, 1, 1, 0] * 10
        bob_bits, bob_bases = channel.transmit(alice_bits, alice_bases)
        assert all(b in (0, 1) for b in bob_bits)
        assert all(b in (0, 1) for b in bob_bases)

    def test_eavesdrop_mode_produces_results(self):
        from qiskit_advanced import RealisticNoiseChannel

        channel = RealisticNoiseChannel(eavesdrop=True)
        alice_bits = [0, 1, 0, 1, 1, 0, 1, 0]
        alice_bases = [0, 1, 1, 0, 0, 1, 0, 1]
        bob_bits, bob_bases = channel.transmit(alice_bits, alice_bases)
        assert len(bob_bits) == 8

    def test_works_with_bb84_protocol(self):
        from bb84_simulator import BB84Protocol

        result = BB84Protocol(backend="realistic_noise").run(n_bits=4096)
        assert result.backend_used == "realistic_noise"
        assert result.raw_bits == 4096
        assert result.sifted_bits > 0


class TestQiskitCascadeCorrector:
    def test_no_errors_unchanged(self):
        from qiskit_advanced import QiskitCascadeCorrector

        corrector = QiskitCascadeCorrector(n_passes=4)
        alice = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1]
        bob = alice[:]
        result = corrector.correct(alice, bob)
        assert result == alice

    def test_single_error_corrected(self):
        from qiskit_advanced import QiskitCascadeCorrector

        corrector = QiskitCascadeCorrector(n_passes=4)
        alice = [0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1]
        bob = alice[:]
        bob[3] ^= 1  # introduce one error
        result = corrector.correct(alice, bob)
        assert result == alice

    def test_multiple_errors_reduced(self):
        from qiskit_advanced import QiskitCascadeCorrector

        corrector = QiskitCascadeCorrector(n_passes=4, initial_block_size=4)
        alice = [0, 1, 0, 1, 1, 0, 1, 0] * 4  # 32 bits
        bob = alice[:]
        bob[2] ^= 1
        bob[10] ^= 1
        result = corrector.correct(alice, bob)
        errors_before = sum(a != b for a, b in zip(alice, bob))
        errors_after = sum(a != r for a, r in zip(alice, result))
        assert errors_after < errors_before


class TestIBMQuantumChannel:
    def test_import_error_without_runtime(self):
        """IBMQuantumChannel raises ImportError if qiskit-ibm-runtime missing."""
        with patch.dict("sys.modules", {"qiskit_ibm_runtime": None}):
            from qiskit_advanced import IBMQuantumChannel
            with pytest.raises((ImportError, ConnectionError)):
                IBMQuantumChannel()
