# Thesis Subject Brief

**Student:** John Jepsen
**Program:** MSCS
**Date:** July 2026
**Status:** Submitted for Qwasar review

---

## Subject

The operational validity of the canonical 11% QBER (quantum bit error rate)
abort threshold in BB84 quantum key distribution.

## Thesis Statement

The 11% QBER threshold — widely cited as the point at which BB84 must abort —
is an artifact of an asymptotic security proof, not a safe operating
threshold. This thesis quantifies how far below 11% the practical security
boundary sits, and demonstrates experimentally that a static threshold is an
exploitable policy that adaptive, ML-based abort criteria dominate.

## Background

The 11% figure derives from the Shor–Preskill security proof: the asymptotic
BB84 key rate R = 1 − 2H₂(Q) reaches zero at Q ≈ 11%. That result assumes
infinite key blocks, Shannon-limit error correction, and counts any positive
key rate as success. In deployed systems none of these assumptions hold, yet
the 11% figure persists in implementations and literature as a de facto
operating rule.

## Research Questions

1. Where does the secure key rate actually reach zero for realistic finite
   block sizes (finite-key analysis), and how large is the gap from 11%?
2. How much key material can an adversary compromise while deliberately
   holding QBER below the threshold (e.g., partial intercept-resend attacks)?
3. Can a machine-learning detector, trained on richer channel features than
   QBER alone, reliably detect sub-threshold attacks that a static 11%
   policy accepts?
4. Do adversarially evolved attack strategies confirm the exploitability of
   the static threshold — and does adversarial retraining close the gap?

## Method

Four lines of evidence, all built on infrastructure from my completed
capstone (QKD enterprise integration, all five milestones delivered):

1. **Numerical security proofs** — sweep QBER × block size using the
   Shor–Preskill asymptotic bound and Tomamichel finite-key correction
   (implemented in my published `qkdsec` package) to map the true zero-rate
   boundary.
2. **Key-rate and operational collapse** — quantify key-pool starvation near
   threshold using Cascade error-correction leakage models and KME pool
   metrics from the capstone implementation.
3. **Sub-threshold attack simulation** — partial intercept-resend attacks on
   the BB84 simulator (Qiskit Aer), measuring the adversary's information
   gain as a function of QBER held below 11%.
4. **Adversarial ML evaluation** — evaluate the Random Forest eavesdrop
   detector against sub-threshold attacks, and use the existing DEAP
   co-evolutionary gym to evolve threshold-evading strategies against both
   static and adaptive defenses.

## Scope and Assumptions

BB84 with one-way post-processing (the regime where the 11% bound applies).
Two-way post-processing, which tolerates higher QBER, is out of scope and
stated as such. The claim is not that the finite-key gap is unknown to the
literature — it is that this thesis measures the gap end-to-end on a working
stack and demonstrates the exploitability of static thresholds with
adversarial ML, which is the novel contribution.

## Expected Deliverables

- Thesis document with reproducible numerical results
- Key-rate boundary figures (asymptotic vs. finite-key, multiple block sizes)
- Sub-threshold attack and detection benchmark, released as an extension to
  the open-source `qkdsec` package (PyPI)
- Recommended adaptive abort criterion with measured false-accept/false-reject
  trade-offs against the static 11% policy
