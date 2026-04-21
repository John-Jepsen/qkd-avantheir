"""
BB84 QKD Protocol Simulator — Qiskit Edition

Implements the complete BB84 key distribution protocol using IBM Qiskit quantum
circuits executed on the Aer statevector simulator.  Each qubit Alice sends is
represented by a real quantum gate sequence (X for bit-flip, H for basis change)
and measured through a simulated quantum backend — no classical coin-flips.

Protocol steps:
  1. Alice prepares qubits in Z or X basis via Qiskit circuits
  2. Qubits traverse a noisy depolarizing channel (Qiskit Aer noise model)
  3. Bob measures in a random basis; basis sifting discards mismatches
  4. QBER estimation on a public sample detects eavesdropping
  5. Error correction — binary reconciliation over block parities
  6. Privacy amplification — BLAKE2b hash to bound Eve's information

Eavesdropper simulation:
  Eve performs an intercept-resend attack modeled as two sequential circuits:
    Circuit 1: Alice prepares → Eve measures in random basis
    Circuit 2: Eve re-prepares from her result → Bob measures
  This faithfully captures the ~25% QBER introduced by wrong-basis measurement.

Security properties:
  - Aborts if estimated QBER exceeds 11% (BB84 security threshold)
  - Privacy amplification uses BLAKE2b as a universal hash

Requirements:
  pip install qiskit qiskit-aer

Usage:
    from bb84_simulator import BB84Protocol

    result = BB84Protocol().run(n_bits=4096)
    if result.secure:
        print(result.final_key.hex())        # 32-byte (256-bit) shared secret

    # With eavesdropper (will abort):
    result = BB84Protocol(eavesdrop=True).run(n_bits=4096)
    print(result.secure)                      # False

    # Fall back to classical simulation (no Qiskit required):
    result = BB84Protocol(backend="classical").run(n_bits=4096)
"""

import hashlib
import secrets
from dataclasses import dataclass

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

# Process qubits in batches to keep circuit size manageable
_BATCH_SIZE = 256


@dataclass
class BB84Result:
    final_key: bytes         # Empty if not secure
    key_length_bits: int
    raw_bits: int            # Qubits sent by Alice
    sifted_bits: int         # Bits remaining after basis matching
    qber: float              # Estimated quantum bit error rate
    eavesdropper_detected: bool
    secure: bool
    backend_used: str = "qiskit"
    sift_ratio: float = 0.0          # sifted_bits / raw_bits
    block_error_rates: list = None    # Per-block error rates for ML features  # noqa
    error_variance: float = 0.0      # Variance of per-block error rates
    max_burst_length: int = 0        # Longest consecutive error run


# ── Qiskit quantum channel ───────────────────────────────────────────────────


class QiskitQuantumChannel:
    """
    Quantum channel backed by IBM Qiskit Aer simulator.

    Each qubit is prepared with real gate operations (X, H) and measured through
    the Aer backend.  Channel noise is modeled as a single-qubit depolarizing
    error applied via an identity gate inserted between preparation and
    measurement.

    Parameters
    ----------
    error_rate : float
        Background QBER from channel noise. Mapped to depolarizing probability
        p = 3·error_rate/2 so that the resulting bit-flip rate matches.
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper using two-circuit model.
    eavesdrop_fraction : float
        Fraction of qubits Eve intercepts (0.0 to 1.0). Only used when
        eavesdrop=True. Default 1.0 (full intercept-resend). Values below
        1.0 simulate partial intercept attacks where Eve only taps a subset
        of qubits, producing distinct statistical signatures (bimodal error
        distribution, clustered bursts) vs uniform channel noise.
    """

    def __init__(self, error_rate: float = 0.01, eavesdrop: bool = False,
                 eavesdrop_fraction: float = 1.0):
        if not 0.0 <= error_rate <= 0.5:
            raise ValueError("error_rate must be between 0.0 and 0.5")
        if not 0.0 <= eavesdrop_fraction <= 1.0:
            raise ValueError("eavesdrop_fraction must be between 0.0 and 1.0")
        self.error_rate = error_rate
        self.eavesdrop = eavesdrop
        self.eavesdrop_fraction = eavesdrop_fraction

        self._ideal_backend = AerSimulator()
        self._noisy_backend = self._build_noisy_backend() if error_rate > 0 else None

    def _build_noisy_backend(self) -> AerSimulator:
        """Create an Aer backend with depolarizing noise on the id gate."""
        noise_model = NoiseModel()
        # Map error_rate to depolarizing probability:
        # Depolarizing channel: P(bit flip) = 2p/3, so p = 3·error_rate/2
        p = min(1.0, 3 * self.error_rate / 2)
        noise_model.add_all_qubit_quantum_error(
            depolarizing_error(p, 1), ["id"]
        )
        return AerSimulator(noise_model=noise_model)

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        """
        Simulate quantum transmission and return (bob_bits, bob_bases).

        Without eavesdropper: single circuit per batch
            Alice prepares → channel noise (id gate) → Bob measures

        With eavesdropper: two circuits per batch (intercept-resend)
            Circuit 1: Alice prepares → Eve measures (ideal, no noise)
            Circuit 2: Eve re-prepares → channel noise → Bob measures
        """
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]

        if self.eavesdrop:
            if self.eavesdrop_fraction >= 1.0:
                # Full intercept-resend: Eve intercepts every qubit
                eve_bases = [secrets.randbelow(2) for _ in range(n)]
                eve_bits = self._run_circuit(
                    alice_bits, alice_bases, eve_bases, noisy=False
                )
                bob_bits = self._run_circuit(
                    eve_bits, eve_bases, bob_bases, noisy=True
                )
            else:
                # Partial intercept: Eve only taps a fraction of qubits.
                # Intercepted qubits go through Eve's measure-resend cycle.
                # Non-intercepted qubits go straight through the noisy channel.
                intercepted = [
                    secrets.randbelow(1000) < int(self.eavesdrop_fraction * 1000)
                    for _ in range(n)
                ]
                eve_bases = [secrets.randbelow(2) for _ in range(n)]

                # Split into intercepted vs clean qubit lists
                eve_bits = self._run_circuit(
                    alice_bits, alice_bases, eve_bases, noisy=False
                )
                clean_bits = self._run_circuit(
                    alice_bits, alice_bases, bob_bases, noisy=True
                )

                # For intercepted qubits, Eve re-prepares and sends to Bob
                eve_resend = self._run_circuit(
                    eve_bits, eve_bases, bob_bases, noisy=True
                )

                # Merge: intercepted qubits use Eve's resend, others use clean
                bob_bits = [
                    eve_resend[i] if intercepted[i] else clean_bits[i]
                    for i in range(n)
                ]
        else:
            bob_bits = self._run_circuit(
                alice_bits, alice_bases, bob_bases, noisy=True
            )

        return bob_bits, bob_bases

    def _run_circuit(
        self,
        sender_bits: list[int],
        sender_bases: list[int],
        receiver_bases: list[int],
        noisy: bool = True,
    ) -> list[int]:
        """Build and execute quantum circuits in batches."""
        n = len(sender_bits)
        all_results: list[int] = []

        for start in range(0, n, _BATCH_SIZE):
            end = min(start + _BATCH_SIZE, n)
            batch_size = end - start

            qc = QuantumCircuit(batch_size, batch_size)

            # ── Sender preparation ──
            for i in range(batch_size):
                idx = start + i
                if sender_bits[idx] == 1:
                    qc.x(i)                    # encode bit value
                if sender_bases[idx] == 1:
                    qc.h(i)                    # switch to X (diagonal) basis

            # ── Channel transmission (id gate carries depolarizing noise) ──
            if noisy and self.error_rate > 0:
                for i in range(batch_size):
                    qc.id(i)

            # ── Receiver measurement in chosen basis ──
            for i in range(batch_size):
                idx = start + i
                if receiver_bases[idx] == 1:
                    qc.h(i)                    # rotate X basis back to Z for measurement
                qc.measure(i, i)

            # ── Execute on Aer ──
            backend = (
                self._noisy_backend
                if (noisy and self._noisy_backend)
                else self._ideal_backend
            )
            job = backend.run(qc, shots=1)
            counts = job.result().get_counts()

            # Qiskit returns bitstrings MSB-first; qubit 0 is the rightmost char
            bitstring = list(counts.keys())[0].zfill(batch_size)
            bits = [int(b) for b in reversed(bitstring)]
            all_results.extend(bits[:batch_size])

        return all_results


# ── Classical fallback channel (no Qiskit dependency) ────────────────────────


class ClassicalQuantumChannel:
    """
    Classical probabilistic simulation of BB84 (original implementation).
    Used as a fallback when Qiskit is unavailable or for fast comparison runs.
    """

    def __init__(self, error_rate: float = 0.01, eavesdrop: bool = False,
                 eavesdrop_fraction: float = 1.0):
        if not 0.0 <= error_rate <= 0.5:
            raise ValueError("error_rate must be between 0.0 and 0.5")
        if not 0.0 <= eavesdrop_fraction <= 1.0:
            raise ValueError("eavesdrop_fraction must be between 0.0 and 1.0")
        self.error_rate = error_rate
        self.eavesdrop = eavesdrop
        self.eavesdrop_fraction = eavesdrop_fraction

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]
        bob_bits = []
        noise_threshold = int(self.error_rate * 1000)
        intercept_threshold = int(self.eavesdrop_fraction * 1000)

        for i in range(n):
            transmitted_bit = alice_bits[i]
            transmitted_basis = alice_bases[i]

            if self.eavesdrop and secrets.randbelow(1000) < intercept_threshold:
                eve_basis = secrets.randbelow(2)
                if eve_basis == alice_bases[i]:
                    eve_bit = alice_bits[i]
                else:
                    eve_bit = secrets.randbelow(2)
                transmitted_bit = eve_bit
                transmitted_basis = eve_basis

            if bob_bases[i] == transmitted_basis:
                bit = transmitted_bit
            else:
                bit = secrets.randbelow(2)

            if secrets.randbelow(1000) < noise_threshold:
                bit ^= 1

            bob_bits.append(bit)

        return bob_bits, bob_bases


# ── BB84 Protocol ────────────────────────────────────────────────────────────


class BB84Protocol:
    """
    Full BB84 QKD protocol.

    Parameters
    ----------
    error_rate : float
        Background channel error rate (without eavesdropping). Default: 0.01 (1%).
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper. Default: False.
    qber_threshold : float
        Maximum tolerable QBER. Protocol aborts above this. Default: 0.11 (11%).
    sample_fraction : float
        Fraction of sifted bits sacrificed for QBER estimation. Default: 0.10 (10%).
    backend : str
        "qiskit" (default) — run on Qiskit Aer simulator with depolarizing noise.
        "classical" — use the original probabilistic simulation (faster, no Qiskit).
    """

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        eavesdrop_fraction: float = 1.0,
        qber_threshold: float = 0.11,
        sample_fraction: float = 0.10,
        backend: str = "qiskit",
    ):
        self.backend_name = backend
        if backend == "qiskit":
            self.channel = QiskitQuantumChannel(
                error_rate=error_rate, eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
            )
        elif backend == "classical":
            self.channel = ClassicalQuantumChannel(
                error_rate=error_rate, eavesdrop=eavesdrop,
                eavesdrop_fraction=eavesdrop_fraction,
            )
        elif backend == "realistic_noise":
            from qiskit_advanced import RealisticNoiseChannel
            self.channel = RealisticNoiseChannel(eavesdrop=eavesdrop)
        elif backend == "ibm_hardware":
            from qiskit_advanced import IBMQuantumChannel
            self.channel = IBMQuantumChannel(eavesdrop=eavesdrop)
        else:
            raise ValueError(
                f"Unknown backend: {backend!r} "
                "(use 'qiskit', 'classical', 'realistic_noise', or 'ibm_hardware')"
            )
        self.qber_threshold = qber_threshold
        self.sample_fraction = sample_fraction

    def run(self, n_bits: int = 4096) -> BB84Result:
        """
        Execute the full BB84 protocol and return a BB84Result.

        n_bits: number of raw qubits Alice prepares and sends.
                After sifting (~50% yield), sampling (~10% loss), error correction,
                and privacy amplification, the output is always a 256-bit key when
                the protocol succeeds.
        """
        # ── Step 1: Alice generates random bits and basis choices ──────────────
        alice_bits = [secrets.randbelow(2) for _ in range(n_bits)]
        alice_bases = [secrets.randbelow(2) for _ in range(n_bits)]

        # ── Step 2: Quantum channel transmission (Qiskit circuits) ───────────
        bob_bits, bob_bases = self.channel.transmit(alice_bits, alice_bases)

        # ── Step 3: Sifting ────────────────────────────────────────────────────
        sifted_alice: list[int] = []
        sifted_bob: list[int] = []
        for i in range(n_bits):
            if alice_bases[i] == bob_bases[i]:
                sifted_alice.append(alice_bits[i])
                sifted_bob.append(bob_bits[i])

        if len(sifted_alice) < 40:
            raise RuntimeError(
                f"Only {len(sifted_alice)} sifted bits — increase n_bits (try 4096+)"
            )

        # ── Step 4: QBER estimation ──────────────────────────────────────────
        sample_size = max(10, int(len(sifted_alice) * self.sample_fraction))
        sample_alice = sifted_alice[:sample_size]
        sample_bob = sifted_bob[:sample_size]
        errors = sum(a != b for a, b in zip(sample_alice, sample_bob))
        qber = errors / sample_size

        # ── ML feature extraction ────────────────────────────────────────────
        sift_ratio = len(sifted_alice) / n_bits
        block_error_rates = self._compute_block_error_rates(
            sample_alice, sample_bob, block_size=8
        )
        error_variance = (
            sum((r - qber) ** 2 for r in block_error_rates) / len(block_error_rates)
            if block_error_rates else 0.0
        )
        max_burst = self._max_error_burst(sample_alice, sample_bob)

        # Remaining bits form the raw key
        key_alice = sifted_alice[sample_size:]
        key_bob = sifted_bob[sample_size:]

        eavesdropper_detected = qber > self.qber_threshold
        if eavesdropper_detected or not key_alice:
            return BB84Result(
                final_key=b"",
                key_length_bits=0,
                raw_bits=n_bits,
                sifted_bits=len(sifted_alice),
                qber=qber,
                eavesdropper_detected=eavesdropper_detected,
                secure=False,
                backend_used=self.backend_name,
                sift_ratio=sift_ratio,
                block_error_rates=block_error_rates,
                error_variance=error_variance,
                max_burst_length=max_burst,
            )

        # ── Step 5: Error correction ─────────────────────────────────────────
        corrected_bob = self._error_correct(key_alice, key_bob)

        # ── Step 6: Privacy amplification ────────────────────────────────────
        final_key = self._privacy_amplify(corrected_bob)

        return BB84Result(
            final_key=final_key,
            key_length_bits=len(final_key) * 8,
            raw_bits=n_bits,
            sifted_bits=len(sifted_alice),
            qber=qber,
            eavesdropper_detected=False,
            secure=True,
            backend_used=self.backend_name,
            sift_ratio=sift_ratio,
            block_error_rates=block_error_rates,
            error_variance=error_variance,
            max_burst_length=max_burst,
        )

    # ── ML feature helpers ───────────────────────────────────────────────────

    @staticmethod
    def _compute_block_error_rates(
        alice: list[int], bob: list[int], block_size: int = 8
    ) -> list[float]:
        """Per-block error rates for ML feature extraction."""
        rates = []
        for start in range(0, len(alice) - block_size + 1, block_size):
            errs = sum(
                a != b for a, b in zip(alice[start:start + block_size],
                                       bob[start:start + block_size])
            )
            rates.append(errs / block_size)
        return rates

    @staticmethod
    def _max_error_burst(alice: list[int], bob: list[int]) -> int:
        """Length of the longest consecutive error run."""
        max_run = 0
        current = 0
        for a, b in zip(alice, bob):
            if a != b:
                current += 1
                max_run = max(max_run, current)
            else:
                current = 0
        return max_run

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _error_correct(
        self, alice_bits: list[int], bob_bits: list[int]
    ) -> list[int]:
        """
        Simplified binary reconciliation.

        Alice announces the parity of each 8-bit block. For each block whose
        parity disagrees, Bob flips the first differing bit he can identify.
        In a full Cascade implementation multiple passes reduce residual errors
        to near zero; this single pass is adequate for error_rate < ~3%.
        """
        corrected = bob_bits[:]
        block_size = 8
        for start in range(0, len(alice_bits) - block_size + 1, block_size):
            a_block = alice_bits[start : start + block_size]
            b_block = corrected[start : start + block_size]
            if sum(a_block) % 2 != sum(b_block) % 2:
                for j in range(block_size):
                    if a_block[j] != b_block[j]:
                        corrected[start + j] ^= 1
                        break
        return corrected

    def _privacy_amplify(self, bits: list[int]) -> bytes:
        """
        Privacy amplification via BLAKE2b universal hashing.

        Converts the bit array to bytes, then hashes to a fixed 256-bit output.
        By the Leftover Hash Lemma, this bounds the amount of information Eve
        can have about the final key regardless of her side-channel knowledge.
        """
        n = len(bits)
        padded = bits + [0] * ((-n) % 8)
        raw_bytes = bytes(
            sum(padded[i + j] << (7 - j) for j in range(8))
            for i in range(0, len(padded), 8)
        )
        return hashlib.blake2b(raw_bytes, digest_size=32).digest()


# ── Standalone demo ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    scenarios = [
        ("Normal channel (1% noise)",       {"error_rate": 0.01, "eavesdrop": False}),
        ("Noisy channel (5% noise)",         {"error_rate": 0.05, "eavesdrop": False}),
        ("Eavesdropper present (~25% QBER)", {"error_rate": 0.01, "eavesdrop": True}),
    ]

    for backend_name in ("qiskit", "classical"):
        print(f"\n{'=' * 60}")
        print(f"BB84 QKD Protocol — {backend_name.upper()} backend")
        print("=" * 60)

        for name, kwargs in scenarios:
            print(f"\nScenario: {name}")
            result = BB84Protocol(**kwargs, backend=backend_name).run(n_bits=4096)
            print(f"  Backend:          {result.backend_used}")
            print(f"  Raw qubits sent:  {result.raw_bits}")
            print(f"  Sifted bits:      {result.sifted_bits}  (~50% of raw)")
            print(f"  Estimated QBER:   {result.qber:.3f}  ({result.qber * 100:.1f}%)")
            if result.secure:
                print(f"  Final key (256b): {result.final_key.hex()}")
            else:
                reason = "eavesdropper detected" if result.eavesdropper_detected else "QBER too high"
                print(f"  ABORT — {reason}")
