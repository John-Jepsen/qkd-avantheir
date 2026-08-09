#!/usr/bin/env python
"""Thesis Experiment 1: QBER x block-size secure-key-rate sweep for BB84.

Sweeps QBER from 0 to 0.15 (step 0.0025) and computes, via the qkdsec
proofs package (numerical Devetak-Winter SDP, which reproduces the
Shor-Preskill rate for BB84 over a depolarizing channel):

  (a) the asymptotic key rate  r = 1 - H2(Q) - f_ec * H2(Q)
      (f_ec = 1.0 gives the ideal Shor-Preskill rate 1 - 2*H2(Q);
       f_ec = 1.16 is the qkdsec package default, modelling realistic
       Cascade/LDPC reconciliation leakage — both are recorded), and

  (b) the finite-key rate for block sizes n in {1e4 ... 1e9} using the
      Tomamichel et al. finite-size penalty exactly as implemented in
      qkdsec.proofs.finite_size.tomamichel_correction and applied in
      qkdsec.proofs._api.key_rate:

          r_finite = max(0, r_asym - yield * 7*sqrt(log2(2/eps)/n_det))

      with n_det = int(yield * n_signals) and yield = 1.0 for
      DepolarizingChannel.

For each (f_ec, regime) it also locates the zero-rate QBER boundary —
the largest QBER with a strictly positive certified rate — by bisection
to 1e-6, and reports its gap below the canonical 11% threshold.

qkdsec functions used
---------------------
  qkdsec.proofs.key_rate(protocol, channel, n_signals=..., eps_security=...)
  qkdsec.proofs.BB84(f_ec=...)
  qkdsec.proofs.DepolarizingChannel(qber=...)
  qkdsec.proofs.finite_size.tomamichel_correction(n_detected, eps_security)

The finite-size arithmetic below replicates key_rate()'s own penalty
subtraction (qkdsec/src/qkdsec/proofs/_api.py, lines 35-44) so the
expensive SDP is solved once per (QBER, f_ec) and reused across the six
block sizes; equivalence is asserted against direct
key_rate(n_signals=...) calls at several checkpoints before the sweep.

Outputs
-------
  thesis_data/keyrate_sweep.csv        (long form: qber, n_signals, key_rate, f_ec)
  thesis_data/keyrate_boundaries.json  (boundaries + full metadata)
  thesis_figures/keyrate_boundary.png

Run:  implementation/.venv/bin/python thesis/thesis_experiments/exp1_keyrate_sweep.py
"""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

THESIS_DIR = Path(__file__).resolve().parents[1]  # thesis/
REPO = THESIS_DIR.parent  # repo root (holds qkdsec/ submodule, implementation/)
# qkdsec is a git submodule with a src layout and is not pip-installed in
# this venv; from the repo root the bare submodule directory would shadow
# it as an empty namespace package, so put qkdsec/src first on sys.path.
sys.path.insert(0, str(REPO / "qkdsec" / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from qkdsec.proofs import BB84, DepolarizingChannel, key_rate  # noqa: E402
from qkdsec.proofs.finite_size import tomamichel_correction  # noqa: E402

DATA_DIR = THESIS_DIR / "thesis_data"
FIG_DIR = THESIS_DIR / "thesis_figures"

EPS_SECURITY = 1e-10  # qkdsec key_rate() default
SOLVER = "CLARABEL"  # qkdsec key_rate() default
QBER_STEP = 0.0025
QBER_MAX = 0.15
BLOCK_SIZES = [10**4, 10**5, 10**6, 10**7, 10**8, 10**9]
F_ECS = [1.0, 1.16]  # ideal reconciliation / qkdsec package default
BISECT_TOL = 1e-6
SP_THRESHOLD = 0.11  # canonical asymptotic Shor-Preskill abort threshold

_OK_STATUSES = ("optimal", "optimal_inaccurate")
_asym_cache: dict[tuple[float, float], float] = {}
_solve_count = 0


def asym_rate(qber: float, f_ec: float) -> float:
    """Asymptotic certified rate from the qkdsec SDP (cached)."""
    global _solve_count
    key = (round(qber, 12), f_ec)
    if key not in _asym_cache:
        res = key_rate(
            BB84(f_ec=f_ec), DepolarizingChannel(qber=qber), solver=SOLVER
        )
        _asym_cache[key] = res.r_lower if res.sdp_status in _OK_STATUSES else 0.0
        _solve_count += 1
    return _asym_cache[key]


def finite_rate(qber: float, n_signals: int, f_ec: float) -> float:
    """Finite-key rate, replicating qkdsec.proofs._api.key_rate exactly.

    DepolarizingChannel has total_yield() == 1.0, so n_detected == n_signals
    and the Tomamichel penalty is subtracted at full weight.
    """
    r = asym_rate(qber, f_ec)
    if r <= 0.0:
        return 0.0
    n_detected = int(1.0 * n_signals)
    penalty = tomamichel_correction(n_detected, EPS_SECURITY)
    return max(0.0, r - 1.0 * penalty)


def bisect_boundary(rate_fn, lo: float, hi: float, tol: float = BISECT_TOL) -> float:
    """Largest QBER with a positive rate, given rate_fn(lo) > 0 >= rate_fn(hi)."""
    assert rate_fn(lo) > 0.0, "lower bracket must have positive rate"
    assert rate_fn(hi) <= 0.0, "upper bracket must have zero rate"
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if rate_fn(mid) > 0.0:
            lo = mid
        else:
            hi = mid
    return lo


def qkdsec_version() -> str:
    try:
        import tomllib

        with open(REPO / "qkdsec" / "pyproject.toml", "rb") as fh:
            return tomllib.load(fh)["project"]["version"]
    except Exception:
        return "unknown"


def qkdsec_git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(REPO / "qkdsec"), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def main() -> None:
    t0 = time.time()
    n_steps = round(QBER_MAX / QBER_STEP)
    qbers = [round(i * QBER_STEP, 6) for i in range(n_steps + 1)]

    # --- Cross-check: fast path == qkdsec.key_rate(n_signals=...) ----------
    for q, n in [(0.01, 10**4), (0.05, 10**6), (0.09, 10**9), (0.05, 10**5)]:
        direct = key_rate(
            BB84(f_ec=1.16), DepolarizingChannel(qber=q),
            n_signals=n, eps_security=EPS_SECURITY,
        ).r_lower
        fast = finite_rate(q, n, 1.16)
        assert abs(direct - fast) < 1e-9, (q, n, direct, fast)
    print("cross-check vs key_rate(n_signals=...) passed")

    # --- Sweep --------------------------------------------------------------
    rows: list[tuple[float, str, float, float]] = []
    curves: dict[tuple[float, str], list[float]] = {}
    for f_ec in F_ECS:
        for label, fn in [("asymptotic", lambda q, fe=f_ec: asym_rate(q, fe))] + [
            (str(n), lambda q, n=n, fe=f_ec: finite_rate(q, n, fe))
            for n in BLOCK_SIZES
        ]:
            curves[(f_ec, label)] = [fn(q) for q in qbers]
            rows.extend(
                (q, label, r, f_ec)
                for q, r in zip(qbers, curves[(f_ec, label)])
            )
        print(f"sweep f_ec={f_ec} done ({time.time() - t0:.0f}s, "
              f"{_solve_count} SDP solves)")

    DATA_DIR.mkdir(exist_ok=True)
    FIG_DIR.mkdir(exist_ok=True)

    csv_path = DATA_DIR / "keyrate_sweep.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qber", "n_signals", "key_rate", "f_ec"])
        w.writerows(rows)
    print(f"wrote {csv_path} ({len(rows)} rows)")

    # --- Zero-rate boundaries (fine bisection) ------------------------------
    boundaries: dict[str, dict[str, dict]] = {}
    for f_ec in F_ECS:
        per_fec: dict[str, dict] = {}
        specs = [("asymptotic", lambda q, fe=f_ec: asym_rate(q, fe))] + [
            (str(n), lambda q, n=n, fe=f_ec: finite_rate(q, n, fe))
            for n in BLOCK_SIZES
        ]
        for label, fn in specs:
            b = bisect_boundary(fn, 0.0, QBER_MAX)
            per_fec[label] = {
                "zero_rate_qber_boundary": round(b, 7),
                "gap_from_0.11_abs": round(SP_THRESHOLD - b, 7),
                "gap_from_0.11_pct": round((SP_THRESHOLD - b) / SP_THRESHOLD * 100, 3),
            }
            print(f"f_ec={f_ec} {label:>10}: boundary QBER = {b:.5f} "
                  f"(gap below 11%: {SP_THRESHOLD - b:+.5f})")
        boundaries[f"f_ec={f_ec}"] = per_fec

    meta = {
        "experiment": "exp1_keyrate_sweep",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "qkdsec_version": qkdsec_version(),
        "qkdsec_git_sha": qkdsec_git_sha(),
        "python": sys.version.split()[0],
        "functions_used": [
            "qkdsec.proofs.key_rate (Devetak-Winter SDP; reproduces "
            "Shor-Preskill 1-2*H2(Q) for BB84 at f_ec=1)",
            "qkdsec.proofs.BB84(f_ec)",
            "qkdsec.proofs.DepolarizingChannel(qber)",
            "qkdsec.proofs.finite_size.tomamichel_correction(n_detected, "
            "eps_security)",
        ],
        "finite_size_formula": (
            "r_finite = max(0, r_asym - yield * 7*sqrt(log2(2/eps)/n_detected)); "
            "n_detected = int(yield * n_signals); yield = 1.0 for "
            "DepolarizingChannel (replicates qkdsec.proofs._api.key_rate)"
        ),
        "eps_security": EPS_SECURITY,
        "solver": SOLVER,
        "f_ec_values": F_ECS,
        "f_ec_note": "1.0 = ideal (Shannon-limit) reconciliation; 1.16 = "
                     "qkdsec package default (realistic Cascade/LDPC)",
        "block_sizes": BLOCK_SIZES,
        "qber_sweep": {"start": 0.0, "stop": QBER_MAX, "step": QBER_STEP},
        "bisection_tolerance": BISECT_TOL,
        "reference_threshold": SP_THRESHOLD,
        "caveats": [
            "SDP uses CVXPY quantum_rel_entr Pade approximation (2,2); "
            "r_lower is a numerical, not formally verified, lower bound "
            "(per qkdsec.proofs.sdp docstring).",
            "Boundary = largest QBER at which the certified rate is "
            "strictly positive, to within the bisection tolerance.",
        ],
    }
    json_path = DATA_DIR / "keyrate_boundaries.json"
    with open(json_path, "w") as fh:
        json.dump({"metadata": meta, "boundaries": boundaries}, fh, indent=2)
    print(f"wrote {json_path}")

    # --- Task deliverables: keyrate_sweep.{json,csv} -------------------------
    # Canonical exp1 outputs requested by the thesis harness. These use the
    # package-default reconciliation (f_ec = 1.16, the "practical" regime the
    # figure emphasises) and the five block sizes 1e4..1e8, with the wide CSV
    # column layout (qber, r_asymptotic, r_n1e4 ... r_n1e8) and a per-regime
    # {qber, rate} array plus a summary giving the zero-crossing QBER and its
    # gap below the canonical 11% threshold.
    F_EC_MAIN = 1.16
    MAIN_BLOCKS = [10**4, 10**5, 10**6, 10**7, 10**8]

    def _label(n: int) -> str:
        return f"n1e{int(math.log10(n))}"

    main_regimes = [("asymptotic", "asymptotic")] + [
        (str(n), _label(n)) for n in MAIN_BLOCKS
    ]

    def _crossing(rate_list: list[float]) -> float | None:
        # Linear interpolation between the last strictly-positive point and the
        # first non-positive point on the QBER grid.
        for i in range(1, len(rate_list)):
            rp, rc = rate_list[i - 1], rate_list[i]
            if rp > 0.0 and rc <= 0.0:
                qp, qc = qbers[i - 1], qbers[i]
                if rp == rc:
                    return round(qc, 7)
                return round(qp + (rp / (rp - rc)) * (qc - qp), 7)
        return None

    sweep_curves: dict[str, list[dict]] = {}
    sweep_summary: dict[str, dict] = {}
    for curve_label, out_key in main_regimes:
        rates_here = curves[(F_EC_MAIN, curve_label)]
        sweep_curves[out_key] = [
            {"qber": q, "rate": r} for q, r in zip(qbers, rates_here)
        ]
        cross = _crossing(rates_here)
        sweep_summary[out_key] = {
            "zero_crossing_qber": cross,
            "gap_below_11pct": (
                None if cross is None else round(SP_THRESHOLD - cross, 7)
            ),
        }

    sweep_meta = {
        "experiment": "exp1_keyrate_sweep",
        "generated_utc": meta["generated_utc"],
        "qkdsec_version": meta["qkdsec_version"],
        "qkdsec_git_sha": meta["qkdsec_git_sha"],
        "eps_security": EPS_SECURITY,
        "f_ec": F_EC_MAIN,
        "solver": SOLVER,
        "protocol": "BB84",
        "channel": "DepolarizingChannel",
        "canonical_qber_threshold": SP_THRESHOLD,
        "qber_grid": {"start": 0.0, "stop": QBER_MAX, "step": QBER_STEP,
                      "n_points": len(qbers)},
        "block_sizes": MAIN_BLOCKS,
        "functions_used": meta["functions_used"],
        "finite_size_formula": meta["finite_size_formula"],
        "note": (
            "asymptotic = Tomamichel n->inf limit (Devetak-Winter SDP rate at "
            "f_ec=1.16); rN = same rate minus the Tomamichel finite-size "
            "penalty at block size N. See keyrate_boundaries.json for the "
            "f_ec=1.0 ideal-Shor-Preskill comparison and 1e9 block."
        ),
    }
    sweep_json = DATA_DIR / "keyrate_sweep.json"
    with open(sweep_json, "w") as fh:
        json.dump(
            {"metadata": sweep_meta, "curves": sweep_curves,
             "summary": sweep_summary},
            fh, indent=2,
        )
    print(f"wrote {sweep_json}")

    sweep_csv = DATA_DIR / "keyrate_sweep.csv"
    with open(sweep_csv, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["qber", "r_asymptotic", "r_n1e4", "r_n1e5", "r_n1e6",
                    "r_n1e7", "r_n1e8"])
        col_labels = ["asymptotic"] + [str(n) for n in MAIN_BLOCKS]
        for i, q in enumerate(qbers):
            w.writerow(
                [q] + [curves[(F_EC_MAIN, cl)][i] for cl in col_labels]
            )
    print(f"wrote {sweep_csv}")

    print("\nexp1 zero-crossing summary (f_ec=1.16):")
    print(json.dumps(sweep_summary, indent=2))

    # --- Figure --------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 6))
    colors = plt.cm.viridis(np.linspace(0.0, 0.85, len(BLOCK_SIZES)))

    # Practical (f_ec = 1.16, package default) finite-key curves.
    for color, n in zip(colors, BLOCK_SIZES):
        label = str(n)
        ax.plot(qbers, curves[(1.16, label)], color=color, lw=1.8,
                label=f"finite key, $n = 10^{{{int(math.log10(n))}}}$")
        b = boundaries["f_ec=1.16"][label]["zero_rate_qber_boundary"]
        ax.plot(b, 0.0, "o", color=color, ms=6, zorder=5)

    ax.plot(qbers, curves[(1.16, "asymptotic")], color="black", lw=2.2,
            label=r"asymptotic ($f_{EC}=1.16$)")
    b_asym = boundaries["f_ec=1.16"]["asymptotic"]["zero_rate_qber_boundary"]
    ax.plot(b_asym, 0.0, "o", color="black", ms=6, zorder=5)

    ax.plot(qbers, curves[(1.0, "asymptotic")], color="gray", lw=1.6, ls="--",
            label=r"ideal Shor-Preskill $1-2H_2(Q)$ ($f_{EC}=1$)")

    ax.axvline(SP_THRESHOLD, color="crimson", ls="--", lw=1.4)
    ax.text(SP_THRESHOLD + 0.0015, 0.62, "canonical 11%\nabort threshold",
            color="crimson", fontsize=9)

    ax.set_xlabel("QBER  $Q$")
    ax.set_ylabel("secure key rate  (bits per detected signal)")
    ax.set_title("BB84 secure key rate vs QBER: finite-size (Tomamichel) "
                 "boundaries below the 11% threshold\n"
                 f"qkdsec Devetak-Winter SDP, $f_{{EC}}=1.16$, "
                 f"$\\varepsilon_{{sec}}=10^{{{int(math.log10(EPS_SECURITY))}}}$"
                 " (dots mark zero-rate boundaries)",
                 fontsize=11)
    ax.set_xlim(0.0, QBER_MAX)
    ax.set_ylim(-0.02, 1.02)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()

    fig_path = FIG_DIR / "keyrate_boundary.png"
    fig.savefig(fig_path, dpi=200)
    print(f"wrote {fig_path}")
    print(f"total: {time.time() - t0:.0f}s, {_solve_count} SDP solves")


if __name__ == "__main__":
    main()
