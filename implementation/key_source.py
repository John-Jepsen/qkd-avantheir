"""
KeySource Protocol — Vendor-agnostic key generation interface

Defines the contract that all key sources (BB84 simulator, QuintessenceLabs TSF,
ID Quantique Cerberis, Toshiba KME, QuantumCTek NMS) must implement so they
can be plugged into KeyPool without changing the ETSI 014 REST surface.

Usage:
    from key_source import BB84KeySource

    source = BB84KeySource(error_rate=0.01)
    key = source.generate(size_bits=256)
    print(key.key_id, key.key_bytes.hex())
"""

import hashlib
import uuid
from typing import Protocol, runtime_checkable

from bb84_simulator import BB84Protocol, BB84Result

# Re-export StoredKey so vendor modules can import from one place
from kme_server import StoredKey


@runtime_checkable
class KeySource(Protocol):
    """Protocol that all key backends must satisfy."""

    def generate(self, size_bits: int = 256) -> StoredKey:
        """Generate a single key of the requested size."""
        ...

    def health_check(self) -> dict:
        """Return a dict with at least {"status": "ok"|"degraded"|"error"}."""
        ...


class BB84KeySource:
    """Wraps the existing BB84Protocol as a KeySource."""

    def __init__(self, error_rate: float = 0.01, backend: str = "qiskit") -> None:
        self._proto = BB84Protocol(error_rate=error_rate, backend=backend)
        self._backend = backend

    def generate(self, size_bits: int = 256) -> StoredKey:
        n_raw = max(4096, size_bits * 25)
        result = self._proto.run(n_bits=n_raw)
        if not result.secure:
            raise RuntimeError("BB84 failed — QBER exceeded threshold")

        needed = size_bits // 8
        key = result.final_key
        while len(key) < needed:
            key += hashlib.blake2b(key, digest_size=32).digest()
        key = key[:needed]

        return StoredKey(
            key_id=str(uuid.uuid4()),
            key_bytes=key,
            size_bits=size_bits,
        )

    def health_check(self) -> dict:
        return {"status": "ok", "backend": self._backend, "type": "bb84_simulator"}
