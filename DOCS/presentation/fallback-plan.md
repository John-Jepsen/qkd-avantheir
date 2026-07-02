# Demo Fallback Plan

If the live demo misbehaves, switch immediately — don't debug in front of
the room. The rule: **one retry maximum** per segment, then fallback.

## What to prepare (once, before presentation day)

1. **Screen recording** of one clean end-to-end run of the entire
   [demo script](demo-script.md), captured with QuickTime
   (`⇧⌘5` → record selected window). Keep it as one file with rough
   timestamps noted per segment so you can scrub to any segment
   independently.
2. **Terminal transcripts** captured to text while recording:

   ```bash
   python bb84_simulator.py | tee captures/bb84_run.txt
   curl -s -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" \
     -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": false}' \
     | python3 -m json.tool | tee captures/analyze_clean.json
   curl -s -X POST http://127.0.0.1:8000/analyze -H "Content-Type: application/json" \
     -d '{"n_bits": 4096, "error_rate": 0.01, "eavesdrop": true}' \
     | python3 -m json.tool | tee captures/analyze_eavesdrop.json
   ```

3. **Dashboard screenshots** — two or three frames of the adversarial gym
   mid-evolution, including the phylogeny tree.
4. Put recording + transcripts + screenshots in `DOCS/presentation/captures/`
   and open them in a background window before the talk.

## Degradation ladder

| Level | Situation | Action |
|---|---|---|
| 0 | All good | Full live demo |
| 1 | One component flaky (e.g., dashboard) | Live-demo the rest; screenshots for the flaky part |
| 2 | Environment broken (venv, ports, Wi-Fi) | Play the recording, narrate over it with the same script lines |
| 3 | Machine/projector failure | Walk the architecture from the printed `analyze` JSON transcripts — the SECURE vs. ABORT contrast carries the argument on paper |

## Segment-specific notes

- **Segment 1 (BB84):** the Qiskit run takes noticeably longer than the
  classical backend. If it stalls, the classical fallback shows the same
  QBER story: `python -c "from bb84_simulator import BB84Protocol;
  print(BB84Protocol(backend='classical').run(n_bits=4096))"`.
- **Segment 3 (ML pipeline):** the two JSON transcripts are the core
  evidence — `SECURE` with QBER ~0.01 vs. `ABORT` with QBER ~0.27 and
  `intercept_resend` at confidence 1.0. These read fine as static text.
- **Segment 4 (gym):** the dashboard is the most fragile piece (three
  moving parts: uvicorn, WebSocket, Vite). Screenshots lose nothing
  essential — the phylogeny tree is a static image anyway.

## Talking line for the switch

> "In the interest of time I'll show you the recorded run — this is the
> same code you can run from the repo README."

Say it once, keep moving. Nobody remembers a fallback; everybody remembers
five minutes of live debugging.
