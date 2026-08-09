"""
Experiment 3 — Partial Intercept-Resend Sub-Threshold Exploit Sweep

Question
--------
Can a *partial* intercept-resend eavesdropper keep the observed QBER below the
classic 11% BB84 abort threshold while still stealing key material, and how well
does the trained ML detector catch these sub-threshold attacks compared with the
static 11% policy (which, by definition, accepts anything under 11%)?

Method
------
Uses the real BB84 simulator (`implementation/bb84_simulator.py`) on the Qiskit
Aer backend. The QiskitQuantumChannel supports `eavesdrop_fraction` in [0, 1]:
for each intercepted qubit Eve measures in a random basis and resends, inducing
the textbook ~25% QBER on that qubit; non-intercepted qubits pass through the
noisy channel untouched.

We sweep eavesdrop_fraction over {0.0, 0.1, ..., 1.0} at a fixed modest base
error_rate. For each fraction we record:
  - mean measured QBER (from BB84Result.qber)
  - theoretical QBER prediction: base_error + 0.25 * fraction
  - mean sift ratio
  - Eve's information-gain estimate (proportional to intercept fraction)
  - the trained eavesdrop detector's mean P(attack) and detection rate,
    where P(attack) = 1 - P(clean) and "detected" = predicted label != "clean"

Multi-seed error bars
---------------------
The BB84 simulator draws its channel noise from ``secrets`` (OS entropy), so
every run is an independent draw and there is no seedable RNG. To put honest
error bars on every metric we run ``N_SEEDS`` independent replicate *batches* per
fraction, each a batch of ``TRIALS_PER_SEED`` trials. We compute the per-fraction
mean within each batch, then aggregate mean ± standard deviation of those batch
means across the ``N_SEEDS`` replicates. The band on each curve is ±1 SD of the
batch-mean — a direct measure of run-to-run reproducibility. (Because BB84 uses
OS entropy, the "seed" labels a replicate batch; it does not make a batch
bitwise-reproducible.)

We then locate the sub-threshold exploit window: the largest eavesdrop_fraction
whose *mean measured* QBER stays below 0.11, and report the ML detector's
detection rate within that window against the static policy's rate (0% by
definition, since QBER < 0.11 there).

Outputs
-------
  thesis_data/partial_intercept_sweep.json
  thesis_data/partial_intercept_sweep.csv
  thesis_data/partial_intercept_sweep_per_seed.csv
  thesis_figures/subthreshold_qber.png
  thesis_figures/subthreshold_info_gain.png
"""

import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Repo paths ────────────────────────────────────────────────────────────────
THESIS_DIR = Path(__file__).resolve().parent.parent  # thesis/
REPO_ROOT = THESIS_DIR.parent  # repo root (holds implementation/)
IMPL_DIR = REPO_ROOT / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from bb84_simulator import BB84Protocol            # noqa: E402
from features import extract_features              # noqa: E402
from ml_eavesdrop_classifier import EavesdropClassifier  # noqa: E402

DATA_DIR = THESIS_DIR / "thesis_data"
FIG_DIR = THESIS_DIR / "thesis_figures"
MODEL_PATH = IMPL_DIR / "data" / "eavesdrop_model.pkl"

# ── Experiment configuration ──────────────────────────────────────────────────
# n_bits=4096 raw qubits sift to ~2048 bits (well above the 40-bit floor) and
# each Qiskit run is a few tenths of a second. N_SEEDS batches x TRIALS_PER_SEED
# trials x 11 fractions Qiskit runs; with the partial-intercept path running up
# to 3 circuits per run this stays a few minutes total. Reduce N_SEEDS or
# TRIALS_PER_SEED if slower.
N_BITS = 4096
N_SEEDS = 5                 # independent replicate batches -> mean +/- SD bands
TRIALS_PER_SEED = 15        # trials per batch (75 trials per fraction total)
BASE_ERROR_RATE = 0.01
FRACTIONS = [round(0.1 * i, 1) for i in range(11)]  # 0.0 .. 1.0
QBER_THRESHOLD = 0.11
# Classic intercept-resend induces 25% QBER on intercepted, matched-basis qubits.
IR_QBER_PER_INTERCEPT = 0.25

# Metrics we aggregate mean/std over across replicate batches.
_AGG_METRICS = ["qber_measured", "sift_ratio", "ml_p_attack", "ml_detection_rate"]


def eve_info_gain(fraction: float) -> float:
    """
    Principled estimate of Eve's information gain for partial intercept-resend.

    Eve measures the fraction of qubits she intercepts. On the sifted key
    (Alice/Bob bases match), a qubit Eve intercepted yields her the correct bit
    whenever her random basis matched Alice's (probability 1/2); on a basis
    mismatch she learns nothing about that sifted bit on average. Thus her
    expected fraction of correctly-known sifted key bits is ~0.5 * fraction.
    Information gain scales linearly with the intercept fraction — the more she
    taps, the more key she steals (at the cost of higher induced QBER).
    """
    return 0.5 * fraction


def _run_batch(clf, frac, eavesdrop):
    """Run TRIALS_PER_SEED trials at one fraction; return per-batch means."""
    qbers, sifts, p_attacks, detections = [], [], [], []
    for _ in range(TRIALS_PER_SEED):
        proto = BB84Protocol(
            error_rate=BASE_ERROR_RATE,
            eavesdrop=eavesdrop,
            eavesdrop_fraction=frac if eavesdrop else 1.0,
            backend="qiskit",
        )
        result = proto.run(n_bits=N_BITS)

        det = clf.predict_from_result(result)
        p_attack = 1.0 - det.probabilities.get("clean", 0.0)
        detected = det.predicted_label != "clean"

        qbers.append(result.qber)
        sifts.append(result.sift_ratio)
        p_attacks.append(p_attack)
        detections.append(1.0 if detected else 0.0)

    return {
        "qber_measured": float(np.mean(qbers)),
        "sift_ratio": float(np.mean(sifts)),
        "ml_p_attack": float(np.mean(p_attacks)),
        "ml_detection_rate": float(np.mean(detections)),
    }


def run_sweep():
    print(f"Loading eavesdrop detector: {MODEL_PATH}")
    clf = EavesdropClassifier.load(str(MODEL_PATH))

    per_fraction = {}
    raw_rows = []   # one row per (fraction, seed)

    for frac in FRACTIONS:
        eavesdrop = frac > 0.0
        # Collect one batch-mean per replicate seed.
        batches = {m: [] for m in _AGG_METRICS}
        for seed in range(N_SEEDS):
            bm = _run_batch(clf, frac, eavesdrop)
            for m in _AGG_METRICS:
                batches[m].append(bm[m])
            raw_rows.append([
                seed, frac, bm["qber_measured"], bm["sift_ratio"],
                bm["ml_p_attack"], bm["ml_detection_rate"],
            ])

        agg = {}
        for m in _AGG_METRICS:
            vals = np.array(batches[m], dtype=float)
            agg[f"{m}_mean"] = float(np.mean(vals))
            agg[f"{m}_std"] = float(np.std(vals))

        qber_theory = BASE_ERROR_RATE + IR_QBER_PER_INTERCEPT * frac
        info_gain = eve_info_gain(frac)
        below_threshold = agg["qber_measured_mean"] < QBER_THRESHOLD

        per_fraction[frac] = {
            "eavesdrop_fraction": frac,
            "qber_theory": qber_theory,
            "eve_info_gain": info_gain,
            "below_threshold": below_threshold,
            **agg,
        }

        print(
            f"frac={frac:.1f}  "
            f"QBER={agg['qber_measured_mean']:.4f}±{agg['qber_measured_std']:.4f} "
            f"(theory={qber_theory:.4f})  "
            f"sift={agg['sift_ratio_mean']:.3f}  "
            f"info_gain={info_gain:.3f}  "
            f"ML_det={agg['ml_detection_rate_mean']:.2f}±"
            f"{agg['ml_detection_rate_std']:.2f}  "
            f"below11%={below_threshold}"
        )

    return per_fraction, raw_rows


def find_window(per_fraction):
    """Largest eavesdrop_fraction whose MEAN measured QBER stays below 0.11."""
    sub = [f for f, d in per_fraction.items()
           if f > 0.0 and d["below_threshold"]]
    if not sub:
        return None
    max_frac = max(sub)
    d = per_fraction[max_frac]
    return {
        "max_eavesdrop_fraction_below_threshold": max_frac,
        "qber_at_window_edge": d["qber_measured_mean"],
        "qber_std_at_window_edge": d["qber_measured_std"],
        "eve_info_gain_at_window_edge": d["eve_info_gain"],
        "ml_detection_rate_at_window_edge": d["ml_detection_rate_mean"],
        "ml_detection_std_at_window_edge": d["ml_detection_rate_std"],
        "ml_p_attack_at_window_edge": d["ml_p_attack_mean"],
        # ML detection averaged across ALL positive-fraction sub-threshold points
        "ml_detection_rate_in_window_mean": float(np.mean([
            per_fraction[f]["ml_detection_rate_mean"] for f in sub
        ])),
        "static_policy_detection_rate_in_window": 0.0,
        "sub_threshold_fractions": sorted(sub),
    }


def write_outputs(per_fraction, raw_rows, window):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fracs = sorted(per_fraction.keys())
    keys = ["eavesdrop_fraction", "qber_theory", "eve_info_gain",
            "below_threshold"]
    for m in _AGG_METRICS:
        keys += [f"{m}_mean", f"{m}_std"]
    arr = {k: [per_fraction[f][k] for f in fracs] for k in keys}

    # ── JSON ──
    json_path = DATA_DIR / "partial_intercept_sweep.json"
    with open(json_path, "w") as f:
        json.dump({
            "metadata": {
                "experiment": "exp3_partial_intercept_sweep",
                "description": (
                    "Partial intercept-resend sub-threshold exploit sweep: "
                    "measured vs theoretical QBER, Eve info gain, and ML "
                    "detector performance vs the static 11% policy. Mean +/- SD "
                    "over independent replicate batches."
                ),
                "n_bits": N_BITS,
                "n_seeds": N_SEEDS,
                "trials_per_seed": TRIALS_PER_SEED,
                "trials_per_fraction_total": N_SEEDS * TRIALS_PER_SEED,
                "base_error_rate": BASE_ERROR_RATE,
                "qber_threshold": QBER_THRESHOLD,
                "ir_qber_per_intercept": IR_QBER_PER_INTERCEPT,
                "fractions": FRACTIONS,
                "backend": "qiskit",
                "model_path": str(MODEL_PATH),
                "info_gain_definition": "0.5 * eavesdrop_fraction",
                "p_attack_definition": "1 - P(clean) from RF classifier",
                "detection_definition": "predicted label != clean",
                "error_bar_definition": (
                    "+/-1 SD of the per-batch mean across N_SEEDS replicate "
                    "batches; BB84 uses secrets (OS entropy), so batches are "
                    "independent draws (seed labels a batch, not a fixed RNG)."
                ),
            },
            "arrays": arr,
            "exploit_window": window,
        }, f, indent=2)
    print(f"Wrote {json_path}")

    # ── Aggregated CSV ──
    csv_path = DATA_DIR / "partial_intercept_sweep.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        header = ["eavesdrop_fraction", "qber_measured_mean", "qber_measured_std",
                  "qber_theory", "sift_ratio_mean", "sift_ratio_std",
                  "eve_info_gain", "ml_detection_rate_mean",
                  "ml_detection_rate_std", "below_threshold"]
        w.writerow(header)
        for fr in fracs:
            d = per_fraction[fr]
            w.writerow([
                d["eavesdrop_fraction"], round(d["qber_measured_mean"], 6),
                round(d["qber_measured_std"], 6), round(d["qber_theory"], 6),
                round(d["sift_ratio_mean"], 6), round(d["sift_ratio_std"], 6),
                round(d["eve_info_gain"], 6),
                round(d["ml_detection_rate_mean"], 6),
                round(d["ml_detection_rate_std"], 6), d["below_threshold"],
            ])
    print(f"Wrote {csv_path}")

    # ── Raw per-(seed, fraction) CSV ──
    raw_path = DATA_DIR / "partial_intercept_sweep_per_seed.csv"
    with open(raw_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "eavesdrop_fraction", "qber_measured",
                    "sift_ratio", "ml_p_attack", "ml_detection_rate"])
        for r in raw_rows:
            w.writerow([r[0], r[1], round(r[2], 6), round(r[3], 6),
                        round(r[4], 6), round(r[5], 6)])
    print(f"Wrote {raw_path}")

    # ── Figure 1: QBER vs fraction (mean +/- SD band) ──
    fig, ax = plt.subplots(figsize=(8, 5))
    fr = np.array(arr["eavesdrop_fraction"])
    qm = np.array(arr["qber_measured_mean"])
    qs = np.array(arr["qber_measured_std"])
    qt = np.array(arr["qber_theory"])

    ax.plot(fr, qm, "o-", color="#c0392b",
            label="Measured QBER (mean ±1 SD)")
    ax.fill_between(fr, qm - qs, qm + qs, color="#c0392b", alpha=0.18)
    ax.plot(fr, qt, "s--", color="#2c3e50",
            label="Theory: 0.01 + 0.25·fraction")
    ax.axhline(QBER_THRESHOLD, ls="--", color="black",
               label=f"Abort threshold ({QBER_THRESHOLD:.0%})")

    if window is not None:
        edge = window["max_eavesdrop_fraction_below_threshold"]
        ax.axvspan(0.0, edge, color="#f1c40f", alpha=0.18,
                   label=f"Sub-threshold window (≤{edge:.1f})")

    ax.set_xlabel("Eve's intercept fraction")
    ax.set_ylabel("QBER")
    ax.set_title(
        f"Sub-threshold exploit: QBER vs intercept fraction\n"
        f"{N_SEEDS} replicate batches x {TRIALS_PER_SEED} trials (band = ±1 SD)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p1 = FIG_DIR / "subthreshold_qber.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print(f"Wrote {p1}")

    # ── Figure 2: info gain + ML detection vs fraction (twin axes, SD band) ──
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ig = np.array(arr["eve_info_gain"])
    det = np.array(arr["ml_detection_rate_mean"])
    det_s = np.array(arr["ml_detection_rate_std"])

    c1 = "#8e44ad"
    ax1.plot(fr, ig, "o-", color=c1, label="Eve info gain (0.5·fraction)")
    ax1.set_xlabel("Eve's intercept fraction")
    ax1.set_ylabel("Eve info gain (fraction of sifted key known)", color=c1)
    ax1.tick_params(axis="y", labelcolor=c1)
    ax1.set_ylim(0, 0.55)

    ax2 = ax1.twinx()
    c2 = "#16a085"
    ax2.plot(fr, det, "s--", color=c2, label="ML detection rate (mean ±1 SD)")
    ax2.fill_between(fr, det - det_s, det + det_s, color=c2, alpha=0.18)
    ax2.set_ylabel("ML detection rate", color=c2)
    ax2.tick_params(axis="y", labelcolor=c2)
    ax2.set_ylim(0, 1.05)

    if window is not None:
        edge = window["max_eavesdrop_fraction_below_threshold"]
        ax1.axvspan(0.0, edge, color="#f1c40f", alpha=0.18)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="center right",
               fontsize=9)
    ax1.set_title(
        f"Eve's information gain vs ML detection rate\n"
        f"{N_SEEDS} replicate batches x {TRIALS_PER_SEED} trials (band = ±1 SD)")
    ax1.grid(alpha=0.3)
    fig.tight_layout()
    p2 = FIG_DIR / "subthreshold_info_gain.png"
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print(f"Wrote {p2}")


def main():
    per_fraction, raw_rows = run_sweep()
    window = find_window(per_fraction)
    write_outputs(per_fraction, raw_rows, window)

    print("\n" + "=" * 60)
    print(f"SUB-THRESHOLD EXPLOIT WINDOW  ({N_SEEDS} seeds, mean +/- SD)")
    print("=" * 60)
    if window is None:
        print("No positive intercept fraction stayed below 11% QBER.")
    else:
        print(f"Max intercept fraction under 11% QBER : "
              f"{window['max_eavesdrop_fraction_below_threshold']:.1f}")
        print(f"  Measured QBER at that fraction       : "
              f"{window['qber_at_window_edge']:.4f} +/- "
              f"{window['qber_std_at_window_edge']:.4f}")
        print(f"  Eve info gain there                  : "
              f"{window['eve_info_gain_at_window_edge']:.3f} "
              f"(~{window['eve_info_gain_at_window_edge']*100:.0f}% of sifted key)")
        print(f"  ML detection rate at that fraction   : "
              f"{window['ml_detection_rate_at_window_edge']:.2f} +/- "
              f"{window['ml_detection_std_at_window_edge']:.2f}")
        print(f"  ML detection (mean over window)      : "
              f"{window['ml_detection_rate_in_window_mean']:.2f}")
        print(f"  Static 11% policy detection in window: "
              f"{window['static_policy_detection_rate_in_window']:.2f}")


if __name__ == "__main__":
    main()
