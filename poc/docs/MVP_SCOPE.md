# MVP Scope

## The one-line MVP

> "We can run BB84, deliver the resulting key through a standards-compliant
> KME to two parties, encrypt traffic between them with no Diffie-Hellman,
> and have an ML pipeline correctly call the channel `SECURE` when it is
> clean and `ABORT` when an eavesdropper is on the line."

If a reviewer asks "did the MVP work?", the answer is yes when those four
sentences hold true and `poc/scripts/run_mvp.sh` returns exit code 0.

## Why this is the right MVP

The capstone planning doc lists five milestones, each with several tasks.
Picking the MVP is a question of "which subset of these milestones, when
glued together end-to-end, proves the business logic?" The answer:

| Milestone | Pulled into MVP | Why |
|-----------|-----------------|-----|
| M1: QKD foundations | partial — BB84 only | The pipeline needs *some* quantum key generation; BB84 is the canonical choice and the only protocol the planning doc commits to |
| M2: Protocol integration | partial — TLS PSK only | TLS PSK is the simplest possible protocol-integration win. IPsec/IKEv2 and service-mesh rekeying are documented but require external tools (strongSwan, Istio) the MVP doesn't need |
| M3: Key management | yes — ETSI 014 KME | Without a KME the ML layer has nothing to monitor and the PSK demo has nowhere to fetch keys from |
| M4: Working implementation | yes — full pipeline | This *is* the MVP |
| M5: Integration & delivery | partial — adversarial gym deferred | The dashboard, gym, and full test suite are post-MVP. Their absence does not block proving the business logic |

This carves the project into a 53-second demo (verified — see RESULTS.md)
that exercises the closed loop without depending on hardware, browsers, or
external services.

## What the MVP proves

1. **The integration story is real.** BB84 → KME → PSK is wired up in code,
   not just in the documentation. Keys flow through the standard ETSI 014
   surface and an unmodified PSK consumer can use them.

2. **ML can replace the static QBER threshold without losing detection.**
   The eavesdrop classifier and attack classifier both correctly flag the
   intercept-resend attack at 100% confidence in the captured evidence.
   The clean run is correctly labelled `clean` with >99% confidence.

3. **The closed loop is observable.** A single `/analyze` call returns
   simulation metrics, three ML predictions, and a unified verdict —
   meaning a downstream consumer (a SOC, an SDN controller, an admission
   controller) has everything it needs in one response to make a key-rotate
   or session-abort decision.

## What the MVP intentionally does *not* prove

- That the ML detector survives an adaptive attacker over many rounds.
  That is the M5 adversarial gym question, and it is genuinely a different
  experiment.
- That this works on real quantum hardware. The Qiskit Aer simulator is a
  faithful reproduction of the BB84 algorithm, but the ML models are
  trained on simulator output. The risk register in the planning doc lists
  this as the project's #1 risk.
- That the system is production-secure. The KME runs on plain HTTP over
  localhost and accepts any SAE ID. Authentication, mTLS, and rate
  limiting are not in scope for an MVP.
- That the React + D3 adversarial dashboard renders. The frontend builds,
  but exercising it requires a human in front of a browser — out of scope
  for a one-command MVP.

## What changes if the MVP fails

If criteria 1–2 fail (BB84 doesn't simulate correctly), revisit the
quantum simulation backend choice in M1 — likely a Qiskit version
incompatibility.

If criteria 3–4 fail (ML classifiers misfire), the eavesdrop and attack
models need retraining (`train_all_models.py`). The pickles ship in
`implementation/data/` so this should not happen on a fresh checkout.

If criteria 5–6 fail (KME or PSK), the issue is almost certainly a port
collision (5000 in use) or a missing `cryptography` dependency.

If criteria 7–8 fail (FastAPI), the most common cause is a missing model
pickle. The `/health` endpoint will say which model failed to load.
