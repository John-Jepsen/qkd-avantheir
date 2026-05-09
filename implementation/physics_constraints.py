"""
QKD Physics Constraints for Adversarial Perturbation

Defines physically plausible bounds for each feature in the 8-feature vector.
The adversarial gym uses these to constrain perturbations so that generated
attack vectors remain physically realizable on a real quantum channel.

Key insight: QKD features are not independent. QBER, sift_ratio, error_variance,
and burst length are correlated by the physics of the BB84 protocol and the
specific attack being simulated. Perturbations must respect these covariance
constraints, not just per-feature min/max bounds.
"""

import numpy as np
from features import FEATURE_NAMES


# Per-feature bounds derived from BB84 channel physics.
# These represent the physically realizable range for each feature.
FEATURE_BOUNDS = {
    "qber":                  (0.0,   0.50),   # 0% to 50% error rate
    "sift_ratio":            (0.10,  0.55),   # ~50% from basis matching, losses can reduce
    "error_variance":        (0.0,   0.25),   # variance of per-block error rates
    "max_burst_length":      (0.0,   20.0),   # longest consecutive error run
    "low_block_fraction":    (0.0,   1.0),    # fraction of blocks with 0 errors
    "high_block_fraction":   (0.0,   1.0),    # fraction of blocks with >50% errors
    "error_autocorrelation": (-1.0,  1.0),    # correlation coefficient
    "sift_deviation":        (0.0,   0.40),   # |sift_ratio - 0.5|
    "variance_ratio":        (0.0,   1.0),    # error_var / (qber*(1-qber)), bounded by binomial
    "block_entropy":         (0.0,   3.0),    # Shannon entropy of binned block errors (~ln(10))
    "burst_qber_product":    (0.0,   10.0),   # max_burst * qber
    "block_kurtosis":        (-3.0,  10.0),   # excess kurtosis (bimodal → neg, heavy-tail → pos)
}

# Bounds as numpy arrays for fast vectorized operations
BOUNDS_LOW = np.array([FEATURE_BOUNDS[f][0] for f in FEATURE_NAMES])
BOUNDS_HIGH = np.array([FEATURE_BOUNDS[f][1] for f in FEATURE_NAMES])


def clip_to_bounds(features: np.ndarray) -> np.ndarray:
    """Clip a feature vector (or batch) to physically plausible bounds."""
    return np.clip(features, BOUNDS_LOW, BOUNDS_HIGH)


def validate_features(features: np.ndarray) -> tuple[bool, list[str]]:
    """
    Check whether a feature vector satisfies physics constraints.

    Returns (is_valid, list_of_violations).
    """
    if features.ndim == 1:
        features = features.reshape(1, -1)

    violations = []

    for i, row in enumerate(features):
        prefix = f"[{i}] " if len(features) > 1 else ""

        # Per-feature bounds
        for j, name in enumerate(FEATURE_NAMES):
            lo, hi = FEATURE_BOUNDS[name]
            if row[j] < lo or row[j] > hi:
                violations.append(
                    f"{prefix}{name}={row[j]:.4f} outside [{lo}, {hi}]"
                )

        qber = row[0]
        sift_ratio = row[1]
        error_variance = row[2]
        low_frac = row[4]
        high_frac = row[5]
        sift_dev = row[7]

        # Covariance: sift_deviation must match sift_ratio
        expected_dev = abs(sift_ratio - 0.5)
        if abs(sift_dev - expected_dev) > 0.05:
            violations.append(
                f"{prefix}sift_deviation={sift_dev:.4f} inconsistent with "
                f"sift_ratio={sift_ratio:.4f} (expected ~{expected_dev:.4f})"
            )

        # Covariance: high QBER implies low_block_fraction can't be 1.0
        if qber > 0.10 and low_frac > 0.90:
            violations.append(
                f"{prefix}qber={qber:.4f} but low_block_fraction={low_frac:.4f} "
                f"(impossible: high error rate means some blocks have errors)"
            )

        # Covariance: low QBER implies high_block_fraction should be near 0
        if qber < 0.05 and high_frac > 0.30:
            violations.append(
                f"{prefix}qber={qber:.4f} but high_block_fraction={high_frac:.4f} "
                f"(unlikely: low overall error but many blocks >50% error)"
            )

        # Covariance: error_variance can't exceed qber * (1 - qber)
        max_variance = qber * (1 - qber)
        if error_variance > max_variance + 0.01:
            violations.append(
                f"{prefix}error_variance={error_variance:.4f} exceeds "
                f"theoretical max={max_variance:.4f} for qber={qber:.4f}"
            )

        # Block fractions must sum to <= 1
        if low_frac + high_frac > 1.01:
            violations.append(
                f"{prefix}low_block_fraction + high_block_fraction = "
                f"{low_frac + high_frac:.4f} > 1.0"
            )

    return len(violations) == 0, violations


def enforce_covariance(features: np.ndarray) -> np.ndarray:
    """
    Adjust features to satisfy covariance constraints after perturbation.

    Clips to bounds first, then fixes inconsistencies between features.
    """
    result = clip_to_bounds(features.copy())

    if result.ndim == 1:
        result = result.reshape(1, -1)
        squeeze = True
    else:
        squeeze = False

    for i in range(len(result)):
        qber = result[i, 0]
        sift_ratio = result[i, 1]

        # Fix sift_deviation to match sift_ratio
        result[i, 7] = abs(sift_ratio - 0.5)

        # Cap error_variance at theoretical maximum
        max_var = qber * (1 - qber)
        result[i, 2] = min(result[i, 2], max_var)

        # Fix block fractions: if they sum > 1, scale down proportionally
        low_frac = result[i, 4]
        high_frac = result[i, 5]
        total = low_frac + high_frac
        if total > 1.0:
            result[i, 4] = low_frac / total
            result[i, 5] = high_frac / total

        # High QBER can't have all-zero blocks
        if qber > 0.10:
            result[i, 4] = min(result[i, 4], 1.0 - qber)

        # Low QBER shouldn't have many high-error blocks
        if qber < 0.05:
            result[i, 5] = min(result[i, 5], qber * 3)

        # ── Derived features are NOT auto-computed ──────────────────────────
        # The attacker must evolve variance_ratio, block_entropy,
        # burst_qber_product, and block_kurtosis independently. If it gets
        # them wrong, the inconsistency between the derived value and the
        # true relationship (e.g., variance_ratio != error_variance/(qber*(1-qber)))
        # becomes a signal the defender can learn to detect.
        # Only apply basic bound clamping — no relationship enforcement.

    if squeeze:
        result = result.squeeze(0)
    return result


def random_within_bounds(n_samples: int = 1, rng: np.random.Generator = None) -> np.ndarray:
    """Generate random feature vectors within physics bounds (but NOT covariance-enforced)."""
    if rng is None:
        rng = np.random.default_rng()
    raw = rng.uniform(BOUNDS_LOW, BOUNDS_HIGH, size=(n_samples, len(FEATURE_NAMES)))
    return enforce_covariance(raw)
