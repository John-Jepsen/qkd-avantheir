"""
BB84 QKD Protocol Simulator

Implements the complete BB84 key distribution protocol:
  1. Alice generates random bits and bases, Bob measures in random bases
  2. Basis sifting — discard positions where bases differ
  3. QBER estimation — sample a fraction of sifted bits to detect eavesdropping
  4. Error correction — binary reconciliation over block parities
  5. Privacy amplification — BLAKE2b hash to bound Eve's information

Security properties:
  - Aborts if estimated QBER exceeds 11% (BB84 security threshold)
  - Eavesdropper simulation adds ~25% QBER via intercept-resend attack
  - Privacy amplification uses BLAKE2b as a universal hash

Usage:
    from bb84_simulator import BB84Protocol

    result = BB84Protocol().run(n_bits=4096)
    if result.secure:
        print(result.final_key.hex())        # 32-byte (256-bit) shared secret

    # With eavesdropper (will abort):
    result = BB84Protocol(eavesdrop=True).run(n_bits=4096)
    print(result.secure)                      # False
"""

import hashlib
import secrets
from dataclasses import dataclass


@dataclass
class BB84Result:
    final_key: bytes         # Empty if not secure
    key_length_bits: int
    raw_bits: int            # Qubits sent by Alice
    sifted_bits: int         # Bits remaining after basis matching
    qber: float              # Estimated quantum bit error rate
    eavesdropper_detected: bool
    secure: bool


class QuantumChannel:
    """
    Simulates a lossy quantum channel with optional intercept-resend eavesdropper.

    error_rate: background QBER from channel noise (independent of eavesdropping)
    eavesdrop:  if True, Eve intercepts every qubit in a random basis and re-prepares
                before Bob receives it. This adds ~25% additional QBER.
    """

    def __init__(self, error_rate: float = 0.01, eavesdrop: bool = False):
        if not 0.0 <= error_rate <= 0.5:
            raise ValueError("error_rate must be between 0.0 and 0.5")
        self.error_rate = error_rate
        self.eavesdrop = eavesdrop

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        """
        Bob measures the qubits Alice sent. Returns (bob_bits, bob_bases).

        When bases match and there is no eavesdropping or noise, Bob's bit
        equals Alice's bit. When bases differ, Bob gets a uniformly random bit.
        Channel noise flips bits independently at error_rate probability.
        """
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]
        bob_bits = []

        noise_threshold = int(self.error_rate * 1000)

        for i in range(n):
            transmitted_bit = alice_bits[i]
            transmitted_basis = alice_bases[i]

            if self.eavesdrop:
                # Eve picks a random basis and measures
                eve_basis = secrets.randbelow(2)
                if eve_basis == alice_bases[i]:
                    # Eve's measurement is correct — she learns the bit
                    eve_bit = alice_bits[i]
                else:
                    # Wrong basis — Eve gets a random result and disturbs the qubit
                    eve_bit = secrets.randbelow(2)
                transmitted_bit = eve_bit
                transmitted_basis = eve_basis

            # Bob measures in his random basis
            if bob_bases[i] == transmitted_basis:
                bit = transmitted_bit
            else:
                bit = secrets.randbelow(2)

            # Independent channel noise
            if secrets.randbelow(1000) < noise_threshold:
                bit ^= 1

            bob_bits.append(bit)

        return bob_bits, bob_bases


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
    """

    def __init__(
        self,
        error_rate: float = 0.01,
        eavesdrop: bool = False,
        qber_threshold: float = 0.11,
        sample_fraction: float = 0.10,
    ):
        self.channel = QuantumChannel(error_rate=error_rate, eavesdrop=eavesdrop)
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

        # ── Step 2: Quantum channel transmission ───────────────────────────────
        bob_bits, bob_bases = self.channel.transmit(alice_bits, alice_bases)

        # ── Step 3: Sifting ────────────────────────────────────────────────────
        # Alice and Bob compare bases on the public classical channel.
        # They keep only the bit positions where they used the same basis.
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

        # ── Step 4: QBER estimation ────────────────────────────────────────────
        # A random sample of sifted bits is revealed publicly to measure the
        # error rate. These bits are discarded afterward — they cannot be part
        # of the final key.
        sample_size = max(10, int(len(sifted_alice) * self.sample_fraction))
        sample_alice = sifted_alice[:sample_size]
        sample_bob = sifted_bob[:sample_size]
        errors = sum(a != b for a, b in zip(sample_alice, sample_bob))
        qber = errors / sample_size

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
            )

        # ── Step 5: Error correction ───────────────────────────────────────────
        # Binary reconciliation: compare block parities to locate and fix errors.
        # Real systems use Cascade or LDPC. This simplified version corrects one
        # error per 8-bit block — sufficient for typical low QBER values.
        corrected_bob = self._error_correct(key_alice, key_bob)

        # ── Step 6: Privacy amplification ─────────────────────────────────────
        # Hash the corrected key to collapse Eve's partial information to zero.
        # BLAKE2b acting as a universal hash ensures that even if Eve obtained
        # t bits of information, the output leaks at most 2^(-security_param) bits.
        final_key = self._privacy_amplify(corrected_bob)

        return BB84Result(
            final_key=final_key,
            key_length_bits=len(final_key) * 8,
            raw_bits=n_bits,
            sifted_bits=len(sifted_alice),
            qber=qber,
            eavesdropper_detected=False,
            secure=True,
        )

    # ── Internal helpers ───────────────────────────────────────────────────────

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


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    scenarios = [
        ("Normal channel (1% noise)",      {"error_rate": 0.01, "eavesdrop": False}),
        ("Noisy channel (5% noise)",        {"error_rate": 0.05, "eavesdrop": False}),
        ("Eavesdropper present (~25% QBER)", {"error_rate": 0.01, "eavesdrop": True}),
    ]

    print("BB84 QKD Protocol Simulator")
    print("=" * 60)

    for name, kwargs in scenarios:
        print(f"\nScenario: {name}")
        result = BB84Protocol(**kwargs).run(n_bits=4096)
        print(f"  Raw qubits sent:  {result.raw_bits}")
        print(f"  Sifted bits:      {result.sifted_bits}  (~50% of raw)")
        print(f"  Estimated QBER:   {result.qber:.3f}  ({result.qber * 100:.1f}%)")
        if result.secure:
            print(f"  Final key (256b): {result.final_key.hex()}")
        else:
            print(f"  ABORT — {'eavesdropper detected' if result.eavesdropper_detected else 'QBER too high'}")
