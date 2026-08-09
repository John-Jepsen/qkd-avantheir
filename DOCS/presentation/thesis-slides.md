---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 26px; }
  h1 { font-size: 44px; }
  h2 { font-size: 34px; }
  table { font-size: 20px; }
  code { font-size: 20px; }
---

<!-- _paginate: false -->

# Learned vs. Fixed Decision Boundaries for Eavesdrop Detection in QKD

## An adversarially-robust machine-learning reappraisal of the 11% QBER rule

**John Jepsen — MSCS (Machine Learning)**

<!-- Front page — not counted toward the 5–15 slide budget -->

---

## The 11% rule is a classifier — the simplest one possible

Every QKD deployment runs a detector: *measure QBER; if it exceeds 11%, abort.*

Stated as machine learning, that rule is a **univariate decision stump**:

| Component | The 11% rule |
|---|---|
| Features | **one** (QBER) |
| Decision boundary | a hand-set constant (0.11) |
| Training | none |
| Calibration | none |
| Operating point | one fixed threshold |
| Adaptation to adversary | none |

**This is an ML thesis.** QKD is the testbed, the data-generating process, and
the source of ground-truth labels — not the subject.

---

## The machine-learning question

> Does a **trained, multivariate classifier** dominate a hand-set single-feature
> threshold — and does the advantage survive an **adaptive adversary**?

Four questions, each measured end-to-end on a working stack:

1. **Calibration** — where is the true class boundary, and how far off is 11%?
2. **Cost** — what does the stump's fixed operating point cost?
3. **Representation** — do richer features recover attacks the stump accepts?
4. **Robustness** — does the learned detector hold when the attacker adapts?

---

## Method — an ML harness on a QKD testbed

| ML role | Component |
|---|---|
| Ground-truth labels | `qkdsec` key-rate package (Devetak–Winter SDP) |
| Data-generating process | BB84 simulator on Qiskit Aer + tunable eavesdropper |
| Learned detector | Random Forest on a **12-feature** vector |
| Adversarial-training harness | DEAP co-evolutionary attacker/defender gym |

- Both classifiers see **identical runs** through **identical feature extraction** —
  the only difference is how many features each may use.
- Two experiments reported as **means over 5 seeds, ±1 SD** — variance-controlled.

---

## Result 1 — the hand-set boundary is *miscalibrated*

True zero-rate QBER boundary (ε = 10⁻¹⁰):

| Regime | f_ec = 1.00 (ideal) | f_ec = 1.16 (practical) |
|---|---|---|
| Asymptotic | 11.00% | **9.81%** |
| n = 10⁶ | 10.33% | **9.23%** |
| n = 10⁴ | 5.21% | 4.70% |

- **11% is recovered only in the ideal asymptotic case** — validating the pipeline.
- With realistic reconciliation the true boundary is **9.81%**, and 9.23% at 10⁶ signals.
- The stump's boundary is **offset by 1–6 points of QBER — always toward accepting insecure runs.**

---

## Result 2 — the cost of the fixed operating point

A fixed threshold is a fixed **operating point** — and operating points have
asymmetric costs (cost-sensitive classification).

- Net secure key rate hits zero at **QBER = 9.81%** — independently reproduces Result 1.
- In an ETSI-QKD-014 key-pool model: break-even near **Q ≈ 3.8%**, zero production by **≈9.8%**.
- Accepting a run in the **9–11% band delivers zero usable key while reporting success** —
  starving every downstream consumer.

**A learned detector exposes a *tunable* operating point — the stump has one hard-wired split.**

---

## Result 3 — the multivariate classifier dominates (core result)

Detection recall on **hard negatives** — attacks engineered to sit *under* the 11% split:

| Intercept fraction | Mean QBER | Stump recall | RF recall |
|---|---|---|---|
| 0.1 | 3.2% | 0% | 24% ± 9% |
| 0.2 | 5.5% | 0% | 73% ± 8% |
| 0.3 | 8.2% | **0%** | **96% ± 5%** |
| 0.4 | 11.0% | (aborts) | 100% |

At 8.2% QBER the stump has **0% recall by construction**; the Random Forest —
reading error variance, burst structure, and sift statistics — reaches **96%**.

**A feature-engineering / representation win:** same runs, separable feature space.

---

## Result 4 — robustness under co-evolutionary attack

The DEAP gym evolves bounded-perturbation, threshold-evading attacks over 20
generations (mean ± 1 SD, 5 seeds). *Evasion = attacks let through.*

| Defender | Evasion (attack success) |
|---|---|
| Static 11% stump | **34.5% ± 3.2%** |
| Learned RF, frozen | 8.7% ± 3.8% |
| Learned RF, retrained each gen | 8.8% ± 2.1% |

- Attacker genuinely improves (fitness ~0.03 → ~0.8), yet learned defenders hold at **6–9%**.
- **25.7-point gap** > 3× the combined noise → statistically decisive.

---

## An honest ML qualification

**Adversarial retraining did *not* beat the frozen baseline** (8.8% vs 8.7%, within noise).

- Against this bounded-perturbation attacker, the RF is already near its robustness floor.
- The advantage comes from the **representation** (multivariate features) —
  **not** from the co-evolutionary hardening loop.

> This distinction is only visible **because of the multi-seed error bars.**
> The win is a *feature effect*, stated precisely.

---

## Synthesis — four ML claims, one argument

| # | ML claim | Result |
|---|---|---|
| 1 | Boundary is **miscalibrated** | 11% → true 9.81% |
| 2 | Fixed operating point has a **cost** | zero key in 9–11% band |
| 3 | **Representation** recovers hard negatives | 0% → 96% recall |
| 4 | Learned detector is **adversarially robust** | 34.5% → 8.7% evasion |

**Contribution — a learning result, not a cryptographic one:** a calibrated,
feature-rich, adversarially-evaluated classifier dominates a hand-set threshold
on a real security-detection task, with quantified margins.

---

## Recommendation — an adaptive abort criterion

Replace the static 11% policy with a **calibrated, tunable operating point**:

1. **Calibrate** to the true zero-rate boundary for the deployment's f_ec and block
   size (≤ 9.81%, not 11%).
2. **Choose** the operating point that meets an explicit false-accept budget.
3. **Gain** the sub-threshold recall (Result 3) that *no* QBER-only threshold can reach.

Turns "abort at 11%" from an inherited constant into a **deliberate, auditable choice.**

---

## References & scope

**Reviewed papers (≤ 2005, directly related):**
- **[1]** Dalvi, Domingos, Mausam, Sanghai, Verma — *Adversarial Classification*, KDD 2004
- **[2]** Shor & Preskill — *Simple Proof of Security of BB84*, Phys. Rev. Lett. 85, 441 (2000)

**Supporting:** Goodfellow et al. — *Adversarial Examples* (ICLR 2015); *GANs* (NeurIPS 2014)

**Scope:** BB84 with one-way post-processing (where the 11% bound applies).
All results reproducible from `thesis_experiments/`, `thesis_data/`, `thesis_figures/`.
