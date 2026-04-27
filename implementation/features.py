"""
Shared feature extraction for QKD ML models.

All classifiers (eavesdrop, attack, adversarial) use the same 8-feature
vector extracted from BB84Result objects. Single source of truth prevents
drift between models and simplifies the adversarial perturbation surface.

Features:
  0. qber              — Estimated quantum bit error rate
  1. sift_ratio        — Sifted bits / raw bits sent
  2. error_variance    — Variance of per-block error rates
  3. max_burst_length  — Longest consecutive error run
  4. low_block_fraction  — Fraction of blocks with zero errors
  5. high_block_fraction — Fraction of blocks with >50% errors
  6. error_autocorrelation — Correlation between consecutive block errors
  7. sift_deviation    — |sift_ratio - 0.5|
"""

import numpy as np


FEATURE_NAMES = [
    "qber",
    "sift_ratio",
    "error_variance",
    "max_burst_length",
    "low_block_fraction",
    "high_block_fraction",
    "error_autocorrelation",
    "sift_deviation",
]


def extract_features(result) -> list[float]:
    """Extract the 8-feature vector from a BB84Result."""
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

    return [qber, sift_ratio, error_variance, max_burst,
            low_frac, high_frac, autocorr, sift_deviation]
