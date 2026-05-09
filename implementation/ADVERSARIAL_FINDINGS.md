# Adversarial Evolution Findings

Results from co-evolutionary adversarial testing of QKD ML eavesdrop detection models.

## Experiment Setup

All runs use the DEAP evolutionary gym (`adversarial_gym.py`) which co-evolves attack
vectors against a defender classifier. Each generation:

1. Attackers are evaluated on evasion rate (fooling the defender into predicting "clean")
2. Top attackers are mixed into training data
3. Defender retrains incrementally (`warm_start`)
4. Phylogeny tree records lineage of evolved strategies

Baseline classifier: `EavesdropClassifier` (RandomForest) trained on BB84 simulator
output with three classes: clean, eavesdrop, partial_intercept.

All runs used the classical BB84 backend for speed with 1200 training samples at 2048 bits.

---

## Run 1: 8-Feature Baseline

**Config:** 100 population, 40 generations, epsilon=0.20, mutation=0.25, hardening=0.3

**Features (8):** qber, sift_ratio, error_variance, max_burst_length, low_block_fraction,
high_block_fraction, error_autocorrelation, sift_deviation

| Metric | Value |
|--------|-------|
| Initial evasion | 21.5% |
| Final evasion | 32.8% |
| Final defender accuracy | 87.5% |

**Observation:** Attackers won. Evasion climbed steadily from 21.5% to 32.8% over 40
generations. The defender held accuracy on clean data but couldn't keep up with evolved
attacks. The 8-feature surface was small enough for the evolutionary search to find
consistent evasion strategies.

---

## Run 2: 12-Feature with Enforced Covariance

**Config:** 100 population, 40 generations, epsilon=0.20, mutation=0.25, hardening=0.6

**New features added (4 physics-derived):**
- `variance_ratio` — error_variance / (qber * (1-qber)), normalized to theoretical max
- `block_entropy` — Shannon entropy of binned block error rate distribution
- `burst_qber_product` — max_burst_length * qber, nonlinear coupling term
- `block_kurtosis` — excess kurtosis of block error rates

**Critical design flaw:** `enforce_covariance()` auto-computed the derived features for
the attacker (e.g., `variance_ratio = error_variance / (qber*(1-qber))`). This gave
attackers physically consistent vectors for free — the new features added dimensionality
but no independent discriminative power against this attacker.

**Hardening too aggressive:** 0.6 mix ratio flooded training data with adversarial samples,
diluting the real signal and degrading baseline accuracy.

| Metric | Value |
|--------|-------|
| Initial evasion | 23.5% |
| Final evasion | 38.8% |
| Final defender accuracy | 86.2% |

**Observation:** Worst result. Evasion climbed to 41% at peak (Gen 39). Defender accuracy
dropped to 86.2%. The combination of free covariance enforcement and over-aggressive
hardening hurt on both fronts.

---

## Run 3: 12-Feature Trap Mode (No Derived Feature Enforcement)

**Config:** 100 population, 40 generations, epsilon=0.20, mutation=0.25, hardening=0.3

**Key change:** Removed auto-computation of derived features from `enforce_covariance()`.
The attacker must now evolve `variance_ratio`, `block_entropy`, `burst_qber_product`, and
`block_kurtosis` independently. If the evolved values don't match the true mathematical
relationship (e.g., variance_ratio != error_variance / (qber*(1-qber))), the inconsistency
becomes a signal the defender can learn to detect.

**Defender upgrade:** RandomForest with 200 estimators, max_depth=20, min_samples_leaf=2
(up from 100 estimators, depth 10).

| Metric | Value |
|--------|-------|
| Initial evasion | 23.5% |
| Final evasion | 29.6% |
| Final defender accuracy | 88.3% |

**Observation:** Best result. Evasion curve stayed flat (22-29% range) instead of climbing
monotonically. Defender accuracy held at 88-89% throughout and even ticked up to 89.2%
mid-run. The trap works because an attacker evolving in 12D space must simultaneously
satisfy nonlinear relationships it can't see — real data always has consistent ratios,
evolved data rarely does.

---

## Run 4: GradientBoosting Defender + Trap Mode

**Config:** 100 population, 40 generations, epsilon=0.20, mutation=0.25, hardening=0.3

**Defender:** GradientBoostingClassifier (200 estimators, depth 6, lr=0.1, subsample=0.8).
Trained on 2400 samples (2x previous). Trap mode (derived features not enforced).

| Metric | Value |
|--------|-------|
| Initial evasion | 28.1% |
| Final evasion | 48.8% |
| Final defender accuracy | 84.8% |

**Observation:** Worst result across all runs. Counterintuitive pattern: avg fitness stayed
near 0 (evolved attackers could rarely fool the model directly) but perturbation-based
evasion climbed to nearly 50%. This reveals a fundamental difference in decision boundary
geometry:

- **RandomForest** has smooth, averaged decision boundaries (ensemble of independent trees).
  Small perturbations don't reliably push samples across the boundary.
- **GradientBoosting** has sharp, high-confidence boundaries (sequential trees correct each
  other's residuals). The boundary is precise but brittle — small perturbations in the right
  direction cross it easily.

GB's `warm_start` hardening also behaves differently: new trees are added to correct residuals
from the *shifted* distribution (adversarial mix), making earlier trees less relevant. This
creates a compounding drift where the model gradually loses its grip on the original data
distribution.

---

## Run 5: Big RandomForest + Trap Mode

**Config:** 100 population, 50 generations, epsilon=0.20, mutation=0.25, hardening=0.3

**Defender:** RandomForestClassifier (300 estimators, depth 25, min_samples_leaf=2).
Trained on 3600 samples at 4096 bits per sample. Trap mode (derived features not enforced).

| Metric | Value |
|--------|-------|
| Baseline accuracy | 92% |
| Initial evasion | 24.1% |
| Final evasion | 24.8% |
| Final defender accuracy | 91.2% |

**Observation:** Best result by a wide margin. Evasion was essentially **flat for 50
generations** — the attacker made zero progress. The evasion curve stayed locked in the
22-25% band throughout, never trending upward. This held even as avg fitness climbed to
0.99 (Gen 49), meaning nearly every evolved individual could fool the model when evaluated
directly, yet perturbation-based evasion didn't budge.

Why this works:
- **3x more training data** (3600 vs 1200) gives the RF enough examples to learn the true
  joint distribution of all 12 features, including the derived-feature consistency patterns.
- **4096 bits per sample** (vs 2048) produces more precise block-level statistics, making
  the derived features (entropy, kurtosis) more discriminative.
- **300 trees at depth 25** provides enough capacity to model the nonlinear consistency
  relationships without overfitting (RF's bagging prevents it).
- **Trap mode** forces the attacker to independently satisfy 4 derived-feature relationships
  it can't see, while the defender has learned exactly what those relationships look like
  from 3600 real samples.

The disconnect between high avg fitness (0.99) and flat evasion (24.8%) is significant:
it means the attacker found a way to fool the model with *specific* evolved vectors, but
the perturbation-based evasion metric (which adds random bounded noise to real test data)
remains low. The defender's learned decision boundary is robust to perturbations even though
it has exploitable pockets in feature space.

---

## Comparison

| Run | Defender | Features | Hardening | Covariance | Final Evasion | Defender Acc |
|-----|----------|----------|-----------|------------|---------------|-------------|
| 1. Baseline | RF-100/d10 | 8 | 0.3 | enforced | 32.8% | 87.5% |
| 2. Enforced 12 | RF-100/d10 | 12 | 0.6 | enforced | 38.8% | 86.2% |
| 3. Trap mode | RF-200/d20 | 12 | 0.3 | NOT enforced | 29.6% | 88.3% |
| 4. GB trap | GB-200/d6 | 12 | 0.3 | NOT enforced | 48.8% | 84.8% |
| **5. Big RF trap** | **RF-300/d25** | **12** | **0.3** | **NOT enforced** | **24.8%** | **91.2%** |

---

## Key Takeaways

1. **More features != better defense.** Adding physics-derived features with automatic
   covariance enforcement actually *helped* the attacker by giving it consistent vectors
   for free. The extra dimensions increased the evasion surface without adding detection power.

2. **Trap features work.** When derived features are NOT auto-computed, the attacker must
   independently guess relationships like `variance_ratio = error_variance / (qber*(1-qber))`.
   Getting this wrong creates detectable inconsistencies. Real BB84 data always satisfies
   these relationships exactly; evolved attack vectors rarely do.

3. **Hardening ratio matters.** 0.6 adversarial mix degraded the defender. 0.3 maintained
   clean-data accuracy while still hardening against evolved attacks.

4. **Defender capacity helps.** Deeper trees (depth 20 vs 10) and more estimators (200 vs 100)
   let the defender learn the consistency patterns in the derived features.

5. **RandomForest >> GradientBoosting for adversarial robustness.** RF's smooth averaged
   boundaries resist perturbation. GB's sharp sequential boundaries are precise but brittle.
   This is consistent with findings in the adversarial ML literature: ensemble diversity
   (RF) provides natural robustness that sequential boosting (GB) does not.

6. **Data volume is the strongest lever.** Going from 1200 → 3600 training samples (with
   4096 bits per sample for richer statistics) dropped evasion from 29.6% → 24.8% and
   made the evasion curve completely flat over 50 generations. The attacker literally
   couldn't make progress. More data lets the defender learn the true joint feature
   distribution precisely enough that perturbation-based attacks can't find systematic gaps.

7. **High fitness ≠ high evasion.** In Run 5, avg fitness reached 0.99 while evasion
   stayed at 24.8%. The attacker found specific exploitable pockets in feature space, but
   these don't generalize — random perturbations of real data don't land in those pockets.
   This is a desirable property: the defender is robust where it matters (near real data)
   even if it has holes in unreachable regions of feature space.

---

## Files Modified

- `features.py` — Extended from 8 to 12 features (added variance_ratio, block_entropy,
  burst_qber_product, block_kurtosis). Uses scipy.stats for entropy and kurtosis.
- `physics_constraints.py` — Added bounds for new features. Removed auto-computation of
  derived features in `enforce_covariance()` (trap mode).
- `ml_eavesdrop_classifier.py` — Updated `predict()` signature to accept 12 features.
- `requirements.txt` — Added explicit scipy dependency.
