"""
Hybrid QKD + Post-Quantum Cryptography Key Derivation

Implements the combined key derivation pattern per:
  - ETSI TS 104 015 (hybrid QKD+PQC key derivation)
  - IETF RFC 9794 (hybrid key exchange terminology)
  - NIST FIPS 203 (ML-KEM / Kyber-768 — mocked here)

Architecture:
  QKD key (from KME)     ──┐
                            ├──► HKDF-SHA256 ──► 256-bit combined secret
  ML-KEM shared secret   ──┘

Security: the combined key is secure if EITHER the QKD channel OR the
ML-KEM is unbroken. An attacker must break both simultaneously.

In production, replace MockMLKEM with liboqs Python bindings:
  from oqs import KeyEncapsulation
  kem = KeyEncapsulation("Kyber768")
  pk, sk = kem.generate_keypair()
  ct, ss = kem.encap_secret(pk)
  ss2    = kem.decap_secret(ct)

Usage:
  from hybrid_kdf import HybridKeyExchange
  from bb84_simulator import BB84Protocol

  qkd_key = BB84Protocol().run(n_bits=4096).final_key  # 32 bytes

  alice = HybridKeyExchange(qkd_key)
  bob   = HybridKeyExchange(qkd_key)

  pk, ct, alice_key = alice.initiate()   # Alice sends (pk, ct) to Bob
  bob_key = bob.respond(pk, ct)          # Bob derives the same key

  assert alice_key == bob_key            # Shared secret established
"""

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# ── MockMLKEM ──────────────────────────────────────────────────────────────────

class MockMLKEM:
    """
    Mock ML-KEM (Kyber-768) key encapsulation mechanism.

    Mirrors Kyber-768 wire sizes:
      - Public key:     1184 bytes
      - Secret key:       32 bytes (simplified; real sk is 2400 bytes)
      - Ciphertext:     1088 bytes
      - Shared secret:    32 bytes

    Security note: this is NOT cryptographically secure. The shared secret
    is embedded in the first 32 bytes of the ciphertext so that any holder
    of the ciphertext can recover it — the inverse of a real KEM. This is
    intentional for simulation purposes and clearly documented here.

    Replace with liboqs or pqcrypto for production use.
    """

    PUBLIC_KEY_SIZE  = 1184  # bytes — Kyber-768 public key
    SECRET_KEY_SIZE  = 32    # bytes — simplified
    CIPHERTEXT_SIZE  = 1088  # bytes — Kyber-768 ciphertext
    SHARED_SECRET_SIZE = 32  # bytes — Kyber-768 shared secret

    def keygen(self) -> tuple[bytes, bytes]:
        """Generate a (public_key, secret_key) keypair."""
        secret_key = os.urandom(self.SECRET_KEY_SIZE)
        public_key = os.urandom(self.PUBLIC_KEY_SIZE)
        return public_key, secret_key

    def encapsulate(self, public_key: bytes) -> tuple[bytes, bytes]:
        """
        Encapsulate: generate a shared secret and return (ciphertext, shared_secret).

        Mock behavior: the shared secret is embedded in the first 32 bytes of
        the ciphertext, allowing decapsulate to recover it without the secret key.
        This is the opposite of real KEM security — done here for testability.
        """
        shared_secret = os.urandom(self.SHARED_SECRET_SIZE)
        padding       = os.urandom(self.CIPHERTEXT_SIZE - self.SHARED_SECRET_SIZE)
        ciphertext    = shared_secret + padding
        return ciphertext, shared_secret

    def decapsulate(self, secret_key: bytes, ciphertext: bytes) -> bytes:
        """
        Decapsulate: recover the shared secret from the ciphertext.

        Mock behavior: reads the first 32 bytes of ciphertext.
        """
        if len(ciphertext) < self.SHARED_SECRET_SIZE:
            raise ValueError(
                f"Ciphertext too short: expected at least {self.SHARED_SECRET_SIZE} bytes"
            )
        return ciphertext[:self.SHARED_SECRET_SIZE]


# ── Key derivation ─────────────────────────────────────────────────────────────

def derive_hybrid_key(
    qkd_key: bytes,
    kem_secret: bytes,
    context: bytes = b"hybrid-key-derivation",
) -> bytes:
    """
    Derive a 256-bit combined key from a QKD key and an ML-KEM shared secret.

    Per ETSI TS 104 015 §6.3 and RFC 9794 §4:
      IKM = qkd_key || kem_secret
      PRK = HKDF-Extract(salt="qkd-hybrid-v1", IKM)
      OKM = HKDF-Expand(PRK, info=context, length=32)

    Returns 32 bytes (256 bits).
    """
    ikm = qkd_key + kem_secret
    hkdf = HKDF(
        algorithm=SHA256(),
        length=32,
        salt=b"qkd-hybrid-v1",
        info=context,
    )
    return hkdf.derive(ikm)


# ── HybridKeyExchange ──────────────────────────────────────────────────────────

@dataclass
class HybridKeyResult:
    """Result of a hybrid key exchange initiation."""
    combined_key: bytes      # 256-bit shared secret (keep private)
    public_key:   bytes      # ML-KEM public key (send to peer)
    ciphertext:   bytes      # ML-KEM ciphertext (send to peer)
    algorithm:    str        # descriptor string


class HybridKeyExchange:
    """
    End-to-end hybrid QKD + ML-KEM key exchange.

    Both Alice and Bob must already share the same QKD key (obtained
    independently from their respective KME instances). The KEM layer
    adds a second independent secret that must also be broken for an
    attacker to recover the combined key.

    Typical flow:
      1. Alice calls initiate() → gets (public_key, ciphertext, combined_key)
      2. Alice sends public_key and ciphertext to Bob (out-of-band)
      3. Bob calls respond(public_key, ciphertext) → gets same combined_key
      4. Both use combined_key for AES-256-GCM or as TLS PSK
    """

    def __init__(self, qkd_key: bytes):
        if len(qkd_key) != 32:
            raise ValueError(f"QKD key must be 32 bytes, got {len(qkd_key)}")
        self._qkd_key = qkd_key
        self._kem = MockMLKEM()

    def initiate(self) -> HybridKeyResult:
        """
        Alice side: generate ML-KEM keypair, encapsulate, derive combined key.

        Returns a HybridKeyResult. Alice must send result.public_key and
        result.ciphertext to Bob so he can derive the same combined_key.
        """
        public_key, secret_key = self._kem.keygen()
        ciphertext, kem_secret = self._kem.encapsulate(public_key)
        combined = derive_hybrid_key(self._qkd_key, kem_secret)
        return HybridKeyResult(
            combined_key=combined,
            public_key=public_key,
            ciphertext=ciphertext,
            algorithm="QKD+ML-KEM-768/HKDF-SHA256",
        )

    def respond(self, public_key: bytes, ciphertext: bytes) -> bytes:
        """
        Bob side: decapsulate the KEM ciphertext, derive the same combined key.

        Returns the 256-bit combined key (same as alice_result.combined_key).
        """
        kem_secret = self._kem.decapsulate(public_key, ciphertext)
        return derive_hybrid_key(self._qkd_key, kem_secret)


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from bb84_simulator import BB84Protocol

    print("Hybrid QKD + ML-KEM Key Exchange Demo")
    print("=" * 55)

    result = BB84Protocol(error_rate=0.01).run(n_bits=4096)
    if not result.secure:
        print("BB84 failed — aborting demo.")
        sys.exit(1)

    qkd_key = result.final_key
    print(f"QKD key (BB84):    {qkd_key.hex()[:32]}...  ({len(qkd_key)*8} bits)")
    print(f"Channel QBER:      {result.qber:.3f}  ({result.qber*100:.1f}%)")
    print()

    alice = HybridKeyExchange(qkd_key)
    bob   = HybridKeyExchange(qkd_key)

    alice_result = alice.initiate()
    bob_key = bob.respond(alice_result.public_key, alice_result.ciphertext)

    match = alice_result.combined_key == bob_key
    print(f"Alice hybrid key:  {alice_result.combined_key.hex()[:32]}...")
    print(f"Bob   hybrid key:  {bob_key.hex()[:32]}...")
    print(f"Keys match:        {'YES — hybrid session established' if match else 'NO — mismatch!'}")
    print(f"Algorithm:         {alice_result.algorithm}")
    print()
    print("ML-KEM ciphertext size:", len(alice_result.ciphertext), "bytes (Kyber-768 mock)")
    print("ML-KEM public key size:", len(alice_result.public_key), "bytes")
