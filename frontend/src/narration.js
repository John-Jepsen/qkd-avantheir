// Translates a single generation's metrics into a plain-English play-by-play line.
// Designed to read like sports commentary so a non-specialist viewer
// can follow what the system is doing in real time.

function pct(x) { return `${Math.round((x || 0) * 100)}%` }

function trend(prev, curr) {
  if (prev == null) return null
  const delta = curr - prev
  if (Math.abs(delta) < 0.01) return 'holding steady'
  return delta > 0 ? 'climbing' : 'falling'
}

const VERDICTS = [
  { max: 0.10, line: 'defender is dominating' },
  { max: 0.25, line: 'defender has the edge' },
  { max: 0.45, line: 'roughly even' },
  { max: 0.70, line: 'attackers are pulling ahead' },
  { max: 1.01, line: 'defender is in trouble' },
]

function verdictFor(evasion) {
  return VERDICTS.find(v => evasion <= v.max).line
}

export function narrateGeneration(gen, idx, previous) {
  const prev = previous && previous[idx - 1]
  const evasionTrend = trend(prev?.evasion_rate, gen.evasion_rate)
  const accTrend = trend(prev?.defender_accuracy, gen.defender_accuracy)
  const verdict = verdictFor(gen.evasion_rate)

  if (idx === 0) {
    return `Generation 1: first wave of attackers spawned. ${pct(gen.evasion_rate)} slipped past the defender, defender accuracy ${pct(gen.defender_accuracy)}. ${verdict}.`
  }
  const evasionPhrase = evasionTrend === 'falling'
    ? `evasion dropped to ${pct(gen.evasion_rate)} — defender is catching more of them`
    : evasionTrend === 'climbing'
      ? `evasion climbed to ${pct(gen.evasion_rate)} — attackers found a weakness`
      : `evasion holding at ${pct(gen.evasion_rate)}`
  const accPhrase = accTrend === 'climbing'
    ? `accuracy up to ${pct(gen.defender_accuracy)}`
    : accTrend === 'falling'
      ? `accuracy slipped to ${pct(gen.defender_accuracy)}`
      : `accuracy steady at ${pct(gen.defender_accuracy)}`

  return `Generation ${idx + 1}: ${evasionPhrase}; ${accPhrase}. ${verdict}.`
}

export function narrateAll(generations) {
  return generations.map((g, i) => ({
    idx: i,
    text: narrateGeneration(g, i, generations),
  }))
}

export function narrateResult(result) {
  if (!result) return null
  const dropped = result.initial_evasion_rate - result.final_evasion_rate
  const held = result.final_evasion_rate <= 0.15
  if (held) {
    return `Defender held the line. Final evasion ${pct(result.final_evasion_rate)} (down from ${pct(result.initial_evasion_rate)} — a ${pct(dropped)} drop). Accuracy ${pct(result.final_defender_accuracy)}.`
  }
  return `Defender struggled. Final evasion ${pct(result.final_evasion_rate)} (started at ${pct(result.initial_evasion_rate)}). Try a higher hardening mix or more generations.`
}
