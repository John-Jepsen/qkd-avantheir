"""
Adversarial Evaluation for QKD ML Models

Baseline evaluation script that measures evasion rates before and after
adversarial hardening. The proof-of-concept for the evolutionary gym.

Steps:
  1. Load trained eavesdrop + attack classifiers
  2. Generate correctly-classified test samples
  3. Apply bounded perturbations (constrained to QKD physics)
  4. Measure evasion rate (fraction of perturbed samples that fool the model)
  5. Retrain with adversarial samples mixed in
  6. Measure evasion rate again (should decrease)

Usage:
    .venv/bin/python adversarial_eval.py
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score

from features import extract_features, FEATURE_NAMES
from physics_constraints import clip_to_bounds, enforce_covariance, BOUNDS_LOW, BOUNDS_HIGH


def generate_perturbations(
    X: np.ndarray,
    epsilon: float = 0.1,
    rng: np.random.Generator = None,
) -> np.ndarray:
    """
    Apply bounded perturbations to feature vectors within physics constraints.

    Each feature is perturbed by a random amount in [-epsilon, +epsilon],
    scaled by the feature's range. Then covariance constraints are enforced.
    """
    if rng is None:
        rng = np.random.default_rng()

    feature_ranges = BOUNDS_HIGH - BOUNDS_LOW
    noise = rng.uniform(-epsilon, epsilon, size=X.shape) * feature_ranges
    perturbed = X + noise
    return enforce_covariance(perturbed)


def evaluate_evasion(
    model,
    X: np.ndarray,
    y_true: np.ndarray,
    epsilon: float = 0.1,
    n_trials: int = 5,
    rng: np.random.Generator = None,
) -> dict:
    """
    Measure evasion rate: fraction of correctly-classified samples that
    become misclassified after perturbation.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Find correctly classified samples
    y_pred = model.predict(X)
    correct_mask = y_pred == y_true
    X_correct = X[correct_mask]
    y_correct = y_true[correct_mask]

    if len(X_correct) == 0:
        return {"evasion_rate": 0.0, "n_correct": 0, "n_evaded": 0}

    # Run multiple perturbation trials and average
    total_evaded = 0
    total_tested = 0
    for _ in range(n_trials):
        X_perturbed = generate_perturbations(X_correct, epsilon, rng)
        y_perturbed = model.predict(X_perturbed)
        evaded = np.sum(y_perturbed != y_correct)
        total_evaded += evaded
        total_tested += len(X_correct)

    return {
        "evasion_rate": total_evaded / total_tested,
        "n_correct": int(np.sum(correct_mask)),
        "n_evaded": total_evaded,
        "n_tested": total_tested,
    }


def adversarial_retrain(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_adv: np.ndarray,
    y_adv: np.ndarray,
    mix_ratio: float = 0.3,
    rng: np.random.Generator = None,
) -> object:
    """
    Retrain model with adversarial samples mixed into training data.

    mix_ratio: fraction of training data that should be adversarial samples.
    Returns the retrained model (same type, new weights).
    """
    if rng is None:
        rng = np.random.default_rng()

    n_adv = int(len(X_train) * mix_ratio / (1 - mix_ratio))
    if n_adv > len(X_adv):
        n_adv = len(X_adv)

    indices = rng.choice(len(X_adv), size=n_adv, replace=n_adv > len(X_adv))
    X_augmented = np.vstack([X_train, X_adv[indices]])
    y_augmented = np.concatenate([y_train, y_adv[indices]])

    # Shuffle
    perm = rng.permutation(len(X_augmented))
    X_augmented = X_augmented[perm]
    y_augmented = y_augmented[perm]

    model.fit(X_augmented, y_augmented)
    return model


def run_eval():
    """Run the full adversarial evaluation pipeline."""
    from bb84_simulator import BB84Protocol
    from ml_eavesdrop_classifier import EavesdropClassifier
    import ml_eavesdrop_classifier

    rng = np.random.default_rng(42)

    # Use classical backend for speed
    orig = ml_eavesdrop_classifier.BB84Protocol
    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)

    ml_eavesdrop_classifier.BB84Protocol = FastProto

    print("=" * 60)
    print("ADVERSARIAL EVALUATION — Eavesdrop Classifier")
    print("=" * 60)

    # Train baseline
    print("\n1. Training baseline classifier (600 samples)...")
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=600, n_bits=1024)
    clf.train()
    ml_eavesdrop_classifier.BB84Protocol = orig

    X_test = clf.X_test
    y_test = clf.y_test
    X_train = clf.X_train
    y_train = clf.y_train

    # Baseline accuracy
    baseline_acc = accuracy_score(y_test, clf.model.predict(X_test))
    print(f"\n2. Baseline test accuracy: {baseline_acc:.1%}")

    # Evaluate evasion at different perturbation strengths
    print("\n3. Evasion rates at different perturbation strengths:")
    for eps in [0.05, 0.10, 0.15, 0.20, 0.30]:
        result = evaluate_evasion(clf.model, X_test, y_test, epsilon=eps, rng=rng)
        print(f"   epsilon={eps:.2f}: evasion={result['evasion_rate']:.1%} "
              f"({result['n_evaded']}/{result['n_tested']})")

    # Generate adversarial samples for hardening
    eps_harden = 0.15
    print(f"\n4. Generating adversarial samples (epsilon={eps_harden})...")
    X_adv = generate_perturbations(X_train, epsilon=eps_harden, rng=rng)
    y_adv = clf.model.predict(X_train)  # original labels

    # Retrain with adversarial augmentation
    print("5. Retraining with 30% adversarial augmentation...")
    hardened_model = RandomForestClassifier(
        n_estimators=100, max_depth=10, random_state=42
    )
    hardened_model.fit(X_train, y_train)  # start fresh
    adversarial_retrain(hardened_model, X_train, y_train, X_adv, y_adv,
                        mix_ratio=0.3, rng=rng)

    # Post-hardening accuracy
    hardened_acc = accuracy_score(y_test, hardened_model.predict(X_test))
    print(f"\n6. Post-hardening test accuracy: {hardened_acc:.1%}")

    # Post-hardening evasion
    print("\n7. Post-hardening evasion rates:")
    for eps in [0.05, 0.10, 0.15, 0.20, 0.30]:
        before = evaluate_evasion(clf.model, X_test, y_test, epsilon=eps, rng=rng)
        after = evaluate_evasion(hardened_model, X_test, y_test, epsilon=eps, rng=rng)
        delta = after["evasion_rate"] - before["evasion_rate"]
        print(f"   epsilon={eps:.2f}: {before['evasion_rate']:.1%} → "
              f"{after['evasion_rate']:.1%} ({delta:+.1%})")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Baseline accuracy:     {baseline_acc:.1%}")
    print(f"  Hardened accuracy:     {hardened_acc:.1%}")
    ev_before = evaluate_evasion(clf.model, X_test, y_test, epsilon=0.15, rng=rng)
    ev_after = evaluate_evasion(hardened_model, X_test, y_test, epsilon=0.15, rng=rng)
    print(f"  Evasion (eps=0.15):    {ev_before['evasion_rate']:.1%} → {ev_after['evasion_rate']:.1%}")
    print(f"  Hardening effective:   {'YES' if ev_after['evasion_rate'] < ev_before['evasion_rate'] else 'NO'}")


if __name__ == "__main__":
    run_eval()
