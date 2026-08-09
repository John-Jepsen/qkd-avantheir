# Thesis Submission

**Learned vs. Fixed Decision Boundaries for Eavesdrop Detection in QKD**
*An adversarially-robust machine-learning reappraisal of the 11% QBER rule*

John Jepsen · MSCS (Machine Learning)

This folder holds the complete thesis submission and everything needed to
reproduce its numbers. It is a **machine-learning thesis**: the canonical 11%
QBER abort rule in BB84 is treated as a classifier — a univariate decision
stump — and compared against a trained, multivariate detector. QKD is the
testbed and data-generating process, not the subject.

## Contents

| Path | What it is |
|---|---|
| `thesis-paper.md` | The paper (~2,900 words excl. bibliography). Reframes the 11% rule as a stump; four results (miscalibration, operating-point cost, hard-negative recall, adversarial robustness). |
| `thesis-brief.md` | Subject brief: thesis statement, research questions, method, and submission deliverables/requirements. |
| `thesis-results-draft.md` | Working draft of the results chapters (ML framing, full tables). |
| `thesis-slides.md` | ML-led slide deck, Marp markdown source (11 content slides). |
| `thesis-slides.pptx` | The deck exported to PowerPoint (16:9, editable). |
| `thesis_data/` | Numerical outputs (CSV/JSON) produced by the experiments. |
| `thesis_figures/` | Figures (PNG) produced by the experiments. |
| `thesis_experiments/` | The four scripts that generate `thesis_data/` and `thesis_figures/`. |

## Deliverables checklist (per `thesis-brief.md`)

- **Paper** — 2,800–3,200 words excl. bibliography; ≥2 reviewed academic papers
  dated no later than 2005, listed in the bibliography. Reviewed papers:
  Dalvi et al. *Adversarial Classification* (KDD 2004) and Shor–Preskill
  *Simple Proof of Security of BB84* (PRL 2000).
- **Slide deck** — 5–15 slides excl. front page (`thesis-slides.*`, 11 slides).
- **Recorded presentation** — 18–20 min video (not in this repo).
- **Supporting artifacts** — key-rate boundary figures, the sub-threshold
  attack/detection benchmark, and an adaptive abort criterion (all under
  `thesis_data/` + `thesis_figures/`).

## Experiments → results mapping

Each script maps to one results section in `thesis-paper.md`:

| Script | Paper section | Key outputs |
|---|---|---|
| `thesis_experiments/exp1_keyrate_sweep.py` | §4.1 Miscalibrated boundary | `keyrate_boundaries.json`, `keyrate_sweep.{csv,json}`, `keyrate_boundary.png` |
| `thesis_experiments/exp2_pool_starvation.py` | §4.2 Cost of the operating point | `pool_starvation.{csv,json}`, `cascade_leakage_model.csv`, `empirical_key_yield.csv`, `pool_*.png`, `cascade_leakage.png` |
| `thesis_experiments/exp3_partial_intercept_sweep.py` | §4.3 Hard-negative recall | `partial_intercept_sweep.{json,csv}`, `*_per_seed.csv`, `subthreshold_{qber,info_gain}.png` |
| `thesis_experiments/exp4_adversarial_benchmark.py` | §4.4 Adversarial robustness | `adversarial_benchmark.csv`, `adversarial_evolution_log.json`, `adversarial_{fitness,evasion}.png` |

## Reproducing the numbers

The scripts depend on the repo's shared code — `implementation/` (BB84
simulator, feature extraction, the ML classifiers) and the `qkdsec/` submodule
(numerical key-rate proofs) — which live at the **repo root**, one level above
this folder. Each script resolves those paths from its own location, so it can
be run from anywhere.

From the repo root, using the project virtual environment:

```bash
implementation/.venv/bin/python thesis/thesis_experiments/exp1_keyrate_sweep.py
implementation/.venv/bin/python thesis/thesis_experiments/exp2_pool_starvation.py
implementation/.venv/bin/python thesis/thesis_experiments/exp3_partial_intercept_sweep.py
implementation/.venv/bin/python thesis/thesis_experiments/exp4_adversarial_benchmark.py
```

Outputs are written (and overwritten) under `thesis/thesis_data/` and
`thesis/thesis_figures/`. exp3/exp4 also load the trained eavesdrop model from
`implementation/data/eavesdrop_model.pkl`; the `qkdsec` submodule must be
initialized (`git submodule update --init qkdsec`) for exp1.

## Rebuilding the slide deck

The deck is generated from `thesis-slides.md` by the shared Marp→PPTX
converter in `../DOCS/presentation/`:

```bash
# from the repo root
python3 DOCS/presentation/md_to_pptx.py thesis/thesis-slides.md thesis/thesis-slides.pptx
```
