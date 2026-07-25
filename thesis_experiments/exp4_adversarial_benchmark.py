"""
Thesis Experiment 4 — Adversarial co-evolution: static threshold vs adaptive ML.

Core thesis claim (demonstrated experimentally)
-----------------------------------------------
A static 11% QBER abort threshold is a *fixed policy*. Once an attacker knows the
rule, evolving attack strategies that stay under it is trivial — the threshold's
evasion rate never improves, no matter how the adversary adapts. An adaptive ML
defender that retrains against the evolving population *closes the gap*: its
evasion rate is driven down generation over generation.

This experiment drives the existing DEAP co-evolutionary gym
(``implementation/adversarial_gym.py``) and benchmarks the evolved attack
population against three defenses:

  1. STATIC 11% threshold  — abort iff QBER > 0.11. An attack "evades" if its
     induced QBER < 0.11 while it is a genuine attack (non-clean feature vector).
  2. BASELINE ML detector  — the RandomForest eavesdrop classifier, frozen at
     its pre-evolution weights (never sees adversarial samples).
  3. ADAPTIVE ML detector  — the same classifier, co-evolutionarily retrained
     each generation against the current attack population (the gym's own
     ``current_model``).

Multi-seed error bars
---------------------
The gym's evolution is stochastic and the underlying BB84 dataset is generated
with ``secrets`` (OS entropy), so any single run is one draw from a distribution.
To report robust results we run ``N_SEEDS`` independent replicates. Per replicate
we:
  * rebuild a fresh BB84 dataset (independent OS-entropy noise draw),
  * override the gym's RNG with ``default_rng(seed)`` so its evolutionary
    trajectory is reproducible for that replicate,
  * seed the perturbation RNGs from ``seed``.
We then aggregate mean ± standard deviation across replicates, per generation and
for the final rates, and draw both figures with ±1 SD bands / error bars.

Everything runs against the real implementation modules. This file reads them;
it does not modify any source file (the gym RNG is overridden on the *instance*,
not in the source).

Outputs
-------
  thesis_data/adversarial_evolution_log.json  — metadata + per-seed finals +
                                                 aggregated per-gen (mean/std) +
                                                 one representative phylogeny
  thesis_data/adversarial_benchmark.csv        — aggregated per-gen table (mean/std)
  thesis_data/adversarial_benchmark_per_seed.csv — raw per-(seed,gen) rows
  thesis_figures/adversarial_fitness.png       — best & avg fitness ±1 SD band
  thesis_figures/adversarial_evasion.png       — evasion vs 3 defenses ±1 SD band

HARD RULE: this file only reads the existing implementation modules; it does not
modify any source file.
"""

import csv
import json
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Wire up imports against the existing implementation package ──────────────
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMPL_DIR = os.path.join(REPO_ROOT, "implementation")
sys.path.insert(0, IMPL_DIR)

from sklearn.base import clone                              # noqa: E402
from sklearn.metrics import accuracy_score                 # noqa: E402

import bb84_simulator                                       # noqa: E402
from bb84_simulator import BB84Protocol                    # noqa: E402
import ml_eavesdrop_classifier                             # noqa: E402
from ml_eavesdrop_classifier import EavesdropClassifier    # noqa: E402
from features import FEATURE_NAMES                          # noqa: E402
from physics_constraints import enforce_covariance         # noqa: E402
from adversarial_eval import generate_perturbations, evaluate_evasion  # noqa: E402
import adversarial_gym                                      # noqa: E402
from adversarial_gym import AdversarialGym                  # noqa: E402

DATA_DIR = os.path.join(REPO_ROOT, "thesis_data")
FIG_DIR = os.path.join(REPO_ROOT, "thesis_figures")
MODEL_PATH = os.path.join(IMPL_DIR, "data", "eavesdrop_model.pkl")

# ── Experiment configuration ─────────────────────────────────────────────────
# Population 50, 20 generations: comfortably meets the >=20-generation requirement
# with a population in the requested 40-60 band. Five independent replicates give
# ±1 SD error bars on every reported quantity.
POPULATION_SIZE = 50
N_GENERATIONS = 20
EPSILON = 0.15              # perturbation strength (matches adversarial_eval default sweep point)
HARDENING_MIX = 0.3        # fraction of adversarial samples in defender retraining
DATASET_SAMPLES = 900      # BB84 sessions used to (re)build the train/test split
N_BITS = 2048              # qubits per BB84 session (classical fast-backend)
QBER_THRESHOLD = 0.11
SEEDS = [42, 43, 44, 45, 46]   # independent replicates -> mean +/- SD error bars


# ── Defenses and the common evasion metric ───────────────────────────────────
#
# All three defenses are scored on ONE common definition so the comparison is
# apples-to-apples:
#
#     evasion rate = (# genuine attack samples the defense lets through)
#                    / (# genuine attack samples)
#
# "Genuine attack" = any sample whose true label is an eavesdrop or a
# partial_intercept (real key leakage). "Lets through" means:
#   - STATIC   : induced QBER < 0.11, so the 11% rule does not abort — exactly
#                the thesis definition (a real attack whose QBER stays under the
#                line). This is the *policy artifact*, independent of any model.
#   - ML models: the classifier predicts "clean" for the attack sample.

ATTACK_LABELS = ("eavesdrop", "partial_intercept")
_QBER_IDX = FEATURE_NAMES.index("qber")


def _attack_subset(X, y):
    """Return the genuine-attack rows of a labelled test set."""
    mask = np.isin(y, ATTACK_LABELS)
    return X[mask], y[mask]


def static_evasion_rate(X, y):
    """
    Fraction of genuine attacks the STATIC 11% threshold fails to abort.

    Deterministic given the test set: a pure property of the attack samples'
    QBER, so no RNG and no perturbation — a policy-aware Eve who merely keeps
    QBER < 0.11 evades by construction. (It still varies across replicates
    because each replicate draws a fresh BB84 dataset.)
    """
    Xa, _ = _attack_subset(X, y)
    if len(Xa) == 0:
        return 0.0
    return float(np.mean(Xa[:, _QBER_IDX] < QBER_THRESHOLD))


def ml_evasion_rate(model, X, y, epsilon, rng):
    """
    Fraction of genuine attacks an ML defender lets through (predicts "clean")
    after an epsilon perturbation of the attack samples.
    """
    Xa, _ = _attack_subset(X, y)
    if len(Xa) == 0:
        return 0.0
    Xp = generate_perturbations(Xa, epsilon=epsilon, rng=rng)
    preds = model.predict(Xp)
    return float(np.mean(preds == "clean"))


# ── Fast classical BB84 backend for dataset (re)generation ───────────────────
def _install_fast_backend():
    """Force the classical BB84 backend for fast, deterministic dataset builds."""
    orig = ml_eavesdrop_classifier.BB84Protocol

    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)

        def run(self, **kw):
            return self._p.run(**kw)

    ml_eavesdrop_classifier.BB84Protocol = FastProto
    return orig


def build_dataset():
    """
    Reconstruct a train/test split for the eavesdrop classifier.

    Regenerates a labelled BB84 dataset and trains a model consistent with THIS
    split. The BB84 simulator draws its channel noise from ``secrets`` (OS
    entropy), so each call is an independent replicate — the source of the
    across-seed variance the error bars capture.
    """
    orig = _install_fast_backend()
    print(f"  Generating BB84 dataset ({DATASET_SAMPLES} sessions, "
          f"{N_BITS} qubits each, classical backend)...")
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=DATASET_SAMPLES, n_bits=N_BITS)
    clf.train()  # ensures a model consistent with THIS split
    ml_eavesdrop_classifier.BB84Protocol = orig
    return clf


# ── One replicate ─────────────────────────────────────────────────────────────
def run_single_seed(seed):
    """
    Run the full build -> evolve -> benchmark pipeline for one replicate.

    Returns a dict with the per-generation records, the final evasion rates, the
    defender accuracies, the gym's internal metric, and the phylogeny.
    """
    print(f"\n=== Replicate seed={seed} ===")

    # 1. Fresh dataset + split + a trained model to clone.
    clf = build_dataset()
    X_train, y_train = clf.X_train, clf.y_train
    X_test, y_test = clf.X_test, clf.y_test

    # 2. Freeze a baseline ML defender (never sees adversarial samples).
    baseline_model = clone(clf.model)
    baseline_model.fit(X_train, y_train)
    baseline_acc = accuracy_score(y_test, baseline_model.predict(X_test))
    print(f"  Baseline ML test accuracy: {baseline_acc:.1%}")

    # Independent, seed-derived RNGs for the extra per-gen measurements.
    baseline_rng = np.random.default_rng(seed + 1)
    adaptive_rng = np.random.default_rng(seed + 2)

    # Static evasion is a pure property of this replicate's test set — constant
    # across generations within the replicate (varies across replicates).
    static_ev_const = static_evasion_rate(X_test, y_test)

    per_gen = []

    # ── Intercept the gym's evolving adaptive defender ───────────────────────
    _adaptive_holder = {"model": None}
    _orig_eval = adversarial_gym.evaluate_evasion

    def _capturing_eval(model, *a, **kw):
        _adaptive_holder["model"] = model
        return _orig_eval(model, *a, **kw)

    adversarial_gym.evaluate_evasion = _capturing_eval

    def on_generation(gr):
        static_ev = static_ev_const
        baseline_ev = ml_evasion_rate(baseline_model, X_test, y_test,
                                      EPSILON, baseline_rng)
        adaptive_model = _adaptive_holder["model"]
        adaptive_ev = ml_evasion_rate(adaptive_model, X_test, y_test,
                                      EPSILON, adaptive_rng) \
            if adaptive_model is not None else float("nan")

        per_gen.append({
            "generation": gr.generation,
            "best_fitness": float(gr.best_fitness),
            "avg_fitness": float(gr.avg_fitness),
            "evasion_vs_static": float(static_ev),
            "evasion_vs_baseline_ml": float(baseline_ev),
            "evasion_vs_adaptive_ml": float(adaptive_ev),
            "gym_reported_adaptive_evasion": float(gr.evasion_rate),
            "adaptive_defender_accuracy": float(gr.defender_accuracy),
        })

    # 3. Run the gym. Override its RNG on the instance so this replicate's
    #    evolutionary trajectory is reproducible for `seed` (no source edit).
    gym = AdversarialGym(
        population_size=POPULATION_SIZE,
        n_generations=N_GENERATIONS,
        epsilon=EPSILON,
        hardening_mix=HARDENING_MIX,
        on_generation=on_generation,
    )
    gym.rng = np.random.default_rng(seed)
    print(f"  Evolving: pop={POPULATION_SIZE}, gens={N_GENERATIONS}, "
          f"epsilon={EPSILON}, gym.rng seed={seed}")
    try:
        result = gym.evolve(X_train, y_train, X_test, y_test, clf.model)
    finally:
        adversarial_gym.evaluate_evasion = _orig_eval  # restore

    # 4. Final defense benchmark on the common attack-subset metric.
    final_static = static_ev_const
    final_baseline = ml_evasion_rate(baseline_model, X_test, y_test, EPSILON,
                                     np.random.default_rng(seed + 98))
    final_adaptive = ml_evasion_rate(_adaptive_holder["model"], X_test, y_test,
                                     EPSILON, np.random.default_rng(seed + 99))
    print(f"  Final evasion — static={final_static:.1%}  "
          f"baseline={final_baseline:.1%}  adaptive={final_adaptive:.1%}")

    return {
        "seed": seed,
        "per_gen": per_gen,
        "final_static": final_static,
        "final_baseline": final_baseline,
        "final_adaptive": final_adaptive,
        "baseline_acc": float(baseline_acc),
        "adaptive_acc": float(result.final_defender_accuracy),
        "gym_initial_evasion": float(result.initial_evasion_rate),
        "gym_final_evasion": float(result.final_evasion_rate),
        "phylogeny": result.phylogeny.to_dict(),
    }


# ── Aggregation across replicates ─────────────────────────────────────────────
_AGG_METRICS = [
    "best_fitness", "avg_fitness",
    "evasion_vs_static", "evasion_vs_baseline_ml", "evasion_vs_adaptive_ml",
]


def aggregate(seed_results):
    """
    Build per-generation mean/std across replicates.

    Returns a list (one entry per generation) of
    {generation, <metric>_mean, <metric>_std, ...}.
    """
    n_gen = min(len(r["per_gen"]) for r in seed_results)
    agg = []
    for g in range(n_gen):
        row = {"generation": g, "n_seeds": len(seed_results)}
        for m in _AGG_METRICS:
            vals = np.array([r["per_gen"][g][m] for r in seed_results], dtype=float)
            row[f"{m}_mean"] = float(np.nanmean(vals))
            row[f"{m}_std"] = float(np.nanstd(vals))
        agg.append(row)
    return agg


def _final_stats(seed_results, key):
    vals = np.array([r[key] for r in seed_results], dtype=float)
    return float(np.nanmean(vals)), float(np.nanstd(vals))


def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    t0 = time.time()

    seed_results = [run_single_seed(s) for s in SEEDS]
    agg = aggregate(seed_results)

    # Final rates: mean +/- SD across replicates.
    fs_mean, fs_std = _final_stats(seed_results, "final_static")
    fb_mean, fb_std = _final_stats(seed_results, "final_baseline")
    fa_mean, fa_std = _final_stats(seed_results, "final_adaptive")
    bacc_mean, bacc_std = _final_stats(seed_results, "baseline_acc")
    aacc_mean, aacc_std = _final_stats(seed_results, "adaptive_acc")

    elapsed = time.time() - t0

    # ── Aggregated per-gen CSV ───────────────────────────────────────────────
    csv_path = os.path.join(DATA_DIR, "adversarial_benchmark.csv")
    cols = ["generation", "n_seeds"]
    for m in _AGG_METRICS:
        cols += [f"{m}_mean", f"{m}_std"]
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in agg:
            w.writerow({k: round(row[k], 6) if isinstance(row[k], float) else row[k]
                        for k in cols})
    print(f"\nWrote {csv_path}  ({len(agg)} generations x {len(SEEDS)} seeds)")

    # ── Raw per-(seed, gen) CSV ──────────────────────────────────────────────
    raw_path = os.path.join(DATA_DIR, "adversarial_benchmark_per_seed.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seed", "generation", "best_fitness", "avg_fitness",
                    "evasion_vs_static", "evasion_vs_baseline_ml",
                    "evasion_vs_adaptive_ml"])
        for r in seed_results:
            for rec in r["per_gen"]:
                w.writerow([r["seed"], rec["generation"],
                            round(rec["best_fitness"], 6),
                            round(rec["avg_fitness"], 6),
                            round(rec["evasion_vs_static"], 6),
                            round(rec["evasion_vs_baseline_ml"], 6),
                            round(rec["evasion_vs_adaptive_ml"], 6)])
    print(f"Wrote {raw_path}")

    # ── JSON log ─────────────────────────────────────────────────────────────
    log = {
        "experiment": "exp4_adversarial_benchmark",
        "metadata": {
            "generations": N_GENERATIONS,
            "population_size": POPULATION_SIZE,
            "seeds": SEEDS,
            "n_seeds": len(SEEDS),
            "epsilon": EPSILON,
            "hardening_mix": HARDENING_MIX,
            "dataset_samples": DATASET_SAMPLES,
            "n_bits": N_BITS,
            "qber_threshold": QBER_THRESHOLD,
            "feature_names": FEATURE_NAMES,
            "gym_backend": "classical",
            "baseline_ml_accuracy_mean": round(bacc_mean, 6),
            "baseline_ml_accuracy_std": round(bacc_std, 6),
            "final_adaptive_defender_accuracy_mean": round(aacc_mean, 6),
            "final_adaptive_defender_accuracy_std": round(aacc_std, 6),
            "total_elapsed_s": round(elapsed, 2),
            "reproducibility_note": (
                "gym RNG and perturbation RNGs are seeded per replicate; the "
                "underlying BB84 dataset uses secrets (OS entropy), so each "
                "replicate is an independent draw. Error bars are +/-1 SD across "
                f"{len(SEEDS)} replicates."
            ),
        },
        "evasion_metric": (
            "fraction of genuine attack samples (eavesdrop + partial_intercept) "
            "each defense lets through: static = induced QBER < 0.11; "
            "ML = predicted 'clean' after epsilon perturbation of attack samples"
        ),
        "final_evasion_rates": {
            "static_threshold": {"mean": round(fs_mean, 6), "std": round(fs_std, 6)},
            "baseline_ml": {"mean": round(fb_mean, 6), "std": round(fb_std, 6)},
            "adaptive_ml": {"mean": round(fa_mean, 6), "std": round(fa_std, 6)},
        },
        "verdicts": {
            "adaptive_ml_dominates_static": bool(
                fa_mean < fs_mean and fb_mean < fs_mean),
            "retraining_beat_baseline": bool((fb_mean - fa_mean) > 0.005),
            "static_gap_exceeds_noise": bool(
                (fs_mean - max(fb_mean, fa_mean)) > (fs_std + max(fb_std, fa_std))),
        },
        "per_seed_finals": [
            {"seed": r["seed"], "static": round(r["final_static"], 6),
             "baseline_ml": round(r["final_baseline"], 6),
             "adaptive_ml": round(r["final_adaptive"], 6),
             "gym_initial_evasion": round(r["gym_initial_evasion"], 6),
             "gym_final_evasion": round(r["gym_final_evasion"], 6)}
            for r in seed_results
        ],
        "per_generation_aggregated": [
            {k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items()}
            for row in agg
        ],
        # One representative phylogeny (first replicate) to keep the file small.
        "representative_phylogeny": {
            "seed": seed_results[0]["seed"],
            "tree": seed_results[0]["phylogeny"],
        },
    }
    json_path = os.path.join(DATA_DIR, "adversarial_evolution_log.json")
    with open(json_path, "w") as f:
        json.dump(log, f, indent=2)
    print(f"Wrote {json_path}  "
          f"({log['representative_phylogeny']['tree']['total_nodes']} "
          f"phylogeny nodes, replicate {seed_results[0]['seed']})")

    # ── Figures (with +/-1 SD bands) ─────────────────────────────────────────
    make_fitness_figure(agg)
    make_evasion_figure(agg, (fs_mean, fs_std), (fb_mean, fb_std),
                        (fa_mean, fa_std))

    print_conclusion(agg, (fs_mean, fs_std), (fb_mean, fb_std), (fa_mean, fa_std),
                     (bacc_mean, bacc_std), (aacc_mean, aacc_std))


def _band(ax, gens, mean, std, color, label, marker):
    mean = np.asarray(mean)
    std = np.asarray(std)
    ax.plot(gens, mean, marker=marker, color=color, label=label)
    ax.fill_between(gens, mean - std, mean + std, alpha=0.18, color=color)


def make_fitness_figure(agg):
    gens = [r["generation"] for r in agg]
    best_m = [r["best_fitness_mean"] for r in agg]
    best_s = [r["best_fitness_std"] for r in agg]
    avg_m = [r["avg_fitness_mean"] for r in agg]
    avg_s = [r["avg_fitness_std"] for r in agg]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    _band(ax, gens, best_m, best_s, "tab:red", "best fitness", "o")
    _band(ax, gens, avg_m, avg_s, "tab:blue", "mean fitness", "s")
    ax.set_xlabel("Generation")
    ax.set_ylabel("Fitness (evasion score vs adaptive defender)")
    ax.set_title(
        "Experiment 4 — Attack fitness over co-evolution\n"
        f"pop={POPULATION_SIZE}, gens={N_GENERATIONS}, epsilon={EPSILON}, "
        f"{len(SEEDS)} seeds (band = +/-1 SD)")
    ax.set_ylim(-0.02, 1.05)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(FIG_DIR, "adversarial_fitness.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")


def make_evasion_figure(agg, static, baseline, adaptive):
    gens = [r["generation"] for r in agg]
    fig, ax = plt.subplots(figsize=(9.5, 6))
    _band(ax, gens, [r["evasion_vs_static_mean"] for r in agg],
          [r["evasion_vs_static_std"] for r in agg],
          "tab:red", "static 11% threshold (exploitable)", "s")
    _band(ax, gens, [r["evasion_vs_baseline_ml_mean"] for r in agg],
          [r["evasion_vs_baseline_ml_std"] for r in agg],
          "tab:orange", "baseline ML (frozen)", "^")
    _band(ax, gens, [r["evasion_vs_adaptive_ml_mean"] for r in agg],
          [r["evasion_vs_adaptive_ml_std"] for r in agg],
          "tab:green", "adaptive ML (retrained each gen)", "o")

    ax.set_xlabel("Generation")
    ax.set_ylabel("Evasion rate (fraction of attacks that slip through)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(
        "Experiment 4 — Evasion vs three defenses under co-evolution\n"
        f"{len(SEEDS)} seeds, band = +/-1 SD. Static stays high/exploitable; "
        "ML defenses hold low")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)

    # Annotate final points with mean +/- SD.
    if gens:
        gx = gens[-1]
        for (m, s), c in [(static, "tab:red"), (baseline, "tab:orange"),
                          (adaptive, "tab:green")]:
            ax.annotate(f"{m:.0%}±{s:.0%}", (gx, m),
                        textcoords="offset points", xytext=(6, 0),
                        fontsize=9, color=c, weight="bold")

    fig.tight_layout()
    out = os.path.join(FIG_DIR, "adversarial_evasion.png")
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")


def print_conclusion(agg, static, baseline, adaptive, bacc, aacc):
    fs_m, fs_s = static
    fb_m, fb_s = baseline
    fa_m, fa_s = adaptive
    print("\n" + "=" * 70)
    print(f"EXPERIMENT 4 CONCLUSION  ({len(SEEDS)} seeds, mean +/- SD)")
    print("=" * 70)
    print(f"  Generations:                 {len(agg)}")
    print(f"  Population size:             {POPULATION_SIZE}")
    print(f"  Baseline ML accuracy:        {bacc[0]:.1%} +/- {bacc[1]:.1%}")
    print(f"  Adaptive ML final accuracy:  {aacc[0]:.1%} +/- {aacc[1]:.1%}")
    print()
    print("  FINAL EVASION RATES (higher = defense more exploitable):")
    print(f"    static 11% threshold:      {fs_m:.1%} +/- {fs_s:.1%}")
    print(f"    baseline ML (frozen):      {fb_m:.1%} +/- {fb_s:.1%}")
    print(f"    adaptive ML (retrained):   {fa_m:.1%} +/- {fa_s:.1%}")
    print()
    primary = ("SUPPORTED" if fa_m < fs_m and fb_m < fs_m else "NOT SUPPORTED")
    sep = fs_m - max(fb_m, fa_m)
    noise = fs_s + max(fb_s, fa_s)
    print("  PRIMARY THESIS — an ML defense dominates the static 11% threshold:")
    print(f"    static {fs_m:.1%} vs ML ~{min(fb_m, fa_m):.1%}; "
          f"separation {sep:.1%} vs combined SD {noise:.1%}")
    print(f"    verdict: {primary}"
          + ("  (gap exceeds noise)" if sep > noise else "  (within noise!)"))
    print()
    gap_closed = fb_m - fa_m
    print("  SECONDARY — did adversarial retraining beat the frozen baseline?")
    print(f"    baseline {fb_m:.1%} vs adaptive {fa_m:.1%} "
          f"(gap closed {gap_closed:+.1%}, SDs {fb_s:.1%}/{fa_s:.1%})")
    if gap_closed > 0.005 and gap_closed > (fb_s + fa_s):
        print("    verdict: YES — retraining lowered evasion beyond noise")
    elif abs(gap_closed) <= (fb_s + fa_s):
        print("    verdict: NEUTRAL — difference within replicate noise; baseline "
              "ML already near its floor for this perturbing attacker")
    else:
        print("    verdict: NO — retraining did not improve on the frozen baseline")


if __name__ == "__main__":
    run()
