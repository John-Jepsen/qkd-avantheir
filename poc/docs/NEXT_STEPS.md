# Next Steps After the MVP

The MVP confirms the business logic is real and the chosen stack works
end-to-end. This document is the honest list of what comes next, and
which items would change the project's milestone plan vs. just refining
existing milestones.

## Items that are already done but not in the MVP demo

These are wired up in `implementation/` and tested individually. They
were excluded from the MVP not because they don't work but because they
require extra infrastructure to demo.

| Item | Why excluded | What would need to happen |
|------|--------------|---------------------------|
| Dual-KME with peer sync (`kme_dual.py`) | Needs two ports + peer sync configuration | Extend `03_kme_psk_demo.sh` to start both KMEs and assert the peer-sync POST landed |
| Trusted-node relay (`relay_network.py`) | Needs multi-node topology config | New script `06_relay_demo.sh` that builds a 4-node path NYC→LA |
| Hybrid QKD+PQC KDF (`hybrid_kdf.py`) | Needs ML-KEM dependency | Add a KAT-style assertion that Alice and Bob derive the same combined key |
| Adversarial evaluation (`adversarial_eval.py`) | Quick to run, just not on the MVP critical path | One-shot script that prints evasion-rate before/after hardening |
| React + D3 dashboard (`frontend/`) | Needs a browser to verify | Smoke test that `npm run build` succeeds; visual verification stays manual |

None of these change the milestone plan. They are loose ends that will
be tied off during M5.

## Items that could change the milestone plan

Reflecting on the MVP per the assignment brief — "students should
consider its outcome to validate their own ideas, seek for orientation,
and eventually make more abrupt changes in terms of planning and the
project as a whole" — here is the honest re-read:

### 1. The KME pool startup time is real and noticeable.

Pre-filling 50 keys via BB84 takes about 30 seconds even on the classical
backend. For a presentation demo this is awkward. Options:

- Lower `POOL_TARGET` to 5 for the demo and document why.
- Make `POOL_TARGET` configurable via env var (small one-line change).
- Pre-warm the pool by serializing keys to disk for the demo, with a
  warning that this is demo-only.

Recommendation: env var. Touches one line of `kme_server.py`. Low risk.

### 2. The 8→12 feature upgrade broke the 8-feature tests but not the run.

The pickle files on disk were already retrained at 12 features, so
`run_mvp.sh` passes. But `tests/test_features.py` and
`tests/test_ml_classifiers.py` still assert `len(FEATURE_NAMES) == 8`
and will fail if anyone runs the full pytest suite.

Recommendation: update the assertions to 12. This is a small fix that
should land before M5 wraps.

### 3. The MVP doesn't prove the *adaptive* claim.

Submission 2's abstract emphasizes "co-evolving attacker and defender."
The MVP only shows the defender works against a *static* intercept-resend
attack. The whole point of the project — that the ML defender holds up
when attackers learn — is in `adversarial_gym.py` and not part of the
MVP exit criteria.

Recommendation: do not change the milestone plan, but reframe the MVP
as "the closed-loop pipeline works" and explicitly mark "the adaptive
defense holds over generations" as the M5 deliverable. The
`ADVERSARIAL_FINDINGS.md` document already captures the experimental
results from M5 work that has happened.

### 4. The `/analyze` endpoint runs BB84 inline.

Each `/analyze` call kicks off a new BB84 simulation. For a few requests
this is fine. For a real-world stream of monitoring requests this would
be a problem. The production answer is to decouple sampling from
classification — the API should accept a `BB84Result` payload and return
a verdict, with the simulator running on its own cadence.

Recommendation: not blocking for the MVP. Add as a "production hardening"
note for the final presentation.

### 5. There is no end-to-end test in CI yet.

`run_mvp.sh` *is* the end-to-end test, but it isn't wired into GitHub
Actions. The existing CI workflow runs unit tests only.

Recommendation: add a workflow that runs `run_mvp.sh` on a Linux runner
and uploads the `evidence/` folder as an artifact. This is the
single most valuable thing M5 could ship — it makes "did the MVP still
work this week?" an answerable question without re-running locally.

## Items that the MVP made it clear we *don't* need

- A persistent database. The in-memory data structures are sufficient
  for the reference architecture. This was an open question in the
  planning doc; the MVP confirms the call.
- A separate auth service for the KME. Per the planning doc, the KME
  trusts any SAE ID. The MVP demonstrates this is fine for the
  reference scope.
- A bespoke ML model server. `joblib.load` of a pickle file is plenty
  for this use case. No need for a model registry or an inference
  framework.

## Honest delta from Submission 2's plan

Submission 2 implies the MVP would land at the end of M4. In practice
the MVP landed inside M4 — the ML pipeline was already complete enough
to demonstrate the closed loop without finishing every M4 task. This is
a small win on schedule but does not change scope.

The largest open work item is the adversarial gym and dashboard (M5),
which has substantial code already (`adversarial_gym.py`,
`adversarial_eval.py`, `frontend/`) but is not what the MVP demonstrates.
