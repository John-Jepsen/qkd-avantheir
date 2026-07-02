# Live Demo Script

Rehearsed sequence for the final presentation. Total demo target: ~6 minutes.
Every command below assumes the repo root is `~/Desktop/mscs/qkd-avantheir`
and the implementation venv is built (`cd implementation && python3 -m venv
.venv && source .venv/bin/activate && pip install -r requirements.txt`).

Run through this end-to-end at least once the day before, and once ~30
minutes before presenting. If anything misbehaves, switch to the
[fallback plan](fallback-plan.md) without apologizing — the recording shows
the same thing.

## Pre-flight checklist (before the talk starts)

- [ ] `cd implementation && source .venv/bin/activate` in **four** terminals
- [ ] Trained models exist: `ls data/*.pkl` — if empty, run
      `python train_all_models.py`
- [ ] Frontend deps installed: `cd frontend && npm install`
- [ ] Ports 5000, 8000, 3000 free: `lsof -i :5000 -i :8000 -i :3000`
- [ ] Terminal font large enough to read from the back of the room
- [ ] Fallback recording/screenshots open in a background window

---

## Segment 1 — BB84 with an eavesdropper (~90 s)

**Terminal 1:**

```bash
python bb84_simulator.py
```

**Say while it runs:** "This is the BB84 protocol running as real quantum
circuits on IBM's Qiskit Aer simulator — X and H gates for encoding, a
depolarizing noise model for the fiber. Three scenarios: clean channel,
noisy channel, and an intercept-resend eavesdropper."

**Point at:** the eavesdropper scenario QBER (~25%) versus the clean run
(~1%). "Eve can't measure without disturbing — wrong-basis collapse forces
the error rate to ~25%, far past the 11% abort threshold. Detection here is
physics, not heuristics."

## Segment 2 — Key delivery + QKD-keyed encryption (~2 min)

**Terminal 1 (leave running):**

```bash
python kme_server.py
```

**Say:** "This is a Key Management Entity implementing ETSI GS QKD 014 —
the same REST API real Toshiba or ID Quantique hardware exposes. It
pre-generates 50 BB84 keys and refills in the background."

**Terminal 2:**

```bash
curl http://127.0.0.1:5000/api/v1/keys/sae-bob/status
python tls_psk_demo.py server
```

**Terminal 3:**

```bash
python tls_psk_demo.py client
```

**Say:** "Alice fetched a key and a key ID from `/enc_keys`; she sends Bob
only the ID; Bob redeems it at `/dec_keys`. They now share a 256-bit secret
that never crossed the classical network — and use it for AES-256-GCM.
There is no Diffie-Hellman anywhere in this exchange. This is exactly the
external-PSK pattern TLS 1.3 supports in RFC 8446."

## Segment 3 — ML adaptive pipeline (~90 s)

**Terminal 4:**

```bash
uvicorn api:app --port 8000
```

**Terminal 2 (server demo done, reuse it):**

```bash
# Clean channel
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": false}' | python3 -m json.tool

# Eavesdropper
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": true}' | python3 -m json.tool
```

**Point at:** `"verdict": "SECURE"` on the first call; on the second,
`"verdict": "ABORT"`, QBER ~0.27, and
`"predicted_attack": "intercept_resend"` with confidence ~1.0.

**Say:** "Five models run in one closed loop — eavesdrop detection, attack
classification, QBER forecasting, parameter tuning, and KME traffic anomaly
detection. Instead of a single hard threshold, the system names the attack
and recommends the response."

## Segment 4 — Adversarial gym dashboard (~60 s)

**Terminal 2:**

```bash
cd ../frontend && npm run dev
```

Open `http://localhost:3000` (the FastAPI service from Segment 3 must stay
up — the dashboard streams from its `/ws/evolution` WebSocket).

**Say:** "Static benchmarks can't tell you whether a defense survives an
adversary that adapts. This gym co-evolves attack strategies — bounded by
QKD physics — against defenders that retrain each generation. The phylogeny
tree tracks which attack lineages survived."

Let one or two generations stream, then stop.

## Segment 5 — one-liner close (~15 s)

"Everything you just saw is reproducible from the repo README, and the
client, proofs, and simulator ship as `qkdsec` on PyPI — `pip install
qkdsec`."

---

## Timing summary

| Segment | Time |
|---|---|
| BB84 + eavesdropper | 1.5 min |
| KME + PSK demo | 2 min |
| ML pipeline | 1.5 min |
| Adversarial gym | 1 min |
| Close | 0.25 min |

## Known failure modes

| Symptom | Fix |
|---|---|
| KME port busy | `lsof -ti :5000 | xargs kill`; macOS: disable AirPlay Receiver (also claims 5000) |
| `/analyze` returns model errors | `python train_all_models.py`, restart uvicorn |
| Dashboard blank | Confirm uvicorn on 8000 is up **before** loading page; hard-refresh |
| Qiskit import error | `source .venv/bin/activate` was skipped, or fall back: `BB84Protocol(backend="classical")` |
| Anything else | Switch to the fallback recording — do not debug live |
