# Learned vs. Fixed Decision Boundaries for Eavesdrop Detection in Quantum Key Distribution

### An adversarially-robust machine-learning reappraisal of the 11% QBER rule

**John Jepsen** · MSCS (Machine Learning) · 2026

---

## Abstract

The canonical 11% quantum-bit-error-rate (QBER) abort rule in BB84 key
distribution is, in machine-learning terms, the simplest classifier that can
exist: a univariate decision stump with a hand-set split point, no training,
and a single fixed operating point. This thesis treats that rule as an ML
baseline and asks whether a trained, multivariate classifier dominates it, and
whether the advantage survives an adaptive adversary. On a working QKD stack I
show four things: (a) the stump's decision boundary is *miscalibrated* — offset
from the true class boundary by 1–6 points of QBER, always toward accepting
insecure runs; (b) that miscalibration has a measurable operational cost; (c) a
twelve-feature supervised classifier recovers hard-negative attacks the stump
accepts by construction, lifting recall from 0% to 96%; and (d) the learned
detector holds under co-evolutionary attack (8.7% evasion) where the stump
collapses (34.5%). The contribution is a learning result, not a cryptographic
one: a calibrated, feature-rich, adversarially-evaluated classifier dominates a
hand-set threshold on a security-critical detection task, with quantified
calibration, recall, and robustness margins.

---

## 1. Introduction

Practitioners who deploy quantum key distribution run a classifier every time
they decide whether a key exchange is trustworthy — they just do not call it
that. The decision is: measure the quantum bit error rate (QBER) of a BB84 run,
and if it exceeds 11%, abort; otherwise accept the key. Stated plainly, this is
a *univariate decision stump*: one feature (QBER), one hand-set split point
(0.11), no training data, no calibration against ground truth, and no adaptation
to the adversary. It is the degenerate limit of a supervised classifier.

This thesis is a machine-learning thesis. QKD is the application domain — it
supplies the data-generating process, the ground-truth labels, and a
security-critical reason to care whether the classifier is any good — but it is
not the subject. The subject is a standard ML question asked of a rule that
happens to be load-bearing in a real system: **does a trained, multivariate
classifier dominate a hand-set single-feature threshold, and does that
dominance survive when the adversary adapts?**

Four research questions follow directly:

1. **Calibration.** Where does the true class boundary — the QBER at which a run
   is genuinely insecure — actually sit, and how far is the 11% split from it?
2. **Cost of the operating point.** What is the false-negative cost of the
   stump's fixed operating point in a realistic key-delivery model?
3. **Representation.** Does a supervised classifier trained on richer channel
   features recover the hard-negative attacks the univariate stump accepts by
   construction?
4. **Adversarial robustness.** Under bounded-perturbation, co-evolutionary
   attack, does the learned detector's advantage hold while the stump's does
   not?

Each question is answered end-to-end on infrastructure from a completed QKD
capstone, so every claim is measured on a working stack rather than argued in
the abstract. The results establish, in order: a miscalibrated boundary, a
quantified cost, a representation win, and a robustness margin.

The contribution is deliberately framed as machine learning rather than
cryptography. Prior work on QKD security reasons about the 11% bound as a
physics result to be proved tighter or looser; this thesis instead treats the
bound as a *deployed classifier* and evaluates it with the standard ML apparatus
— calibration against ground-truth labels, recall on hard-negative examples,
cost-sensitive operating points, and worst-case robustness against an adaptive
adversary. Naming the rule as a classifier is itself the enabling move: once it
is one, every downstream comparison is a routine ML question with a measurable
answer, and the answer is that the hand-set threshold loses on all four axes.

---

## 2. Background and Related Work

### 2.1 The threshold as a degenerate classifier

The 11% figure comes from the Shor–Preskill security proof for BB84 [2]: the
asymptotic secure-key rate `R = 1 − 2H₂(Q)` reaches zero at `Q ≈ 11%`, where
`H₂` is binary entropy. That derivation assumes infinite key blocks, error
correction at the Shannon limit, and treats *any* positive key rate as success.
Deployed systems satisfy none of these assumptions, yet the 11% number persists
as a de facto operating rule.

Read as machine learning, this is a classifier with every part fixed by hand.
The feature space is one-dimensional (QBER alone). The decision boundary is a
constant that was never fit to labeled data. The operating point is a single
threshold with no precision–recall trade-off exposed. A stump like this has two
predictable failure modes: it is **miscalibrated** if the hand-set split does
not coincide with the true class boundary, and it is **blind by construction**
to any attack that keeps its one feature below the split. Both failure modes are
exactly what a trained, multivariate classifier is built to fix — the first
through calibration against ground-truth labels, the second through a richer
representation that separates classes the marginal feature cannot.

### 2.2 Adversarial machine learning

A security detector is not evaluated against nature; it is evaluated against an
adversary who observes the detector and adapts. Dalvi, Domingos, Mausam, Sanghai,
and Verma [1] formalized exactly this setting — *adversarial classification* —
modeling classification as a game between a classifier and an adversary who
modifies instances specifically to evade detection, and showing that a detector
which ignores that game is systematically beaten by one that anticipates it.
This is precisely the situation of the 11% stump: a fixed classifier facing an
adversary free to shape the channel. The modern adversarial-ML literature
sharpens the same point with bounded-perturbation *adversarial examples* [3] and
the generator-versus-discriminator *adversarial-training* paradigm [4]; the
co-evolutionary attacker/defender game used in §4.4 is a discrete instantiation
of that adaptive-adversary idea. Together these define the robustness bar this
thesis holds both classifiers to: not "accurate on a fixed test set," but
"accurate against an adversary that is allowed to adapt."

### 2.3 Scope

The analysis is confined to BB84 with one-way post-processing — the regime where
the 11% bound applies. Two-way post-processing, which tolerates higher QBER, is
explicitly out of scope. The claim here is not that the finite-key gap is
unknown to the physics literature; it is that the *ML question* — whether a
trained, feature-rich, adversarially-evaluated classifier dominates a hand-set
single-feature threshold on this detection task — has not been posed and
measured end-to-end, and that is what this thesis does.

---

## 3. Method

Four components from the completed capstone supply the experimental harness,
each mapped to its ML role:

- **Ground-truth labels** come from the `qkdsec` key-rate package, which
  computes the BB84 secure-key rate via a Devetak–Winter semidefinite program
  (asymptotic Shor–Preskill limit plus a finite-key correction). This locates
  the physically true secure/insecure boundary the stump is trying to place.
- **The data-generating process** is a BB84 simulator on Qiskit Aer, with
  configurable depolarizing noise and a tunable partial intercept-resend
  eavesdropper. It produces labeled runs (clean vs. attacked) at controlled
  attack strengths.
- **The learned detector** is a Random Forest trained on a twelve-feature
  vector per run: eight directly measured channel statistics (QBER, sift ratio,
  error variance, maximum error-burst length, low- and high-error block
  fractions, error autocorrelation, and sift deviation) plus four
  physics-derived features (variance ratio, block entropy, burst–QBER product,
  and block-error kurtosis). The physics-derived features are constrained by the
  channel and so are hard to forge independently. Feature extraction is a single
  shared function, so the stump and the forest see identical runs — the only
  difference is how many features each is allowed to use.
- **The adversarial-training harness** is a DEAP co-evolutionary gym that evolves
  bounded-perturbation, threshold-evading attack strategies over successive
  generations against a defender that may retrain each generation.

**Training and evaluation protocol.** The Random Forest is fit on labeled BB84
runs generated across a grid of noise levels and attack strengths, with clean
and attacked runs balanced so that neither class dominates the fit. Because the
comparison of interest is behavior on *hard negatives*, the held-out evaluation
set deliberately over-samples the sub-threshold band — attacks whose QBER falls
below 11% — rather than the easy, high-QBER attacks both classifiers catch
trivially. The stump requires no training; it is the fixed rule `abort if
QBER > 0.11`, evaluated on the identical runs through the identical feature
extractor, so any performance difference is attributable to representation and
calibration alone, not to a difference in data.

**The co-evolutionary harness.** In §4.4 the attacker is a population of
bounded-perturbation intercept-resend strategies whose parameters are evolved by
the DEAP gym under a fitness function that rewards both stealing key and evading
the defender. Perturbations are bounded so the evolved attacks remain physically
realizable rather than drifting into channel states the hardware could never
produce. Three defenders are held against this evolving population: the static
stump, a frozen Random Forest, and a Random Forest retrained on the attacker's
current generation each round — the discriminator-update half of the
adversarial-training loop. Contrasting the frozen and retrained forests isolates
how much of any robustness comes from the representation versus from
adversarial hardening.

Every result is reproducible from `thesis_experiments/` and `thesis_data/`;
figures are written to `thesis_figures/`. Two experiments (the sub-threshold
benchmark and the co-evolution) are reported as means over five independent
replicate batches with ±1 standard-deviation error bars, so the comparisons
carry variance control rather than resting on a single run.

---

## 4. Results

### 4.1 The hand-set decision boundary is miscalibrated

Before comparing classifiers, we need the true class boundary — the QBER above
which a run is genuinely insecure, i.e., the label the stump is trying to place.
Sweeping the BB84 secure-key rate over QBER and block size with the
Devetak–Winter program in `qkdsec` locates where the secure rate truly reaches
zero, as a function of error-correction inefficiency (`f_ec`) and block size `n`.

**Table 1 — True zero-rate QBER boundary (ε = 10⁻¹⁰).**

| Regime | f_ec = 1.00 (ideal) | f_ec = 1.16 (practical) |
|---|---|---|
| Asymptotic | 11.00% | **9.81%** |
| n = 10⁸ | 10.94% | 9.75% |
| n = 10⁶ | 10.33% | 9.23% |
| n = 10⁵ | 8.96% | 8.02% |
| n = 10⁴ | 5.21% | 4.70% |

The ideal asymptotic case recovers 11.00%, validating the pipeline against the
textbook Shor–Preskill result [2] — but that is the *only* configuration that
yields 11%. With
realistic reconciliation the true boundary is **9.81%**, and at a practical block
of 10⁶ signals it is **9.23%**. In ML terms, the stump's decision boundary is
**offset from the Bayes-optimal boundary by 1–6 points of QBER, always in the
unsafe direction**. The rule is not merely crude; it is *miscalibrated* — its
single hard-coded split point is in the wrong place, and no amount of the one
feature it uses can move it. This is the motivating defect the rest of the
thesis exploits and then repairs.

### 4.2 The cost of the operating point

A fixed threshold is also a fixed *operating point*, and operating points carry
asymmetric costs — the setting for cost-sensitive classification. Reusing the
leakage accounting `r(Q) = max(0, 1 − H₂(Q) − f_ec·H₂(Q))`, the net secure key
rate reaches zero at **QBER = 9.81%** for `f_ec = 1.16`, independently
reproducing §4.1's boundary from a separate calculation — a useful internal
consistency check. Feeding that rate into an ETSI-QKD-014 key-pool model shows
the pool reaching break-even near **Q ≈ 3.8%** and zero production by ≈9.8%. The
false-negative cost of the stump's operating point is therefore concrete:
accepting a run in the 9–11% band delivers zero usable key while reporting
success, starving every downstream consumer. A learned detector, by contrast,
exposes a *tunable* operating point along a precision–recall curve rather than
one hard-wired split.

A second observation reinforces the fragility of a single fixed split: because
QBER is estimated from a finite disclosed sample (~410 bits), the stump's
decision is itself noisy — aborts begin near Q ≈ 9% and are not certain until
Q ≈ 12%. The stump is not even a sharp boundary; it is a noisy one-feature
estimate thresholded without regard to that noise.

### 4.3 A multivariate learned classifier dominates the univariate stump

This is the core ML result: single-feature threshold vs. multi-feature trained
classifier, evaluated specifically on **hard negatives** — attacks engineered to
sit under the QBER split. Using the Qiskit-Aer simulator we sweep a partial
intercept-resend adversary's intercept fraction, averaging over five independent
replicate batches (75 trials per point; band = ±1 SD). The stump's recall on
these examples is 0 by construction — their QBER is under 11% — so the question
is whether learned features recover them.

**Table 2 — Detection recall on sub-threshold attacks (base error 1%).**

| Intercept fraction | Mean QBER | Eve's key knowledge | Stump (QBER-only) recall | RF classifier recall |
|---|---|---|---|---|
| 0.1 | 3.2% | 5% | 0% | 24% ± 9% |
| 0.2 | 5.5% | 10% | 0% | 73% ± 8% |
| 0.3 | 8.2% ± 0.2% | 15% | 0% | **96% ± 5%** |
| 0.4 | 11.0% | 20% | (aborts) | 100% |

Measured QBER tracks the theoretical `0.01 + 0.25·fraction`, confirming the
data-generating process. The **hard-negative region** extends to intercept
fraction 0.3: there the attack induces only 8.2% QBER — the univariate stump has
**0% recall** — while the Random Forest, reading block-level error variance,
burst structure, and sift statistics, achieves **96% ± 5% recall**. The lesson
is an ML one about **feature engineering and representation**: the two
classifiers see the same runs, but the multivariate feature space separates
attacks that are invisible in the marginal QBER distribution the stump projects
onto. The classifier's only weak region is very low intercept (fraction 0.1,
24% recall), where the attack is faint in every feature and Eve steals
correspondingly little — a benign failure mode.

### 4.4 Adversarial robustness under co-evolutionary training

A classifier that beats a *fixed* attack set may still collapse against an
adversary that adapts — the central concern of adversarial classification [1].
We test this with a co-evolutionary game, a discrete analogue of
adversarial/GAN-style training [4]: the DEAP gym evolves bounded-perturbation,
threshold-evading
attacks over 20 generations against three defenders, averaged over five
independent replicates. "Evasion" is attack success — the fraction of genuine
attacks a defender lets through.

**Table 3 — Final evasion rate under co-evolution (mean ± 1 SD, 5 seeds).**

| Defender | Evasion (attack success) |
|---|---|
| Static 11% stump | **34.5% ± 3.2%** |
| Learned RF, frozen (baseline) | 8.7% ± 3.8% |
| Learned RF, retrained each generation (adaptive) | 8.8% ± 2.1% |

The attacker genuinely improves — mean attack fitness climbs from ~0.03 to ~0.8
over the run — yet both learned defenders hold evasion near 6–9% while the stump
sits at **34.5% and never adapts**. The 25.7-point gap between stump and learned
evasion exceeds the combined ±1 SD noise (7.1 points) by more than 3×, so the
dominance is statistically decisive, not a sampling artifact.

One honest, ML-specific qualification: **adversarial retraining did not beat the
frozen baseline** (8.8% vs. 8.7%, within noise). Against this
bounded-perturbation attacker the baseline Random Forest is already near its
robustness floor, so the advantage comes from the *representation* (multivariate
features) rather than from the adversarial-training loop. This sharpens the
fourth claim into a precise ML statement: the win is a **feature/representation
effect, not a co-evolutionary-hardening effect** — a distinction only the
multi-seed error bars make visible.

### 4.5 Synthesis

Read as machine learning, the four results form one argument. §4.1 shows the
hand-set rule is a *miscalibrated univariate classifier* whose boundary (11%) is
offset from the true class boundary (9.81%). §4.2 quantifies the cost of that
fixed operating point. §4.3 shows a *multivariate learned classifier* recovers
the hard-negative attacks the stump misses (0% → 96% recall). §4.4 shows the
learned detector is *adversarially robust* where the stump is trivially
exploited (34.5% → 8.7% evasion), and isolates the effect to representation
rather than retraining.

---

## 5. Discussion, Limitations, and Conclusion

**What the results establish.** A trained, feature-rich, adversarially-evaluated
classifier dominates a hand-set single-feature threshold on a real
security-detection task, with the dominance quantified at every stage:
calibration offset (1–6 points), hard-negative recall (0% → 96%), and adversarial
robustness (34.5% → 8.7% evasion).

**A recommended adaptive abort criterion.** The practical recommendation that
follows is to replace the static 11% policy with a calibrated, tunable operating
point on the learned detector's precision–recall curve. Concretely: calibrate
the decision boundary against the true zero-rate boundary from §4.1 for the
deployment's actual `f_ec` and block size (9.81% or lower, not 11%), then select
the operating point that meets an explicit false-accept budget rather than
inheriting whichever trade-off the 11% split happens to imply. Because the
learned detector reads twelve features, the same operating point also catches
the sub-threshold attacks in §4.3 that no QBER-only threshold — at any value —
can reach. The trade-off is then a measured quantity: for a chosen false-accept
rate, Table 2 gives the recall recovered on hard negatives, and Table 3 gives
the evasion rate held under an adaptive adversary. This turns "abort at 11%"
from an inherited constant into a deliberate, auditable operating-point choice.

**Limitations.** The scope is BB84 with one-way post-processing; two-way
reconciliation tolerates higher QBER and is not modeled. The attacker in §4.4 is
a bounded-perturbation intercept-resend family, not the full space of physical
attacks, and the finding that retraining did not beat the frozen baseline is
specific to that family — a stronger or differently-parameterized adversary
could reopen a gap that adversarial training would then need to close. The
data-generating process is a simulator; the physics is faithful to the modeled
regime, but hardware side-channels are out of scope.

**Conclusion.** The 11% QBER rule is best understood not as a law of physics but
as a classifier — and a poor one: miscalibrated, single-feature, and static. Once
it is named as such, the standard machine-learning toolkit applies directly, and
a calibrated multivariate detector dominates it on exactly the axes an ML
evaluation cares about. The contribution is therefore a learning result, carried
end-to-end on a working QKD stack.

---

## References

### Reviewed papers (≥ 2, dated no later than 2005, directly related)

**[1]** N. Dalvi, P. Domingos, Mausam, S. Sanghai, D. Verma. "Adversarial
Classification." *Proceedings of the 10th ACM SIGKDD International Conference on
Knowledge Discovery and Data Mining (KDD)*, pp. 99–108, 2004. — The foundational
machine-learning treatment of classification as an explicit game between a
classifier and an adversary who modifies instances to evade detection. Dalvi et
al. show that an adversary-unaware classifier is systematically outperformed by
one that anticipates the adversary's best response — the exact premise this
thesis tests. §4.3's hard-negative benchmark and §4.4's co-evolutionary evasion
experiment are direct realizations of their adversary-aware evaluation on the QKD
detection task, with the static 11% stump cast as the adversary-unaware
classifier they prove exploitable and the trained Random Forest as its
adversary-aware replacement.

**[2]** P. W. Shor, J. Preskill. "Simple Proof of Security of the BB84 Quantum
Key Distribution Protocol." *Physical Review Letters*, 85(2):441–444, 2000. — The
origin of the 11% QBER bound: the asymptotic secure-key rate `R = 1 − 2H₂(Q)`
reaches zero at `Q ≈ 11%`. This thesis reviews the result specifically to expose
how it is used in practice — as a hand-set decision boundary for a univariate
classifier. §4.1 calibrates against exactly this bound, recovering 11.00% in the
ideal asymptotic regime the proof assumes and then quantifying how far the
deployed split sits from the true class boundary once the proof's infinite-block,
Shannon-limit assumptions are relaxed.

### Additional supporting references (adversarial-ML context for §4.4)

**[3]** I. J. Goodfellow, J. Shlens, C. Szegedy. "Explaining and Harnessing
Adversarial Examples." *International Conference on Learning Representations
(ICLR)*, 2015.

**[4]** I. J. Goodfellow, J. Pouget-Abadie, M. Mirza, B. Xu, D. Warde-Farley,
S. Ozair, A. Courville, Y. Bengio. "Generative Adversarial Nets." *Advances in
Neural Information Processing Systems (NeurIPS) 27*, pp. 2672–2680, 2014.
