"""
Shared feature extraction for QKD ML models.

All classifiers (eavesdrop, attack, adversarial) use the same 12-feature
vector extracted from BB84Result objects. Single source of truth prevents
drift between models and simplifies the adversarial perturbation surface.

Features 0-7 are directly measured; features 8-11 are physics-derived
quantities that encode nonlinear relationships between observables. These
derived features are hard to fake independently because they are constrained
by quantum channel physics.

Features:
  0. qber              — Estimated quantum bit error rate
  1. sift_ratio        — Sifted bits / raw bits sent
  2. error_variance    — Variance of per-block error rates
  3. max_burst_length  — Longest consecutive error run
  4. low_block_fraction  — Fraction of blocks with zero errors
  5. high_block_fraction — Fraction of blocks with >50% errors
  6. error_autocorrelation — Correlation between consecutive block errors
  7. sift_deviation    — |sift_ratio - 0.5|
  8. variance_ratio    — error_variance / (qber*(1-qber)), normalized variance
  9. block_entropy     — Shannon entropy of block error rate distribution
 10. burst_qber_product — max_burst_length * qber, burst-error coupling
 11. block_kurtosis    — Excess kurtosis of block error rates
"""

import numpy as np
from scipy.stats import entropy as shannon_entropy, kurtosis


FEATURE_NAMES = [
    "qber",
    "sift_ratio",
    "error_variance",
    "max_burst_length",
    "low_block_fraction",
    "high_block_fraction",
    "error_autocorrelation",
    "sift_deviation",
    "variance_ratio",
    "block_entropy",
    "burst_qber_product",
    "block_kurtosis",
]


def extract_features(result) -> list[float]:
    """Extract the 12-feature vector from a BB84Result."""
    block_rates = result.block_error_rates or []

    qber = result.qber
    sift_ratio = result.sift_ratio
    error_variance = result.error_variance
    max_burst = float(result.max_burst_length)

    if block_rates:
        low_frac = sum(1 for r in block_rates if r == 0.0) / len(block_rates)
        high_frac = sum(1 for r in block_rates if r > 0.5) / len(block_rates)

        if len(block_rates) > 2:
            br = np.array(block_rates)
            if br.std() > 1e-10:
                corr_val = np.corrcoef(br[:-1], br[1:])[0, 1]
                autocorr = float(corr_val) if np.isfinite(corr_val) else 0.0
            else:
                autocorr = 0.0
        else:
            autocorr = 0.0
    else:
        low_frac = 1.0
        high_frac = 0.0
        autocorr = 0.0

    sift_deviation = abs(sift_ratio - 0.5)

    # ── Physics-derived features ───────────────────────────────────────────
    # Variance ratio: how close observed variance is to theoretical max.
    # Clean channels have characteristic ratios; faked low-QBER with unusual
    # variance gets exposed because this ratio is constrained by binomial stats.
    max_var = qber * (1 - qber)
    variance_ratio = error_variance / max_var if max_var > 1e-10 else 0.0

    # Block entropy: Shannon entropy of binned block error rates.
    # Natural noise → unimodal → higher entropy.
    # Eavesdropper intercept-resend → bimodal → lower entropy.
    if len(block_rates) > 2:
        br = np.array(block_rates)
        hist, _ = np.histogram(br, bins=10, range=(0.0, 0.5), density=False)
        hist = hist + 1e-10  # avoid log(0)
        block_ent = float(shannon_entropy(hist))
    else:
        block_ent = 0.0

    # Burst-QBER product: nonlinear coupling between burst length and error
    # rate. In real physics these are correlated — an attacker can't set them
    # independently without violating the joint distribution.
    burst_qber_prod = max_burst * qber

    # Block kurtosis: excess kurtosis of block error rate distribution.
    # Gaussian noise → ~0. Eavesdropper bimodal → negative kurtosis.
    # Heavy-tailed partial intercept → positive kurtosis.
    if len(block_rates) > 3:
        br = np.array(block_rates)
        block_kurt = float(kurtosis(br, fisher=True))
        if not np.isfinite(block_kurt):
            block_kurt = 0.0
    else:
        block_kurt = 0.0

    return [qber, sift_ratio, error_variance, max_burst,
            low_frac, high_frac, autocorr, sift_deviation,
            variance_ratio, block_ent, burst_qber_prod, block_kurt]
