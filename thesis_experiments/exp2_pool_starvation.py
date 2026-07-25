"""
Thesis Experiment 2 — Key-pool starvation / operational collapse near the
11% BB84 abort threshold.

Part A: Cascade/error-correction leakage model.
  Analytic net secret-key fraction per sifted bit:
      r(Q) = 1 - f_ec * H2(Q) - H2(Q)
  for reconciliation efficiencies f_ec in {1.00 (Shannon), 1.16 (Cascade),
  1.25}, plus an empirical sweep of the actual BB84 simulator
  (implementation/bb84_simulator.py, classical backend) recording sifted
  length, final key length, yield per raw bit, and abort frequency.

Part B: Discrete-time KME pool-depletion simulation driven by the measured
  yields: pool starts at P0 = 50 keys (matches POOL_TARGET in
  implementation/kme_server.py), consumers draw D = 1 key/s, producer
  generates at 2*D * [r(Q)/r(0)] * (1 - abort_rate(Q)), capped at the pool
  target (the KME only refills up to POOL_TARGET).

Part C (spec deliverables): a fine-grid analytic sweep at the canonical
  Cascade efficiency f_ec=1.16 that fixes a sifted-bit input rate and models a
  fixed-capacity KME pool against a fixed consumer, producing the required
  spec artifacts (pool_starvation.json / .csv with the mandated columns, and
  the net-yield figure).

Formula provenance (read from the repo, not guessed):
  * EC/reconciliation leakage per sifted bit = f_ec * H2(Q).
      qkdsec/src/qkdsec/proofs/protocols/bb84.py  BB84.leakage:
      leakage = yield * f_ec * h(QBER);  f_ec default 1.16 ("practical
      Cascade/LDPC ~1.1-1.2").
  * Privacy-amplification cost per sifted bit = H2(Q) (Eve's bound).
      qkdsec/src/qkdsec/sim/bb84.py  _privacy_amplify:
      secure_bits = n - ceil(n*h(QBER)) - leaked_bits.
  * Hard abort at QBER > 0.11.
      implementation/bb84_simulator.py  qber_threshold=0.11.
  Net secure fraction (Shor-Preskill form):
      r(Q) = max(0, 1 - H2(Q) - f_ec*H2(Q)).

Outputs:
  thesis_data/cascade_leakage_model.csv
  thesis_data/empirical_key_yield.csv
  thesis_data/pool_starvation.csv        (spec columns)
  thesis_data/pool_starvation.json       (spec metadata + arrays)
  thesis_figures/cascade_leakage.png
  thesis_figures/pool_depletion_keycount.png   (Part B key-count model)
  thesis_figures/pool_depletion_timeline.png   (Part C spec, bit reservoir)
  thesis_figures/pool_starvation_yield.png

No existing source files are modified: bb84_simulator is imported and its
module-level `secrets` reference is replaced at runtime with a seeded RNG
shim so the sweep is reproducible.
"""

import csv
import json
import math
import os
import random
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPL_DIR = os.path.join(REPO_ROOT, "implementation")
DATA_DIR = os.path.join(REPO_ROOT, "thesis_data")
FIG_DIR = os.path.join(REPO_ROOT, "thesis_figures")
sys.path.insert(0, IMPL_DIR)

import bb84_simulator  # noqa: E402
from bb84_simulator import BB84Protocol  # noqa: E402
from metrics import MetricsCollector  # noqa: E402

# ── Reproducibility: seeded shim for the module's `secrets` reference ────────


class _SeededSecrets:
    """Drop-in replacement for the `secrets` module (randbelow only)."""

    def __init__(self, seed: int):
        self._rng = random.Random(seed)

    def randbelow(self, n: int) -> int:
        return self._rng.randrange(n)


SEED = 42
bb84_simulator.secrets = _SeededSecrets(SEED)

# ── Experiment parameters ─────────────────────────────────────────────────────

QBER_GRID = [round(0.005 * i, 3) for i in range(0, 25)]   # 0.000 .. 0.120
F_EC_VALUES = [1.00, 1.16, 1.25]
N_BITS = 8192
N_TRIALS = 20
ABORT_THRESHOLD = 0.11

# Part B
POOL_TARGET = 50          # matches kme_server.POOL_TARGET
DEMAND = 1.0              # keys/sec drawn by consumers
SURPLUS_FACTOR = 2.0      # production = 2*D at Q=0
DT = 1.0                  # seconds per step
T_MAX = 1800.0            # simulation horizon
PART_B_QBERS = [0.01, 0.04, 0.07, 0.09, 0.10, 0.105, 0.109]
F_EC_POOL = 1.16          # Cascade efficiency used to drive production

# ── Part C: spec-mandated analytic pool model (bit-rate reservoir) ────────────
# Assumption (documented): a fixed sifted-bit input rate. BB84 sifts ~50% of
# raw qubits; pinning the post-sift rate isolates the QBER dependence to
# reconciliation (EC leakage) and privacy amplification — the physics this
# experiment targets.
SIFTED_RATE_BPS = 1.0e6                          # 1e6 sifted bits/s (assumption)
DEFAULT_KEY_SIZE = 256                           # kme_server.DEFAULT_KEY_SIZE
POOL_CAPACITY_BITS = POOL_TARGET * DEFAULT_KEY_SIZE   # 50 x 256 = 12,800 bits
# Consumer draw pinned to net production at a healthy 2% QBER operating point,
# so low noise is comfortably stable and the collapse point is meaningful.
PIN_QBER = 0.02
PART_C_QBERS = [0.02, 0.05, 0.08, 0.10]          # representative timelines
PART_C_HORIZON_S = 0.05                          # timeline horizon (seconds)


# ── Helpers ───────────────────────────────────────────────────────────────────

def h2(q: float) -> float:
    """Binary entropy in bits."""
    if q <= 0.0 or q >= 1.0:
        return 0.0
    return -q * math.log2(q) - (1 - q) * math.log2(1 - q)


def net_secret_fraction(q: float, f_ec: float) -> float:
    """r(Q) = 1 - f_ec*H2(Q) - H2(Q) per sifted bit (may go negative)."""
    return 1.0 - f_ec * h2(q) - h2(q)


def zero_yield_qber(f_ec: float) -> float:
    """Bisect for the QBER where r(Q) = 0 (i.e., H2(Q) = 1/(1+f_ec))."""
    lo, hi = 1e-9, 0.5
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if net_secret_fraction(mid, f_ec) > 0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ── Part A1: analytic leakage model ──────────────────────────────────────────

def run_analytic() -> tuple[list[dict], dict[float, float]]:
    rows = []
    for q in QBER_GRID:
        row = {"qber": q, "h2": round(h2(q), 6)}
        for f in F_EC_VALUES:
            row[f"r_fec_{f:.2f}"] = round(net_secret_fraction(q, f), 6)
        rows.append(row)

    zero_points = {f: zero_yield_qber(f) for f in F_EC_VALUES}

    path = os.path.join(DATA_DIR, "cascade_leakage_model.csv")
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[A1] wrote {path} ({len(rows)} rows)")
    for f, qz in sorted(zero_points.items()):
        print(f"[A1] zero-yield QBER for f_ec={f:.2f}: {qz:.4f} ({qz*100:.2f}%)")
    return rows, zero_points


# ── Part A2: empirical simulator sweep ───────────────────────────────────────

def run_empirical() -> list[dict]:
    collector = MetricsCollector()
    rows = []
    for q in QBER_GRID:
        qbers, sifted, final_bits, aborts = [], [], [], 0
        for _ in range(N_TRIALS):
            proto = BB84Protocol(
                error_rate=q, backend="classical",
                qber_threshold=ABORT_THRESHOLD,
            )
            result = proto.run(n_bits=N_BITS)
            collector.record_session(result)
            qbers.append(result.qber)
            sifted.append(result.sifted_bits)
            final_bits.append(result.key_length_bits)
            if not result.secure:
                aborts += 1
        abort_rate = aborts / N_TRIALS
        yield_per_raw = (sum(final_bits) / N_TRIALS) / N_BITS
        row = {
            "qber_target": q,
            "qber_observed_mean": round(sum(qbers) / N_TRIALS, 5),
            "sifted_bits": round(sum(sifted) / N_TRIALS, 1),
            "final_key_bits": round(sum(final_bits) / N_TRIALS, 1),
            "yield_per_raw_bit": round(yield_per_raw, 6),
            "abort_rate": abort_rate,
            "n_trials": N_TRIALS,
        }
        rows.append(row)
        print(f"[A2] Q={q:.3f}  obsQBER={row['qber_observed_mean']:.4f}  "
              f"yield/raw={row['yield_per_raw_bit']:.5f}  "
              f"abort_rate={abort_rate:.2f}")

    total, secure, aborted = collector.session_counts()
    print(f"[A2] sessions total={total} secure={secure} aborted={aborted}")

    path = os.path.join(DATA_DIR, "empirical_key_yield.csv")
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[A2] wrote {path} ({len(rows)} rows)")
    return rows


# ── Part B: pool-depletion simulation ────────────────────────────────────────

def interp_abort_rate(q: float, empirical_rows: list[dict]) -> float:
    xs = [r["qber_target"] for r in empirical_rows]
    ys = [r["abort_rate"] for r in empirical_rows]
    return float(np.interp(q, xs, ys))


def run_pool_simulation(empirical_rows: list[dict]) -> tuple[list[dict], dict]:
    rows = []
    timelines = {}
    for q in PART_B_QBERS:
        r_rel = max(0.0, net_secret_fraction(q, F_EC_POOL))  # r(0) = 1
        success = 1.0 - interp_abort_rate(q, empirical_rows)
        production_rel = r_rel * success
        production = SURPLUS_FACTOR * DEMAND * production_rel

        collector = MetricsCollector()
        pool = float(POOL_TARGET)
        levels = [pool]
        time_to_empty = math.inf
        t = 0.0
        while t < T_MAX:
            t += DT
            pool = min(POOL_TARGET, pool + production * DT)  # refill to target
            pool -= DEMAND * DT                              # consumer draw
            if pool <= 0.0:
                pool = 0.0
                if time_to_empty is math.inf:
                    time_to_empty = t
                levels.append(pool)
                break
            levels.append(pool)
            collector.record_pool_level(int(pool))

        min_level = min(levels)
        timelines[q] = levels
        rows.append({
            "qber": q,
            "production_rate_rel": round(production_rel, 4),
            "time_to_empty_s": time_to_empty if time_to_empty is not math.inf else "inf",
            "min_pool_level": round(min_level, 2),
        })
        tte = "never (stable)" if time_to_empty is math.inf else f"{time_to_empty:.0f}s"
        print(f"[B] Q={q:.3f}  prod_rel={production_rel:.3f}  "
              f"time_to_empty={tte}  min_pool={min_level:.1f}")

    path = os.path.join(DATA_DIR, "pool_starvation.csv")
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"[B] wrote {path} ({len(rows)} rows)")
    return rows, timelines


# ── Figures ───────────────────────────────────────────────────────────────────

def plot_cascade_leakage(analytic_rows, zero_points, empirical_rows):
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9, 9), sharex=True,
        gridspec_kw={"height_ratios": [3, 2]},
    )

    qs = [r["qber"] for r in analytic_rows]
    colors = {1.00: "tab:blue", 1.16: "tab:orange", 1.25: "tab:red"}
    for f in F_EC_VALUES:
        ys = [r[f"r_fec_{f:.2f}"] for r in analytic_rows]
        label = f"f_ec = {f:.2f}" + (" (Shannon limit)" if f == 1.0 else
                                     " (typical Cascade)" if f == 1.16 else "")
        ax1.plot(qs, ys, color=colors[f], lw=2, label=label)
        qz = zero_points[f]
        ax1.axvline(qz, color=colors[f], ls=":", lw=1)
        ax1.plot([qz], [0], "o", color=colors[f], ms=7, zorder=5)
        ax1.annotate(f"r=0 @ {qz*100:.2f}%", xy=(qz, 0),
                     xytext=(qz - 0.012, 0.12 + 0.10 * F_EC_VALUES.index(f)),
                     fontsize=8, color=colors[f],
                     arrowprops=dict(arrowstyle="->", color=colors[f], lw=0.8))

    ax1.axvline(ABORT_THRESHOLD, color="k", ls="--", lw=1.5,
                label="11% abort threshold")
    ax1.axhline(0, color="gray", lw=0.8)
    ax1.set_ylabel("Net secret fraction r(Q) per sifted bit")
    ax1.set_title("Cascade/EC leakage: r(Q) = 1 − f_ec·H2(Q) − H2(Q)\n"
                  "Zero-yield QBER falls well below the 11% abort threshold "
                  "once f_ec > 1")
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(alpha=0.3)

    eq = [r["qber_target"] for r in empirical_rows]
    ey = [r["yield_per_raw_bit"] for r in empirical_rows]
    ea = [r["abort_rate"] for r in empirical_rows]
    ax2.plot(eq, ey, "s-", color="tab:green", ms=5,
             label=f"Empirical yield/raw bit (classical backend, "
                   f"n={N_BITS}, {N_TRIALS} trials, 256-bit PA cap)")
    ax2.set_ylabel("Final key bits per raw bit", color="tab:green")
    ax2.tick_params(axis="y", labelcolor="tab:green")
    ax2.axvline(ABORT_THRESHOLD, color="k", ls="--", lw=1.5)
    ax2.grid(alpha=0.3)

    ax2b = ax2.twinx()
    ax2b.plot(eq, ea, "^-", color="tab:purple", ms=5, label="Abort rate")
    ax2b.set_ylabel("Abort rate over trials", color="tab:purple")
    ax2b.tick_params(axis="y", labelcolor="tab:purple")
    ax2b.set_ylim(-0.05, 1.05)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="center left", fontsize=8)
    ax2.set_xlabel("Channel QBER Q")

    fig.tight_layout()
    path = os.path.join(FIG_DIR, "cascade_leakage.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[fig] wrote {path}")


def plot_pool_depletion(timelines):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    cmap = plt.cm.viridis_r
    for i, (q, levels) in enumerate(sorted(timelines.items())):
        ts = np.arange(len(levels)) * DT
        ax.plot(ts, levels, lw=2, color=cmap(i / max(1, len(timelines) - 1)),
                label=f"Q = {q*100:.1f}%")
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("KME pool level (keys)")
    ax.set_title(f"KME key-pool depletion vs QBER\n"
                 f"(P0 = {POOL_TARGET} keys, demand = {DEMAND:.0f} key/s, "
                 f"production = {SURPLUS_FACTOR:.0f}·D·r(Q)·"
                 f"(1−abort), f_ec = {F_EC_POOL})")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_xlim(0, T_MAX)
    fig.tight_layout()
    path = os.path.join(FIG_DIR, "pool_depletion_keycount.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"[fig] wrote {path}")


# ── Part C: spec deliverables (fine-grid analytic pool model) ────────────────

def net_secure_fraction_clamped(q: float, f_ec: float = F_EC_POOL) -> float:
    """r(Q) = max(0, 1 - H2(Q) - f_ec*H2(Q))  (spec form, clamped at 0)."""
    return max(0.0, net_secret_fraction(q, f_ec))


def run_spec_pool_model():
    """Build the spec pool_starvation.{csv,json} and the yield figure."""
    qbers = np.linspace(0.0, 0.12, 601)
    h2_vals = np.array([h2(q) for q in qbers])
    ec_leak_frac = F_EC_POOL * h2_vals
    net_frac = np.array([net_secure_fraction_clamped(q) for q in qbers])
    net_bps = net_frac * SIFTED_RATE_BPS

    nominal_bps = net_secure_fraction_clamped(0.0) * SIFTED_RATE_BPS  # r(0)=1
    consumption_bps = net_secure_fraction_clamped(PIN_QBER) * SIFTED_RATE_BPS

    # Pool starts full; drains when consumption exceeds net production.
    drain = consumption_bps - net_bps
    draining = drain > 0
    pool_stable = ~draining
    depletion_time = np.full_like(qbers, np.nan)
    depletion_time[draining] = POOL_CAPACITY_BITS / drain[draining]

    q_zero = zero_yield_qber(F_EC_POOL)

    # CSV with the spec columns
    csv_path = os.path.join(DATA_DIR, "pool_starvation.csv")
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qber", "h2_qber", "ec_leak_fraction",
                    "net_secure_fraction", "net_key_bps", "pool_stable",
                    "depletion_time_s"])
        for i in range(len(qbers)):
            w.writerow([
                f"{qbers[i]:.6f}", f"{h2_vals[i]:.6f}",
                f"{ec_leak_frac[i]:.6f}", f"{net_frac[i]:.6f}",
                f"{net_bps[i]:.3f}", bool(pool_stable[i]),
                "" if math.isnan(depletion_time[i]) else f"{depletion_time[i]:.6f}",
            ])
    print(f"[C] wrote {csv_path} ({len(qbers)} rows)")

    # JSON metadata + arrays
    json_path = os.path.join(DATA_DIR, "pool_starvation.json")
    payload = {
        "metadata": {
            "experiment": "exp2_pool_starvation",
            "formula": "r(QBER) = max(0, 1 - H2(QBER) - f_ec*H2(QBER))",
            "formula_source": {
                "ec_leakage": "qkdsec/src/qkdsec/proofs/protocols/bb84.py "
                              "BB84.leakage = yield*f_ec*h(QBER), f_ec default 1.16",
                "privacy_amplification": "qkdsec/src/qkdsec/sim/bb84.py "
                              "_privacy_amplify: secure_bits = n - ceil(n*h(QBER)) - leaked",
                "abort_threshold": "implementation/bb84_simulator.py qber_threshold=0.11",
            },
            "constants": {
                "f_ec": F_EC_POOL,
                "qber_abort_threshold": ABORT_THRESHOLD,
                "default_key_size_bits": DEFAULT_KEY_SIZE,
                "pool_target_keys": POOL_TARGET,
            },
            "assumptions": {
                "sifted_rate_bps": SIFTED_RATE_BPS,
                "sifted_rate_note": "fixed post-sift input rate; isolates QBER "
                                    "dependence to reconciliation + privacy amp",
                "pool_capacity_bits": POOL_CAPACITY_BITS,
                "consumption_bps": consumption_bps,
                "consumption_note": f"pinned to net production at QBER={PIN_QBER}",
            },
            "results": {
                "qber_zero_yield": q_zero,
                "nominal_net_bps": nominal_bps,
                "note": "net secure yield reaches zero below the 0.11 abort threshold",
            },
        },
        "arrays": {
            "qber": qbers.tolist(),
            "h2_qber": h2_vals.tolist(),
            "ec_leak_fraction": ec_leak_frac.tolist(),
            "net_secure_fraction": net_frac.tolist(),
            "net_key_bps": net_bps.tolist(),
            "pool_stable": [bool(x) for x in pool_stable],
            "depletion_time_s": [None if math.isnan(x) else float(x)
                                 for x in depletion_time],
        },
    }
    with open(json_path, "w") as fh:
        json.dump(payload, fh, indent=2)
    print(f"[C] wrote {json_path}")

    # Figure: net secure fraction & net key rate vs QBER
    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    ax1.plot(qbers, net_frac, color="#1f77b4", lw=2.2,
             label="Net secure fraction  r(Q)")
    ax1.plot(qbers, ec_leak_frac, color="#ff7f0e", lw=1.6, ls=":",
             label=r"EC leakage  $f_{ec}\,H_2$(Q)")
    ax1.plot(qbers, h2_vals, color="#2ca02c", lw=1.2, ls="-.",
             label=r"Privacy-amp cost  $H_2$(Q)")
    ax1.axvline(ABORT_THRESHOLD, color="red", ls="--", lw=1.8,
                label="11% abort threshold")
    ax1.axvline(q_zero, color="purple", ls="--", lw=1.5,
                label=f"net yield = 0  (Q={q_zero*100:.2f}%)")
    ax1.plot([q_zero], [0.0], "o", color="purple", ms=7, zorder=5)
    ax1.set_xlabel("Channel QBER Q")
    ax1.set_ylabel("bits per sifted bit")
    ax1.set_xlim(0, 0.12)
    ax1.set_ylim(0, 1.05)
    ax1.grid(alpha=0.3)

    ax2 = ax1.twinx()
    ax2.set_ylabel("net secure key rate (bits/s)")
    ax2.set_ylim(0, 1.05 * nominal_bps)

    ax1.set_title("Operational collapse: net secure key yield vs QBER "
                  f"(f_ec={F_EC_POOL})\n"
                  f"zero yield at Q={q_zero*100:.2f}%, far below the 11% abort")
    ax1.legend(loc="upper right", fontsize=8.5, framealpha=0.9)
    fig.tight_layout()
    fig_path = os.path.join(FIG_DIR, "pool_starvation_yield.png")
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    print(f"[fig] wrote {fig_path}")

    # Figure: pool depletion timelines at the spec QBER values
    fig, ax = plt.subplots(figsize=(9, 5.5))
    t = np.linspace(0, PART_C_HORIZON_S, 500)
    colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(PART_C_QBERS)))
    for q, c in zip(PART_C_QBERS, colors):
        prod = net_secure_fraction_clamped(q) * SIFTED_RATE_BPS
        net_drain = consumption_bps - prod
        level = np.clip(POOL_CAPACITY_BITS - net_drain * t, 0.0, POOL_CAPACITY_BITS)
        if net_drain > 0:
            lbl = f"Q={q*100:.0f}%  (depletes in {POOL_CAPACITY_BITS/net_drain*1000:.2f} ms)"
        else:
            lbl = f"Q={q*100:.0f}%  (stable)"
        ax.plot(t * 1000, level, lw=2.0, color=c, label=lbl)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xlabel("time (ms)")
    ax.set_ylabel("KME pool level (secure bits)")
    ax.set_ylim(0, POOL_CAPACITY_BITS * 1.05)
    ax.set_xlim(0, PART_C_HORIZON_S * 1000)
    ax.grid(alpha=0.3)
    ax.set_title("KME key-pool depletion under rising QBER\n"
                 f"(capacity {POOL_CAPACITY_BITS} bits = {POOL_TARGET}x256-bit keys; "
                 f"consumption pinned to Q={PIN_QBER})")
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    tl_path = os.path.join(FIG_DIR, "pool_depletion_timeline.png")
    fig.savefig(tl_path, dpi=150)
    plt.close(fig)
    print(f"[fig] wrote {tl_path}  (spec QBERs {PART_C_QBERS})")

    return {
        "q_zero": q_zero,
        "nominal_bps": nominal_bps,
        "consumption_bps": consumption_bps,
        "qbers": qbers,
        "net_frac": net_frac,
        "net_bps": net_bps,
        "depletion_time": depletion_time,
        "pool_stable": pool_stable,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    print("=" * 70)
    print("Experiment 2 — key-pool starvation near the 11% abort threshold")
    print(f"seed={SEED}  n_bits={N_BITS}  trials/point={N_TRIALS}")
    print("=" * 70)

    analytic_rows, zero_points = run_analytic()
    empirical_rows = run_empirical()
    pool_rows, timelines = run_pool_simulation(empirical_rows)

    plot_cascade_leakage(analytic_rows, zero_points, empirical_rows)
    plot_pool_depletion(timelines)

    spec = run_spec_pool_model()

    print("\nSummary")
    print("-" * 70)
    for f, qz in sorted(zero_points.items()):
        print(f"  zero-yield QBER (f_ec={f:.2f}): {qz*100:.2f}%")
    print("  Pool time-to-empty (Part B, key-count model):")
    for r in pool_rows:
        print(f"    Q={r['qber']:<6} prod_rel={r['production_rate_rel']:<7} "
              f"tte={r['time_to_empty_s']}s min_pool={r['min_pool_level']}")

    print("\n  Spec pool model (Part C, f_ec=1.16, bit reservoir):")
    print(f"    net secure yield reaches ZERO at QBER = {spec['q_zero']*100:.2f}%"
          f"  (<< 11% abort)")
    print(f"    nominal net rate (Q->0)      : {spec['nominal_bps']:,.0f} bits/s")
    print(f"    consumption (pinned @ Q={PIN_QBER}) : {spec['consumption_bps']:,.0f} bits/s")
    print(f"    pool capacity                : {POOL_CAPACITY_BITS} bits "
          f"({POOL_TARGET} x {DEFAULT_KEY_SIZE}-bit keys)")
    print(f"    {'QBER':>6} {'net_frac':>9} {'net_bps':>12} {'stable':>7} {'deplete_ms':>12}")
    for q in [0.0, 0.02, 0.05, 0.08, 0.10, 0.11]:
        prod = net_secure_fraction_clamped(q) * SIFTED_RATE_BPS
        d = spec["consumption_bps"] - prod
        if d > 0:
            dms = f"{POOL_CAPACITY_BITS / d * 1000:.3f}"
            stab = "no"
        else:
            dms, stab = "stable", "yes"
        print(f"    {q:>6.2f} {net_secure_fraction_clamped(q):>9.4f} "
              f"{prod:>12,.0f} {stab:>7} {dms:>12}")


if __name__ == "__main__":
    main()
