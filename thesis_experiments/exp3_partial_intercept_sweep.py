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
error_rate. For each fraction we run several trials and record:
  - mean measured QBER (from BB84Result.qber)
  - theoretical QBER prediction: base_error + 0.25 * fraction
  - mean sift ratio
  - Eve's information-gain estimate (proportional to intercept fraction)
  - the trained eavesdrop detector's mean P(attack) and detection rate,
    where P(attack) = 1 - P(clean) and "detected" = predicted label != "clean"

We then locate the sub-threshold exploit window: the largest eavesdrop_fraction
whose *measured* QBER stays below 0.11, and report the ML detector's detection
rate within that window against the static policy's rate (0% by definition,
since QBER < 0.11 there).

Outputs
-------
  thesis_data/partial_intercept_sweep.json
  thesis_data/partial_intercept_sweep.csv
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
REPO_ROOT = Path(__file__).resolve().parent.parent
IMPL_DIR = REPO_ROOT / "implementation"
sys.path.insert(0, str(IMPL_DIR))

from bb84_simulator import BB84Protocol            # noqa: E402
from features import extract_features              # noqa: E402
from ml_eavesdrop_classifier import EavesdropClassifier  # noqa: E402

DATA_DIR = REPO_ROOT / "thesis_data"
FIG_DIR = REPO_ROOT / "thesis_figures"
MODEL_PATH = IMPL_DIR / "data" / "eavesdrop_model.pkl"

# ── Experiment configuration ──────────────────────────────────────────────────
# n_bits=4096 raw qubits sift to ~2048 bits (well above the 40-bit floor) and
# each Qiskit run is a few tenths of a second. 20 trials x 11 fractions = 220
# runs; with the partial-intercept path running up to 3 circuits per run this
# stays under a few minutes total. Reduce N_TRIALS/N_BITS if slower.
N_BITS = 4096
N_TRIALS = 20
BASE_ERROR_RATE = 0.01
FRACTIONS = [round(0.1 * i, 1) for i in range(11)]  # 0.0 .. 1.0
QBER_THRESHOLD = 0.11
# Classic intercept-resend induces 25% QBER on intercepted, matched-basis qubits.
IR_QBER_PER_INTERCEPT = 0.25


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


def run_sweep():
    print(f"Loading eavesdrop detector: {MODEL_PATH}")
    clf = EavesdropClassifier.load(str(MODEL_PATH))

    rows = []
    per_fraction = {}

    for frac in FRACTIONS:
        eavesdrop = frac > 0.0
        qbers, sifts, p_attacks, detections = [], [], [], []

        for t in range(N_TRIALS):
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

        qber_measured = float(np.mean(qbers))
        qber_theory = BASE_ERROR_RATE + IR_QBER_PER_INTERCEPT * frac
        sift_ratio = float(np.mean(sifts))
        info_gain = eve_info_gain(frac)
        ml_p_attack = float(np.mean(p_attacks))
        ml_detection_rate = float(np.mean(detections))
        below_threshold = qber_measured < QBER_THRESHOLD

        per_fraction[frac] = {
            "eavesdrop_fraction": frac,
            "qber_measured": qber_measured,
            "qber_measured_std": float(np.std(qbers)),
            "qber_theory": qber_theory,
            "sift_ratio": sift_ratio,
            "eve_info_gain": info_gain,
            "ml_p_attack": ml_p_attack,
            "ml_detection_rate": ml_detection_rate,
            "below_threshold": below_threshold,
        }

        rows.append([
            frac, qber_measured, qber_theory, sift_ratio,
            info_gain, ml_detection_rate, below_threshold,
        ])

        print(
            f"frac={frac:.1f}  QBER_meas={qber_measured:.4f} "
            f"(theory={qber_theory:.4f})  sift={sift_ratio:.3f}  "
            f"info_gain={info_gain:.3f}  ML_det={ml_detection_rate:.2f}  "
            f"P(atk)={ml_p_attack:.2f}  below11%={below_threshold}"
        )

    return per_fraction, rows


def find_window(per_fraction):
    """Largest eavesdrop_fraction whose MEASURED QBER stays below 0.11 (frac>0)."""
    sub = [f for f, d in per_fraction.items()
           if f > 0.0 and d["below_threshold"]]
    if not sub:
        return None
    max_frac = max(sub)
    d = per_fraction[max_frac]
    return {
        "max_eavesdrop_fraction_below_threshold": max_frac,
        "qber_at_window_edge": d["qber_measured"],
        "eve_info_gain_at_window_edge": d["eve_info_gain"],
        "ml_detection_rate_at_window_edge": d["ml_detection_rate"],
        "ml_p_attack_at_window_edge": d["ml_p_attack"],
        # ML detection averaged across ALL positive-fraction sub-threshold points
        "ml_detection_rate_in_window_mean": float(np.mean([
            per_fraction[f]["ml_detection_rate"] for f in sub
        ])),
        "static_policy_detection_rate_in_window": 0.0,
        "sub_threshold_fractions": sorted(sub),
    }


def write_outputs(per_fraction, rows, window):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    fracs = sorted(per_fraction.keys())
    arr = {k: [per_fraction[f][k] for f in fracs] for k in [
        "eavesdrop_fraction", "qber_measured", "qber_measured_std",
        "qber_theory", "sift_ratio", "eve_info_gain",
        "ml_p_attack", "ml_detection_rate", "below_threshold",
    ]}

    # ── JSON ──
    json_path = DATA_DIR / "partial_intercept_sweep.json"
    with open(json_path, "w") as f:
        json.dump({
            "metadata": {
                "experiment": "exp3_partial_intercept_sweep",
                "description": (
                    "Partial intercept-resend sub-threshold exploit sweep: "
                    "measured vs theoretical QBER, Eve info gain, and ML "
                    "detector performance vs the static 11% policy."
                ),
                "n_bits": N_BITS,
                "trials_per_fraction": N_TRIALS,
                "base_error_rate": BASE_ERROR_RATE,
                "qber_threshold": QBER_THRESHOLD,
                "ir_qber_per_intercept": IR_QBER_PER_INTERCEPT,
                "fractions": FRACTIONS,
                "backend": "qiskit",
                "model_path": str(MODEL_PATH),
                "info_gain_definition": "0.5 * eavesdrop_fraction",
                "p_attack_definition": "1 - P(clean) from RF classifier",
                "detection_definition": "predicted label != clean",
            },
            "arrays": arr,
            "exploit_window": window,
        }, f, indent=2)
    print(f"Wrote {json_path}")

    # ── CSV ──
    csv_path = DATA_DIR / "partial_intercept_sweep.csv"
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "eavesdrop_fraction", "qber_measured", "qber_theory",
            "sift_ratio", "eve_info_gain", "ml_detection_rate",
            "below_threshold",
        ])
        for r in rows:
            w.writerow(r)
    print(f"Wrote {csv_path}")

    # ── Figure 1: QBER vs fraction ──
    fig, ax = plt.subplots(figsize=(8, 5))
    fr = np.array(arr["eavesdrop_fraction"])
    qm = np.array(arr["qber_measured"])
    qs = np.array(arr["qber_measured_std"])
    qt = np.array(arr["qber_theory"])

    ax.plot(fr, qm, "o-", color="#c0392b", label="Measured QBER (Qiskit)")
    ax.fill_between(fr, qm - qs, qm + qs, color="#c0392b", alpha=0.15)
    ax.plot(fr, qt, "s--", color="#2c3e50",
            label="Theory: 0.01 + 0.25·fraction")
    ax.axhline(QBER_THRESHOLD, ls="--", color="black",
               label=f"Abort threshold ({QBER_THRESHOLD:.0%})")

    # Shade the sub-threshold exploit window (positive fractions, QBER < 0.11).
    if window is not None:
        edge = window["max_eavesdrop_fraction_below_threshold"]
        ax.axvspan(0.0, edge, color="#f1c40f", alpha=0.18,
                   label=f"Sub-threshold window (≤{edge:.1f})")

    ax.set_xlabel("Eve's intercept fraction")
    ax.set_ylabel("QBER")
    ax.set_title("Sub-threshold exploit: QBER vs intercept fraction")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p1 = FIG_DIR / "subthreshold_qber.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)
    print(f"Wrote {p1}")

    # ── Figure 2: info gain + ML detection vs fraction (twin axes) ──
    fig, ax1 = plt.subplots(figsize=(8, 5))
    ig = np.array(arr["eve_info_gain"])
    det = np.array(arr["ml_detection_rate"])

    c1 = "#8e44ad"
    ax1.plot(fr, ig, "o-", color=c1, label="Eve info gain (0.5·fraction)")
    ax1.set_xlabel("Eve's intercept fraction")
    ax1.set_ylabel("Eve info gain (fraction of sifted key known)", color=c1)
    ax1.tick_params(axis="y", labelcolor=c1)
    ax1.set_ylim(0, 0.55)

    ax2 = ax1.twinx()
    c2 = "#16a085"
    ax2.plot(fr, det, "s--", color=c2, label="ML detection rate")
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
    ax1.set_title("Eve's information gain vs ML detection rate")
    ax1.grid(alpha=0.3)
    fig.tight_layout()
    p2 = FIG_DIR / "subthreshold_info_gain.png"
    fig.savefig(p2, dpi=150)
    plt.close(fig)
    print(f"Wrote {p2}")


def main():
    per_fraction, rows = run_sweep()
    window = find_window(per_fraction)
    write_outputs(per_fraction, rows, window)

    print("\n" + "=" * 60)
    print("SUB-THRESHOLD EXPLOIT WINDOW")
    print("=" * 60)
    if window is None:
        print("No positive intercept fraction stayed below 11% QBER.")
    else:
        print(f"Max intercept fraction under 11% QBER : "
              f"{window['max_eavesdrop_fraction_below_threshold']:.1f}")
        print(f"  Measured QBER at that fraction       : "
              f"{window['qber_at_window_edge']:.4f}")
        print(f"  Eve info gain there                  : "
              f"{window['eve_info_gain_at_window_edge']:.3f} "
              f"(~{window['eve_info_gain_at_window_edge']*100:.0f}% of sifted key)")
        print(f"  ML detection rate at that fraction   : "
              f"{window['ml_detection_rate_at_window_edge']:.2f}")
        print(f"  ML detection (mean over window)      : "
              f"{window['ml_detection_rate_in_window_mean']:.2f}")
        print(f"  Static 11% policy detection in window: "
              f"{window['static_policy_detection_rate_in_window']:.2f}")


if __name__ == "__main__":
    main()
