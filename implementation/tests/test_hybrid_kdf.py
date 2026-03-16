"""
Tests for hybrid QKD + ML-KEM key derivation.

Covers: MockMLKEM wire sizes, derive_hybrid_key determinism and
sensitivity, and HybridKeyExchange initiate/respond symmetry.
"""

import os

import pytest
from hybrid_kdf import HybridKeyExchange, MockMLKEM, derive_hybrid_key


# ── MockMLKEM ──────────────────────────────────────────────────────────────────

def test_keygen_sizes():
    kem = MockMLKEM()
    pk, sk = kem.keygen()
    assert len(pk) == MockMLKEM.PUBLIC_KEY_SIZE
    assert len(sk) == MockMLKEM.SECRET_KEY_SIZE


def test_encapsulate_sizes():
    kem = MockMLKEM()
    pk, _ = kem.keygen()
    ct, ss = kem.encapsulate(pk)
    assert len(ct) == MockMLKEM.CIPHERTEXT_SIZE
    assert len(ss) == MockMLKEM.SHARED_SECRET_SIZE


def test_encapsulate_decapsulate_symmetry():
    kem = MockMLKEM()
    pk, sk = kem.keygen()
    ct, ss_enc = kem.encapsulate(pk)
    ss_dec = kem.decapsulate(sk, ct)
    assert ss_enc == ss_dec


def test_decapsulate_short_ciphertext_raises():
    kem = MockMLKEM()
    _, sk = kem.keygen()
    with pytest.raises(ValueError):
        kem.decapsulate(sk, b"\x00" * 10)


# ── derive_hybrid_key ──────────────────────────────────────────────────────────

def test_derive_is_deterministic():
    qkd = b"\xab" * 32
    kem = b"\xcd" * 32
    assert derive_hybrid_key(qkd, kem) == derive_hybrid_key(qkd, kem)


def test_derive_output_is_32_bytes():
    key = derive_hybrid_key(os.urandom(32), os.urandom(32))
    assert len(key) == 32


def test_derive_different_qkd_keys_different_output():
    kem = os.urandom(32)
    k1  = derive_hybrid_key(b"a" * 32, kem)
    k2  = derive_hybrid_key(b"b" * 32, kem)
    assert k1 != k2


def test_derive_different_kem_secrets_different_output():
    qkd = os.urandom(32)
    k1  = derive_hybrid_key(qkd, b"x" * 32)
    k2  = derive_hybrid_key(qkd, b"y" * 32)
    assert k1 != k2


def test_derive_context_affects_output():
    qkd = os.urandom(32)
    kem = os.urandom(32)
    k1  = derive_hybrid_key(qkd, kem, context=b"context-A")
    k2  = derive_hybrid_key(qkd, kem, context=b"context-B")
    assert k1 != k2


# ── HybridKeyExchange ──────────────────────────────────────────────────────────

def test_initiate_respond_produce_same_key():
    qkd_key = os.urandom(32)
    alice   = HybridKeyExchange(qkd_key)
    bob     = HybridKeyExchange(qkd_key)

    result   = alice.initiate()
    bob_key  = bob.respond(result.public_key, result.ciphertext)

    assert result.combined_key == bob_key


def test_combined_key_is_32_bytes():
    qkd_key = os.urandom(32)
    result  = HybridKeyExchange(qkd_key).initiate()
    assert len(result.combined_key) == 32


def test_algorithm_descriptor_set():
    result = HybridKeyExchange(os.urandom(32)).initiate()
    assert "QKD" in result.algorithm
    assert "ML-KEM" in result.algorithm


def test_different_qkd_keys_different_combined_keys():
    pk_ct = HybridKeyExchange(b"\x00" * 32).initiate()
    result_a = HybridKeyExchange(b"\xaa" * 32).respond(pk_ct.public_key, pk_ct.ciphertext)
    result_b = HybridKeyExchange(b"\xbb" * 32).respond(pk_ct.public_key, pk_ct.ciphertext)
    assert result_a != result_b


def test_wrong_qkd_key_breaks_symmetry():
    alice  = HybridKeyExchange(os.urandom(32))
    bob    = HybridKeyExchange(os.urandom(32))   # different QKD key
    result = alice.initiate()
    bob_key = bob.respond(result.public_key, result.ciphertext)
    assert result.combined_key != bob_key


def test_invalid_qkd_key_length_raises():
    with pytest.raises(ValueError):
        HybridKeyExchange(b"\x00" * 16)   # must be 32 bytes
