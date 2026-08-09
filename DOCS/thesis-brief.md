# Thesis Subject Brief

**Student:** John Jepsen
**Program:** MSCS (Machine Learning)
**Date:** July 2026
**Status:** Submitted for Qwasar review

---

## Subject

Learned vs. fixed decision boundaries for eavesdrop detection, evaluated on
quantum key distribution (QKD) as the application domain. This is a machine
learning thesis; QKD supplies the testbed, the data-generating process, and
the ground-truth labels — it is not the subject.

**Working title:** *Learned vs. Fixed Decision Boundaries for Eavesdrop
Detection in Quantum Key Distribution: an adversarially-robust
machine-learning reappraisal of the 11% QBER rule*

## Thesis Statement

The canonical 11% QBER (quantum bit error rate) abort rule in BB84 is a
classifier — the simplest one possible: a univariate decision stump with a
hand-set split point, no training, no calibration, and a fixed operating
point. This thesis shows that (a) the stump's decision boundary is
miscalibrated — offset from the true class boundary, always in the unsafe
direction; (b) that miscalibration carries a quantifiable operational cost;
(c) a trained multivariate classifier dominates the stump on hard-negative
examples (attacks engineered to sit below the split); and (d) the learned
detector remains robust under adaptive, co-evolutionary attack while the
stump does not.

## Background

The 11% figure derives from the Shor–Preskill security proof: the asymptotic
BB84 key rate R = 1 − 2H₂(Q) reaches zero at Q ≈ 11%. That result assumes
infinite key blocks, Shannon-limit error correction, and counts any positive
key rate as success. In deployed systems none of these assumptions hold, yet
the figure persists as a de facto operating rule. In ML terms, practitioners
are running a hand-set, single-feature threshold classifier on a
security-critical detection task — with no calibration against the true
class boundary and no evaluation against adaptive adversaries.

## Research Questions

1. **Calibration:** Where does the true class boundary (the QBER at which a
   run is genuinely insecure) actually sit for realistic error-correction
   inefficiency and finite block sizes, and how far is the 11% split point
   offset from it?
2. **Cost of the operating point:** What is the operational (false-negative)
   cost of the stump's fixed operating point, measured as key-pool
   starvation in an ETSI QKD 014 key-delivery model?
3. **Representation:** Does a supervised multivariate classifier, trained on
   richer channel features than QBER alone, recover the hard-negative
   attacks the univariate stump accepts by construction?
4. **Adversarial robustness:** Do adversarially evolved, bounded-perturbation
   attack strategies confirm the exploitability of the static threshold —
   and does the learned detector's advantage survive when the adversary
   adapts (co-evolutionary, GAN-style training)?

## Method

Four lines of evidence, all built on infrastructure from my completed
capstone (QKD enterprise integration, all five milestones delivered):

1. **Ground-truth labels** — sweep QBER × block size using the
   Shor–Preskill asymptotic bound and Tomamichel finite-key correction
   (implemented in my published `qkdsec` package) to locate the physically
   true secure/insecure class boundary the stump is trying to place.
2. **Cost-sensitive evaluation** — quantify the false-negative cost of the
   fixed operating point via Cascade error-correction leakage models and
   KME key-pool metrics from the capstone implementation.
3. **Hard-negative benchmark** — partial intercept-resend attacks on the
   BB84 simulator (Qiskit Aer, the data-generating process), measuring
   stump vs. Random Forest recall on attacks held below the 11% split,
   with multi-seed error bars.
4. **Adversarial-training harness** — the existing DEAP co-evolutionary gym
   evolves bounded-perturbation, threshold-evading attacks against static
   and learned defenders, with adversarial retraining each generation, to
   measure robustness under an adaptive adversary.

## Scope and Assumptions

BB84 with one-way post-processing (the regime where the 11% bound applies).
Two-way post-processing, which tolerates higher QBER, is out of scope and
stated as such. The claim is not that the finite-key gap is unknown to the
literature — it is that this thesis poses and answers the ML question:
whether a trained, feature-rich, adversarially-evaluated classifier
dominates a hand-set single-feature threshold on a real security-detection
task, measured end-to-end on a working stack with quantified calibration,
recall, and robustness margins.

## Deliverables (per submission requirements)

- **Thesis paper** — 2800–3200 words excluding bibliography, with
  reproducible numerical results (data in `thesis_data/`, figures in
  `thesis_figures/`). Includes a review of at least 2 academic papers
  directly related to the thesis, listed in the bibliography at the end of
  the paper.
- **Slide deck** — 5–15 slides excluding front page/intro slide,
  summarizing the thesis.
- **Recorded presentation** — video, 18–20 minutes (21 minutes absolute
  maximum).
- **Supporting artifacts** — key-rate boundary figures (asymptotic vs.
  finite-key, multiple block sizes); the sub-threshold attack and detection
  benchmark, released as an extension to the open-source `qkdsec` package
  (PyPI); and a recommended adaptive abort criterion with measured
  false-accept/false-reject trade-offs against the static 11% policy.
