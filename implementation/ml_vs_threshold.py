"""
ML vs Threshold Comparison Sweep

Systematically compares the ML eavesdrop classifier's false negative rate
against the simple 11% QBER threshold across all attack types and parameter
ranges. Answers: does the ML classifier ever produce a WORSE security outcome
than the threshold it replaced?

Usage:
    .venv/bin/python ml_vs_threshold.py
"""

import numpy as np
from bb84_simulator import BB84Protocol
from ml_eavesdrop_classifier import EavesdropClassifier
from ml_attack_classifier import (
    simulate_beam_splitting,
    simulate_pns_attack,
    simulate_trojan_horse,
    _extract_features,
)


QBER_THRESHOLD = 0.11


def run_sweep():
    # Train classifier on fresh data
    print("Training eavesdrop classifier on 3000 samples...")
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=3000, n_bits=4096)
    clf.train()

    rng = np.random.default_rng(42)
    n_trials = 50
    n_bits = 4096

    results = {}

    # --- Full intercept-resend ---
    print("\n=== Full Intercept-Resend ===")
    ml_detect = 0
    threshold_detect = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.03)
        r = BB84Protocol(error_rate=noise, eavesdrop=True).run(n_bits=n_bits)
        det = clf.predict_from_result(r)
        if det.predicted_label != "clean":
            ml_detect += 1
        if r.qber > QBER_THRESHOLD:
            threshold_detect += 1
    results["intercept_resend"] = {
        "ml_detect_rate": ml_detect / n_trials,
        "threshold_detect_rate": threshold_detect / n_trials,
    }
    print(f"  ML detect rate:        {ml_detect}/{n_trials} ({ml_detect/n_trials:.0%})")
    print(f"  Threshold detect rate: {threshold_detect}/{n_trials} ({threshold_detect/n_trials:.0%})")

    # --- Partial intercept (10-50%) ---
    print("\n=== Partial Intercept (10-50%) ===")
    ml_detect = 0
    threshold_detect = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.03)
        fraction = rng.uniform(0.10, 0.50)
        r = BB84Protocol(
            error_rate=noise, eavesdrop=True, eavesdrop_fraction=fraction
        ).run(n_bits=n_bits)
        det = clf.predict_from_result(r)
        if det.predicted_label != "clean":
            ml_detect += 1
        if r.qber > QBER_THRESHOLD:
            threshold_detect += 1
    results["partial_intercept"] = {
        "ml_detect_rate": ml_detect / n_trials,
        "threshold_detect_rate": threshold_detect / n_trials,
    }
    print(f"  ML detect rate:        {ml_detect}/{n_trials} ({ml_detect/n_trials:.0%})")
    print(f"  Threshold detect rate: {threshold_detect}/{n_trials} ({threshold_detect/n_trials:.0%})")

    # --- Beam-splitting ---
    print("\n=== Beam-Splitting ===")
    ml_detect = 0
    threshold_detect = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.03)
        tap = rng.uniform(0.05, 0.25)
        sim = simulate_beam_splitting(n_bits, noise, tap, rng)
        det = clf.predict(
            qber=sim["features"][0],
            sift_ratio=sim["features"][1],
            error_variance=sim["features"][2],
            max_burst=int(sim["features"][3]),
        )
        if det.predicted_label != "clean":
            ml_detect += 1
        if sim["features"][0] > QBER_THRESHOLD:
            threshold_detect += 1
    results["beam_splitting"] = {
        "ml_detect_rate": ml_detect / n_trials,
        "threshold_detect_rate": threshold_detect / n_trials,
    }
    print(f"  ML detect rate:        {ml_detect}/{n_trials} ({ml_detect/n_trials:.0%})")
    print(f"  Threshold detect rate: {threshold_detect}/{n_trials} ({threshold_detect/n_trials:.0%})")

    # --- PNS Attack ---
    print("\n=== PNS Attack ===")
    ml_detect = 0
    threshold_detect = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.03)
        block_frac = rng.uniform(0.15, 0.45)
        sim = simulate_pns_attack(n_bits, noise, block_frac, rng)
        det = clf.predict(
            qber=sim["features"][0],
            sift_ratio=sim["features"][1],
            error_variance=sim["features"][2],
            max_burst=int(sim["features"][3]),
        )
        if det.predicted_label != "clean":
            ml_detect += 1
        if sim["features"][0] > QBER_THRESHOLD:
            threshold_detect += 1
    results["pns_attack"] = {
        "ml_detect_rate": ml_detect / n_trials,
        "threshold_detect_rate": threshold_detect / n_trials,
    }
    print(f"  ML detect rate:        {ml_detect}/{n_trials} ({ml_detect/n_trials:.0%})")
    print(f"  Threshold detect rate: {threshold_detect}/{n_trials} ({threshold_detect/n_trials:.0%})")

    # --- Trojan Horse ---
    print("\n=== Trojan Horse ===")
    ml_detect = 0
    threshold_detect = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.03)
        strength = rng.uniform(0.02, 0.08)
        sim = simulate_trojan_horse(n_bits, noise, strength, rng)
        det = clf.predict(
            qber=sim["features"][0],
            sift_ratio=sim["features"][1],
            error_variance=sim["features"][2],
            max_burst=int(sim["features"][3]),
        )
        if det.predicted_label != "clean":
            ml_detect += 1
        if sim["features"][0] > QBER_THRESHOLD:
            threshold_detect += 1
    results["trojan_horse"] = {
        "ml_detect_rate": ml_detect / n_trials,
        "threshold_detect_rate": threshold_detect / n_trials,
    }
    print(f"  ML detect rate:        {ml_detect}/{n_trials} ({ml_detect/n_trials:.0%})")
    print(f"  Threshold detect rate: {threshold_detect}/{n_trials} ({threshold_detect/n_trials:.0%})")

    # --- Clean channel (false positive check) ---
    print("\n=== Clean Channel (False Positive Check) ===")
    ml_fp = 0
    threshold_fp = 0
    for _ in range(n_trials):
        noise = rng.uniform(0.005, 0.05)
        r = BB84Protocol(error_rate=noise, eavesdrop=False).run(n_bits=n_bits)
        det = clf.predict_from_result(r)
        if det.predicted_label != "clean":
            ml_fp += 1
        if r.qber > QBER_THRESHOLD:
            threshold_fp += 1
    results["clean"] = {
        "ml_fp_rate": ml_fp / n_trials,
        "threshold_fp_rate": threshold_fp / n_trials,
    }
    print(f"  ML false positive rate:        {ml_fp}/{n_trials} ({ml_fp/n_trials:.0%})")
    print(f"  Threshold false positive rate:  {threshold_fp}/{n_trials} ({threshold_fp/n_trials:.0%})")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY: ML vs 11% QBER Threshold")
    print("=" * 70)
    print(f"{'Attack Type':<25} {'ML Detect':>12} {'Threshold':>12} {'ML Advantage':>14}")
    print("-" * 70)
    for attack in ["intercept_resend", "partial_intercept", "beam_splitting",
                    "pns_attack", "trojan_horse"]:
        ml = results[attack]["ml_detect_rate"]
        th = results[attack]["threshold_detect_rate"]
        advantage = ml - th
        marker = "  ML WINS" if advantage > 0 else ("  THRESHOLD WINS" if advantage < 0 else "  TIE")
        print(f"  {attack:<23} {ml:>10.0%}   {th:>10.0%}   {advantage:>+10.0%}{marker}")

    ml_fp = results["clean"]["ml_fp_rate"]
    th_fp = results["clean"]["threshold_fp_rate"]
    print(f"  {'clean (FP rate)':<23} {ml_fp:>10.0%}   {th_fp:>10.0%}")
    print("-" * 70)

    # Verdict
    ml_worse = any(
        results[a]["ml_detect_rate"] < results[a]["threshold_detect_rate"]
        for a in ["intercept_resend", "partial_intercept", "beam_splitting",
                   "pns_attack", "trojan_horse"]
    )
    if ml_worse:
        print("VERDICT: ML classifier has blind spots where the threshold does better.")
        print("         The adversarial benchmark should target these gaps.")
    else:
        print("VERDICT: ML classifier matches or exceeds the threshold on all attacks.")
        print("         Adversarial testing can focus on finding novel evasion strategies.")


if __name__ == "__main__":
    run_sweep()
