"""
QKD Channel Metrics Monitor

Tracks and displays real-time statistics from BB84 sessions:
  - QBER per session (quantum bit error rate)
  - Key generation rate (bits per session)
  - Secure vs aborted session counts
  - Eavesdropper detection events
  - Pool level snapshots (when integrated with KME)

Usage as a library:
  from metrics import MetricsCollector
  from bb84_simulator import BB84Protocol

  collector = MetricsCollector()
  result = BB84Protocol().run(n_bits=4096)
  collector.record_session(result)
  collector.print_dashboard()

Usage standalone:
  python metrics.py
  # Runs 10 demo sessions and prints the dashboard
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from bb84_simulator import BB84Protocol, BB84Result


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class SessionRecord:
    timestamp: datetime
    qber: float
    key_length_bits: int
    raw_bits: int
    sifted_bits: int
    secure: bool
    eavesdropper_detected: bool
    duration_ms: float


# ── MetricsCollector ───────────────────────────────────────────────────────────

class MetricsCollector:
    """
    Thread-safe collector for BB84 session metrics and KME pool snapshots.

    Records each BB84Result and provides aggregated statistics and a
    text dashboard. Designed to be used by kme_server / kme_dual to
    instrument the key pool in production, or standalone for demos.
    """

    MAX_HISTORY = 1000

    def __init__(self) -> None:
        self._sessions: deque[SessionRecord] = deque(maxlen=self.MAX_HISTORY)
        self._pool_levels: deque[int] = deque(maxlen=200)
        self._lock = threading.Lock()
        self._start_time = time.monotonic()

    def record_session(self, result: BB84Result, duration_ms: float = 0.0) -> None:
        """Record one completed BB84 session."""
        record = SessionRecord(
            timestamp=datetime.now(),
            qber=result.qber,
            key_length_bits=result.key_length_bits,
            raw_bits=result.raw_bits,
            sifted_bits=result.sifted_bits,
            secure=result.secure,
            eavesdropper_detected=result.eavesdropper_detected,
            duration_ms=duration_ms,
        )
        with self._lock:
            self._sessions.append(record)

    def record_pool_level(self, available: int) -> None:
        """Snapshot the current KME key pool depth."""
        with self._lock:
            self._pool_levels.append(available)

    # ── Statistics ─────────────────────────────────────────────────────────────

    def average_qber(self, window: int = 20) -> float:
        """Average QBER over the most recent `window` sessions."""
        with self._lock:
            recent = list(self._sessions)[-window:]
        if not recent:
            return 0.0
        return sum(s.qber for s in recent) / len(recent)

    def max_qber(self, window: int = 20) -> float:
        with self._lock:
            recent = list(self._sessions)[-window:]
        return max((s.qber for s in recent), default=0.0)

    def key_rate_bps(self) -> float:
        """Average key bits generated per secure session."""
        with self._lock:
            secure = [s for s in self._sessions if s.secure]
        if not secure:
            return 0.0
        return sum(s.key_length_bits for s in secure) / len(secure)

    def total_key_bits(self) -> int:
        with self._lock:
            return sum(s.key_length_bits for s in self._sessions if s.secure)

    def session_counts(self) -> tuple[int, int, int]:
        """Returns (total, secure, aborted)."""
        with self._lock:
            total   = len(self._sessions)
            secure  = sum(1 for s in self._sessions if s.secure)
            aborted = total - secure
        return total, secure, aborted

    def eavesdrop_events(self) -> int:
        with self._lock:
            return sum(1 for s in self._sessions if s.eavesdropper_detected)

    def current_pool_level(self) -> Optional[int]:
        with self._lock:
            return self._pool_levels[-1] if self._pool_levels else None

    # ── Dashboard ──────────────────────────────────────────────────────────────

    def print_dashboard(self) -> None:
        """Print a text metrics dashboard to stdout."""
        total, secure, aborted = self.session_counts()
        avg_qber  = self.average_qber()
        peak_qber = self.max_qber()
        key_bits  = self.total_key_bits()
        rate      = self.key_rate_bps()
        eve_count = self.eavesdrop_events()
        pool      = self.current_pool_level()
        uptime    = time.monotonic() - self._start_time

        h, rem = divmod(int(uptime), 3600)
        m, s   = divmod(rem, 60)

        print()
        print("━" * 58)
        print("  QKD Channel Metrics Dashboard")
        print("━" * 58)

        if total == 0:
            print("  No sessions recorded yet.")
            print("━" * 58)
            return

        print(f"  Uptime                : {h:02d}:{m:02d}:{s:02d}")
        print(f"  Sessions total        : {total}")
        print(f"  Secure / Aborted      : {secure} / {aborted}")
        print(f"  Eavesdrop detections  : {eve_count}")
        print()

        # QBER bar — 0% to 15% range, threshold at 11%
        bar_len   = 32
        filled    = min(int(avg_qber / 0.15 * bar_len), bar_len)
        bar       = "█" * filled + "░" * (bar_len - filled)
        thresh_x  = int(0.11 / 0.15 * bar_len)
        indicator = " " * thresh_x + "▲ 11% abort threshold"

        print(f"  QBER avg (recent 20)  : {avg_qber:.4f}  ({avg_qber*100:.2f}%)")
        print(f"  QBER peak (recent 20) : {peak_qber:.4f}  ({peak_qber*100:.2f}%)")
        print(f"  QBER bar              : [{bar}]")
        print(f"                           {indicator}")
        print()

        print(f"  Key material total    : {key_bits:,} bits  ({key_bits // 8:,} bytes)")
        print(f"  Avg bits / session    : {rate:.0f} bits")

        if pool is not None:
            print(f"  Pool level (current)  : {pool} keys available")

        print("━" * 58)


# ── Standalone demo ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("Running BB84 demo sessions for metrics collection...")
    print()

    collector = MetricsCollector()
    proto = BB84Protocol

    scenarios = [
        ("Normal (1% noise)",           {"error_rate": 0.01, "eavesdrop": False}, 4096),
        ("Normal (1% noise)",           {"error_rate": 0.01, "eavesdrop": False}, 4096),
        ("Normal (1% noise)",           {"error_rate": 0.01, "eavesdrop": False}, 4096),
        ("Noisy channel (5% noise)",    {"error_rate": 0.05, "eavesdrop": False}, 8192),
        ("Noisy channel (5% noise)",    {"error_rate": 0.05, "eavesdrop": False}, 8192),
        ("Eavesdropper (intercept)",    {"error_rate": 0.01, "eavesdrop": True},  4096),
        ("Normal (1% noise)",           {"error_rate": 0.01, "eavesdrop": False}, 4096),
        ("Normal (1% noise)",           {"error_rate": 0.01, "eavesdrop": False}, 4096),
        ("Eavesdropper (intercept)",    {"error_rate": 0.01, "eavesdrop": True},  4096),
        ("Normal (2% noise)",           {"error_rate": 0.02, "eavesdrop": False}, 4096),
    ]

    for i, (label, kwargs, n_bits) in enumerate(scenarios, 1):
        t0 = time.monotonic()
        result = proto(**kwargs).run(n_bits=n_bits)
        elapsed_ms = (time.monotonic() - t0) * 1000
        collector.record_session(result, duration_ms=elapsed_ms)
        status = "SECURE" if result.secure else "ABORTED"
        print(f"  [{i:2d}] {label:<35} QBER={result.qber:.3f}  {status}")

    collector.record_pool_level(42)   # simulate a KME pool snapshot
    collector.print_dashboard()
