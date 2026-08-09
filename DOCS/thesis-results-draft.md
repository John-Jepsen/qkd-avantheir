# Thesis — Results Chapters (draft, ML-framed)

**Student:** John Jepsen · **Program:** MSCS (Machine Learning)
**Working title:** *Learned vs. Fixed Decision Boundaries for Eavesdrop Detection in Quantum Key Distribution: an adversarially-robust machine-learning reappraisal of the 11% QBER rule*

> **Framing note (the spine of the thesis).** This is a machine-learning thesis; QKD is the application domain and testbed, not the subject. The central reframing:
>
> **The canonical 11% QBER abort rule is a classifier — the simplest one possible.** It is a *univariate decision stump*: a hand-set split on a single feature (QBER), with no training, no calibration, and a fixed operating point. The thesis asks the ML question that follows: *does a trained, multivariate classifier dominate this hand-set rule, and does it stay robust when the adversary adapts?* The four results establish (a) that the stump's decision boundary is miscalibrated — it sits in the wrong place relative to the true class boundary; (b) the operational cost of that miscalibration; (c) that a feature-based supervised classifier dominates the stump on hard (sub-threshold) negatives; and (d) that the learned detector remains robust under adversarial, co-evolutionary attack while the stump does not.
>
> **ML concepts carried through:** decision boundaries and calibration, single- vs multi-feature classification, feature engineering, recall on hard-negative examples, cost-sensitive operating points, adversarial examples and bounded-perturbation robustness, and co-evolutionary (GAN-style) adversarial training.
>
> **Planning note (not part of the submission).** Paper budget **2800–3200 words** excluding bibliography. Results below run **~1,650 words**. Suggested full-paper map: Introduction + ML problem statement (450) · Background — the threshold as a degenerate classifier, adversarial ML (550) · Method — features, models, the co-evolutionary harness (450) · **Results (this doc, ~1,650)** · Discussion + limitations + conclusion (300) → ~3,400, trim ~250 to land in band. The two required references (2005+) are ML papers, used inline and listed at the end.

---

## 4. Results

Each result is framed as an ML claim and validated on infrastructure from the completed capstone: the `qkdsec` key-rate package (which supplies *ground-truth labels* — the physically true secure/insecure boundary), the Qiskit-Aer BB84 simulator (the *data-generating process*), a Random-Forest eavesdrop classifier (the *learned detector*), and a DEAP co-evolutionary gym (the *adversarial-training harness*). Every number is reproducible from `thesis_experiments/` and `thesis_data/`.

### 4.1 The hand-set decision boundary is miscalibrated

Before comparing classifiers we need the true class boundary — the QBER above which a run is genuinely insecure. This is the label the naive stump is trying (and failing) to place correctly. Sweeping the BB84 secure-key rate over QBER and block size with the Devetak–Winter semidefinite program in `qkdsec` (asymptotic Shor–Preskill limit plus a finite-key correction) locates where the secure rate truly reaches zero, as a function of error-correction inefficiency (`f_ec`) and block size n.

**Table 1 — True zero-rate QBER boundary (ε = 10⁻¹⁰).**

| Regime | f_ec = 1.00 (ideal) | f_ec = 1.16 (practical) |
|---|---|---|
| Asymptotic | 11.00% | **9.81%** |
| n = 10⁸ | 10.94% | 9.75% |
| n = 10⁶ | 10.33% | 9.23% |
| n = 10⁵ | 8.96% | 8.02% |
| n = 10⁴ | 5.21% | 4.70% |

The ideal asymptotic case recovers 11.00%, validating the pipeline against the textbook Shor–Preskill result — but that is the *only* configuration that yields 11%. With realistic reconciliation the true boundary is **9.81%**, and at a practical block of 10⁶ signals it is **9.23%**. In ML terms, the 11% stump has a **decision boundary offset from the Bayes-optimal boundary by 1–6 points of QBER**, always in the unsafe direction. The stump is not merely crude; it is *miscalibrated* — its single hard-coded split point is in the wrong location, and no amount of the one feature it uses can fix it. This is the motivating defect the rest of the thesis exploits and repairs (`keyrate_boundary.png`).

### 4.2 The cost of the operating point

A fixed threshold is also a fixed *operating point*, and operating points have asymmetric costs — the setting for cost-sensitive classification. Reusing the same leakage accounting (`r(Q) = max(0, 1 − H₂(Q) − f_ec·H₂(Q))`), the net secure key rate reaches zero at **QBER = 9.81%** for f_ec = 1.16 — independently reproducing §4.1's boundary from a separate calculation, a useful internal consistency check. Feeding this rate into an ETSI-QKD-014 key-pool model shows the pool reaching **break-even near Q ≈ 3.8%** and zero production by ~9.8% (`pool_starvation_yield.png`, `pool_depletion_timeline.png`). The false-negative cost of the stump's operating point is therefore not abstract: accepting a run in the 9–11% band delivers zero usable key while reporting success, starving every downstream consumer. A learned detector, by contrast, exposes a *tunable* operating point along a precision–recall curve rather than one hard-wired split.

A second observation reinforces why a single fixed split is fragile: because QBER is estimated from a finite disclosed sample (~410 bits), the stump's decision is itself noisy — aborts begin near Q ≈ 9% and are not certain until Q ≈ 12%. The stump is not even a sharp boundary; it is a noisy one-feature estimate thresholded without regard to that noise.

### 4.3 A multivariate learned classifier dominates the univariate stump

This is the core ML result: single-feature threshold vs. multi-feature trained classifier, evaluated specifically on **hard negatives** — attacks engineered to sit under the QBER split. Using the Qiskit-Aer simulator we sweep a partial intercept-resend adversary's intercept fraction, averaging over five independent replicate batches (75 trials per point; band = ±1 SD). The stump's recall on these examples is 0 by construction (their QBER is under 11%); the question is whether learned features recover them.

**Table 2 — Detection recall on sub-threshold attacks (base error 1%).**

| Intercept fraction | Mean QBER | Eve's key knowledge | Stump (QBER-only) recall | RF classifier recall |
|---|---|---|---|---|
| 0.1 | 3.2% | 5% | 0% | 24% ± 9% |
| 0.2 | 5.5% | 10% | 0% | 73% ± 8% |
| 0.3 | 8.2% ± 0.2% | 15% | 0% | **96% ± 5%** |
| 0.4 | 11.0% | 20% | (aborts) | 100% |

Measured QBER tracks the theoretical `0.01 + 0.25·fraction`, confirming the data-generating process. The **hard-negative region** extends to intercept fraction 0.3: there the attack induces only 8.2% QBER — the univariate stump has **0% recall** — while the Random Forest, reading block-level error variance, burst structure, and sift statistics, achieves **96% ± 5% recall**. The lesson is an ML one about **feature engineering and representation**: the two classifiers see the same runs, but the multivariate feature space linearly separates attacks that are invisible in the marginal QBER distribution the stump projects onto. The classifier's only weak region is very low intercept (fraction 0.1, 24% recall), where the attack is faint in every feature and Eve steals correspondingly little — a benign failure mode. (The strict hard-negative edge is fraction 0.3; a single-run pilot placed it at 0.4, and the multi-seed mean corrects that to where fraction 0.4's QBER averages exactly 11.0%.)

### 4.4 Adversarial robustness under co-evolutionary training

A classifier that beats a *fixed* attack set may still collapse against an adversary that adapts — the central concern of adversarial ML [1]. We test this with a co-evolutionary game (a discrete analogue of adversarial/GAN-style training [2]): the DEAP gym evolves bounded-perturbation, threshold-evading attacks over 20 generations against three defenders, averaged over five independent replicates. "Evasion" is attack success — the fraction of genuine attacks a defender lets through.

**Table 3 — Final evasion rate under co-evolution (mean ± 1 SD, 5 seeds).**

| Defender | Evasion (attack success) |
|---|---|
| Static 11% stump | **34.5% ± 3.2%** |
| Learned RF, frozen (baseline) | 8.7% ± 3.8% |
| Learned RF, retrained each generation (adaptive) | 8.8% ± 2.1% |

The attacker genuinely improves — mean attack fitness climbs from ~0.03 to ~0.8 over the run — yet both learned defenders hold evasion near 6–9% while the stump sits at **34.5% and never adapts** across generations (`adversarial_evasion.png`). The 25.7-point gap between stump and learned evasion exceeds the combined ±1 SD noise (7.1 points) by more than 3×, so the dominance is statistically decisive, not a sampling artifact — exactly the kind of variance control an ML evaluation requires.

One honest, ML-specific qualification: **adversarial retraining did not beat the frozen baseline** (8.8% vs 8.7%, within noise). Against this bounded-perturbation attacker the baseline RF is already near its robustness floor, so the gain comes from the *representation* (multivariate features) rather than from the adversarial-training loop. This sharpens the thesis's fourth claim into a precise ML statement: the win is a **feature/representation effect, not a co-evolutionary-hardening effect** — a distinction that only becomes visible with the multi-seed error bars.

### 4.5 Synthesis

Read as ML, the four results form one argument. §4.1 shows the hand-set rule is a *miscalibrated univariate classifier* whose decision boundary (11%) is offset from the true class boundary (9.81%). §4.2 quantifies the cost of that fixed operating point. §4.3 shows a *multivariate learned classifier* recovers the hard-negative attacks the stump misses (0% → 96% recall). §4.4 shows the learned detector is *adversarially robust* where the stump is trivially exploited (34.5% → 8.7% evasion), and isolates the effect to representation rather than retraining. The contribution is therefore not a claim about cryptography but about learning: **a trained, feature-rich, adversarially-evaluated classifier dominates a hand-set single-feature threshold on a real security-detection task, with quantified calibration, recall, and robustness margins.**

---

## Academic paper review (≥ 2 papers, dated 2005 or later)

Both required references are foundational ML papers that the results directly build on, and both are post-2005:

- **[1]** I. J. Goodfellow, J. Shlens, C. Szegedy, "Explaining and Harnessing Adversarial Examples," *ICLR* (2015). — Frames §4.3–§4.4: bounded-perturbation adversarial examples and the evasion/robustness evaluation used against the detector.
- **[2]** I. J. Goodfellow, J. Pouget-Abadie, M. Mirza, B. Xu, D. Warde-Farley, S. Ozair, A. Courville, Y. Bengio, "Generative Adversarial Nets," *NeurIPS* (2014). — The attacker-vs-defender adversarial-training paradigm that the co-evolutionary gym in §4.4 instantiates.

> **Optional domain reference** (if the committee wants ML-applied-to-QKD grounding, not just ML theory): a machine-learning-for-QKD applied paper such as Wang & Lo, "Machine learning for optimal parameter prediction in quantum key distribution," *Phys. Rev. A* 100, 062334 (2019) — **verify the exact citation before use.** I can run a short literature search to confirm this and surface 2–3 alternates directly on ML-based QKD attack detection if you want the domain reference to be airtight.

---

*Data: `thesis_data/keyrate_boundaries.json`, `pool_starvation.json`, `partial_intercept_sweep.{json,csv}`, `adversarial_evolution_log.json`. Figures: `thesis_figures/`.*
