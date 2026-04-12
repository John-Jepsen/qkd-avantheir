"""
Advanced Qiskit Integration — IBM Quantum Hardware & Realistic Noise

Extends the BB84 simulator with two new channel backends:

  1. RealisticNoiseChannel — Uses device-calibrated noise models from
     Qiskit Aer's FakeBackend classes (real T1/T2, readout errors, crosstalk)
     instead of the synthetic single-gate depolarizing model.

  2. IBMQuantumChannel — Submits BB84 circuits to real IBM Quantum hardware
     via the Qiskit Runtime service. Requires an IBM Quantum API token.

  3. QiskitCascadeCorrector — Multi-pass Cascade error correction that
     improves on the single-pass binary reconciliation in bb84_simulator.py.

Requirements:
  pip install qiskit-ibm-runtime qiskit-aer

Usage:
    from bb84_simulator import BB84Protocol

    # Hardware-calibrated noise (no API token needed):
    result = BB84Protocol(backend="realistic_noise").run(n_bits=4096)

    # Real IBM Quantum hardware (requires IBM_QUANTUM_TOKEN):
    result = BB84Protocol(backend="ibm_hardware").run(n_bits=512)
"""

import os
import secrets
import logging

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

log = logging.getLogger(__name__)

_BATCH_SIZE = 256


class RealisticNoiseChannel:
    """
    Quantum channel using device-calibrated noise from IBM fake backends.

    Instead of a single depolarizing error on the id gate, this loads the
    full noise profile of a real IBM device (T1/T2 decoherence, readout
    errors, gate errors, crosstalk) via AerSimulator.from_backend().

    Parameters
    ----------
    device_name : str
        Name of the fake backend to load. Options include:
        "sherbrooke", "brisbane", "osaka", "kyoto", "torino".
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper.
    """

    SUPPORTED_DEVICES = {
        "sherbrooke": "FakeSherbrooke",
        "brisbane": "FakeBrisbane",
        "osaka": "FakeOsaka",
        "kyoto": "FakeKyoto",
        "torino": "FakeTorino",
    }

    def __init__(self, device_name: str = "sherbrooke", eavesdrop: bool = False):
        self.device_name = device_name
        self.eavesdrop = eavesdrop
        self._ideal_backend = AerSimulator()
        self._noisy_backend = self._build_backend(device_name)
        log.info("RealisticNoiseChannel: loaded %s noise model", device_name)

    def _build_backend(self, device_name: str) -> AerSimulator:
        """Build an AerSimulator with noise from a real IBM device."""
        try:
            from qiskit_ibm_runtime.fake_provider import FakeSherbrooke
            fake_backends = {
                "sherbrooke": FakeSherbrooke,
            }
            # Try to import other backends; fall back to Sherbrooke
            try:
                from qiskit_ibm_runtime.fake_provider import FakeBrisbane
                fake_backends["brisbane"] = FakeBrisbane
            except ImportError:
                pass
            try:
                from qiskit_ibm_runtime.fake_provider import FakeOsaka
                fake_backends["osaka"] = FakeOsaka
            except ImportError:
                pass
            try:
                from qiskit_ibm_runtime.fake_provider import FakeKyoto
                fake_backends["kyoto"] = FakeKyoto
            except ImportError:
                pass
            try:
                from qiskit_ibm_runtime.fake_provider import FakeTorino
                fake_backends["torino"] = FakeTorino
            except ImportError:
                pass

            if device_name not in fake_backends:
                log.warning("Device '%s' not available, falling back to sherbrooke",
                            device_name)
                device_name = "sherbrooke"

            fake_backend = fake_backends[device_name]()
            noise_model = NoiseModel.from_backend(fake_backend)
            return AerSimulator(noise_model=noise_model)

        except ImportError:
            log.warning("qiskit-ibm-runtime not installed; using depolarizing fallback")
            from qiskit_aer.noise import depolarizing_error
            noise_model = NoiseModel()
            noise_model.add_all_qubit_quantum_error(
                depolarizing_error(0.015, 1), ["id"]
            )
            return AerSimulator(noise_model=noise_model)

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        """Simulate quantum transmission with device-calibrated noise."""
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]

        if self.eavesdrop:
            eve_bases = [secrets.randbelow(2) for _ in range(n)]
            eve_bits = self._run_circuit(alice_bits, alice_bases, eve_bases, noisy=False)
            bob_bits = self._run_circuit(eve_bits, eve_bases, bob_bases, noisy=True)
        else:
            bob_bits = self._run_circuit(alice_bits, alice_bases, bob_bases, noisy=True)

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

            for i in range(batch_size):
                idx = start + i
                if sender_bits[idx] == 1:
                    qc.x(i)
                if sender_bases[idx] == 1:
                    qc.h(i)

            if noisy:
                for i in range(batch_size):
                    qc.id(i)

            for i in range(batch_size):
                idx = start + i
                if receiver_bases[idx] == 1:
                    qc.h(i)
                qc.measure(i, i)

            backend = self._noisy_backend if noisy else self._ideal_backend
            job = backend.run(qc, shots=1)
            counts = job.result().get_counts()
            bitstring = list(counts.keys())[0].zfill(batch_size)
            bits = [int(b) for b in reversed(bitstring)]
            all_results.extend(bits[:batch_size])

        return all_results


class IBMQuantumChannel:
    """
    Quantum channel backed by real IBM Quantum hardware.

    Submits BB84 circuits to an IBM Quantum backend via the Runtime service.
    Requires the IBM_QUANTUM_TOKEN environment variable or a saved account.

    Parameters
    ----------
    backend_name : str
        IBM Quantum backend to target (e.g., "ibm_sherbrooke").
    eavesdrop : bool
        Simulate an intercept-resend eavesdropper.
    """

    def __init__(self, backend_name: str = "ibm_sherbrooke", eavesdrop: bool = False):
        self.backend_name = backend_name
        self.eavesdrop = eavesdrop
        self._service = None
        self._backend = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to IBM Quantum Runtime service."""
        try:
            from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

            token = os.environ.get("IBM_QUANTUM_TOKEN")
            if token:
                self._service = QiskitRuntimeService(
                    channel="ibm_quantum", token=token
                )
            else:
                # Try saved credentials
                self._service = QiskitRuntimeService()

            self._backend = self._service.backend(self.backend_name)
            log.info("IBMQuantumChannel: connected to %s", self.backend_name)

        except ImportError:
            raise ImportError(
                "qiskit-ibm-runtime is required for IBM hardware backend. "
                "Install with: pip install qiskit-ibm-runtime"
            )
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to IBM Quantum: {e}. "
                "Set IBM_QUANTUM_TOKEN environment variable or run "
                "QiskitRuntimeService.save_account()."
            )

    def transmit(
        self, alice_bits: list[int], alice_bases: list[int]
    ) -> tuple[list[int], list[int]]:
        """Transmit qubits via real IBM Quantum hardware."""
        n = len(alice_bits)
        bob_bases = [secrets.randbelow(2) for _ in range(n)]

        if self.eavesdrop:
            eve_bases = [secrets.randbelow(2) for _ in range(n)]
            eve_bits = self._run_circuit(alice_bits, alice_bases, eve_bases)
            bob_bits = self._run_circuit(eve_bits, eve_bases, bob_bases)
        else:
            bob_bits = self._run_circuit(alice_bits, alice_bases, bob_bases)

        return bob_bits, bob_bases

    def _run_circuit(
        self,
        sender_bits: list[int],
        sender_bases: list[int],
        receiver_bases: list[int],
    ) -> list[int]:
        """Build and execute circuits on real hardware in batches."""
        from qiskit_ibm_runtime import SamplerV2
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

        n = len(sender_bits)
        all_results: list[int] = []

        for start in range(0, n, _BATCH_SIZE):
            end = min(start + _BATCH_SIZE, n)
            batch_size = end - start

            qc = QuantumCircuit(batch_size, batch_size)

            for i in range(batch_size):
                idx = start + i
                if sender_bits[idx] == 1:
                    qc.x(i)
                if sender_bases[idx] == 1:
                    qc.h(i)

            for i in range(batch_size):
                idx = start + i
                if receiver_bases[idx] == 1:
                    qc.h(i)
                qc.measure(i, i)

            # Transpile for the target backend
            pm = generate_preset_pass_manager(
                backend=self._backend, optimization_level=1
            )
            transpiled = pm.run(qc)

            sampler = SamplerV2(self._backend)
            job = sampler.run([transpiled], shots=1)
            result = job.result()

            # Extract bitstring from SamplerV2 result
            bitarray = result[0].data.meas
            bitstring = bitarray.get_bitstrings()[0]
            bits = [int(b) for b in reversed(bitstring)]
            all_results.extend(bits[:batch_size])

        return all_results


class QiskitCascadeCorrector:
    """
    Multi-pass Cascade error correction protocol.

    Improves on the single-pass binary reconciliation in bb84_simulator.py
    by running multiple passes with increasing block sizes, catching errors
    that single-pass parity checks miss.

    Algorithm:
      Pass 1: block_size = initial_block_size (e.g., 8)
      Pass 2: block_size *= 2 (16), with random permutation
      Pass 3: block_size *= 2 (32), with random permutation
      ...
      Each pass corrects residual errors from previous passes.

    Parameters
    ----------
    n_passes : int
        Number of Cascade passes. More passes = fewer residual errors.
    initial_block_size : int
        Block size for the first pass. Doubles each subsequent pass.
    """

    def __init__(self, n_passes: int = 4, initial_block_size: int = 8):
        self.n_passes = n_passes
        self.initial_block_size = initial_block_size

    def correct(self, alice_bits: list[int], bob_bits: list[int]) -> list[int]:
        """Run multi-pass Cascade and return corrected Bob bits."""
        corrected = bob_bits[:]
        n = len(alice_bits)
        block_size = self.initial_block_size

        for pass_num in range(self.n_passes):
            # Generate a permutation for passes after the first
            if pass_num == 0:
                perm = list(range(n))
            else:
                perm = list(range(n))
                # Deterministic shuffle seeded by pass number for reproducibility
                import random
                rng = random.Random(pass_num)
                rng.shuffle(perm)

            # Apply permutation
            a_perm = [alice_bits[perm[i]] for i in range(n)]
            c_perm = [corrected[perm[i]] for i in range(n)]

            # Parity check and binary search correction on each block
            for start in range(0, n - block_size + 1, block_size):
                a_block = a_perm[start:start + block_size]
                c_block = c_perm[start:start + block_size]

                if sum(a_block) % 2 != sum(c_block) % 2:
                    # Binary search for the error within this block
                    error_idx = self._binary_search(
                        a_perm, c_perm, start, start + block_size
                    )
                    if error_idx is not None:
                        c_perm[error_idx] ^= 1

            # Reverse permutation
            for i in range(n):
                corrected[perm[i]] = c_perm[i]

            block_size *= 2

        return corrected

    def _binary_search(
        self, alice: list[int], bob: list[int], lo: int, hi: int
    ) -> int | None:
        """Binary search for a single error within a block."""
        while hi - lo > 1:
            mid = (lo + hi) // 2
            a_parity = sum(alice[lo:mid]) % 2
            b_parity = sum(bob[lo:mid]) % 2
            if a_parity != b_parity:
                hi = mid
            else:
                lo = mid

        if alice[lo] != bob[lo]:
            return lo
        return None
