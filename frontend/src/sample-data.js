// Pre-baked snapshot of a representative successful run.
// Shown as the empty-state placeholder so first-time visitors see filled
// charts and a result banner instead of empty panels.

export const SAMPLE_GENERATIONS = [
  { evasion_rate: 0.52, defender_accuracy: 0.71, best_fitness: 0.51, avg_fitness: 0.34 },
  { evasion_rate: 0.46, defender_accuracy: 0.74, best_fitness: 0.49, avg_fitness: 0.31 },
  { evasion_rate: 0.39, defender_accuracy: 0.79, best_fitness: 0.44, avg_fitness: 0.28 },
  { evasion_rate: 0.31, defender_accuracy: 0.83, best_fitness: 0.38, avg_fitness: 0.25 },
  { evasion_rate: 0.26, defender_accuracy: 0.86, best_fitness: 0.33, avg_fitness: 0.22 },
  { evasion_rate: 0.20, defender_accuracy: 0.89, best_fitness: 0.28, avg_fitness: 0.19 },
  { evasion_rate: 0.16, defender_accuracy: 0.91, best_fitness: 0.24, avg_fitness: 0.16 },
  { evasion_rate: 0.12, defender_accuracy: 0.93, best_fitness: 0.20, avg_fitness: 0.14 },
  { evasion_rate: 0.09, defender_accuracy: 0.94, best_fitness: 0.17, avg_fitness: 0.12 },
  { evasion_rate: 0.06, defender_accuracy: 0.96, best_fitness: 0.14, avg_fitness: 0.10 },
]

// Real backend stores `features` as a 12-element list with qber at index 0
// and sets attack_type to "evolved" for every gym-spawned individual. We
// mirror that shape exactly so the dashboard renders sample and real runs
// identically.
function makeFeatureVec(qber) {
  return [
    qber,        // 0: qber
    0.5,         // 1: sift_ratio
    0.001,       // 2: error_variance
    3,           // 3: max_burst
    0,           // 4: error_autocorrelation
    -1,          // 5: low_block_fraction
    0,           // 6: high_block_fraction
    1.0,         // 7: variance_ratio
    0.5,         // 8: block_entropy
    qber * 3,    // 9: burst_qber_product
    0,           // 10
    0,           // 11
  ]
}

function buildSamplePhylogeny() {
  const nodes = []
  let id = 0
  for (let i = 0; i < 6; i++) {
    const qber = 0.14 + Math.random() * 0.06   // above the 11% rule
    nodes.push({
      id: id++,
      parent_id: null,
      generation: 0,
      attack_type: 'evolved',
      fitness: 0.2 + Math.random() * 0.25,
      features: makeFeatureVec(qber),
    })
  }
  for (let g = 1; g < 10; g++) {
    const prevGen = nodes.filter(n => n.generation === g - 1)
    const childCount = 4 + Math.floor(Math.random() * 3)
    for (let c = 0; c < childCount; c++) {
      const parent = prevGen[Math.floor(Math.random() * prevGen.length)]
      // Later generations are more subtle — their QBER drifts down toward
      // and past the 11% threshold so the visual reads "static rule misses
      // these but ML catches them"
      const qber = Math.max(0.04, 0.16 - g * 0.012 + (Math.random() - 0.5) * 0.04)
      nodes.push({
        id: id++,
        parent_id: parent.id,
        generation: g,
        attack_type: 'evolved',
        fitness: Math.max(0.05, parent.fitness - 0.02 - Math.random() * 0.03),
        features: makeFeatureVec(qber),
      })
    }
  }
  return { nodes, total_nodes: nodes.length }
}

export const SAMPLE_PHYLOGENY = buildSamplePhylogeny()

// Extract QBER from a phylogeny node regardless of features shape.
// Backend → list with qber at index 0. Older code → dict with .qber.
export function nodeQber(node) {
  const f = node?.features
  if (f == null) return null
  if (Array.isArray(f)) return f[0]
  if (typeof f === 'object') return f.qber ?? null
  return null
}

// Static 11% rule: catch rate = fraction of attackers whose QBER ≥ 0.11.
// If the phylogeny has no usable QBER values, fall back to the supplied
// default so the card still renders.
export function staticRuleCatchRate(phylogeny, fallback = 0.62) {
  if (!phylogeny?.nodes?.length) return fallback
  let caught = 0
  let total = 0
  for (const n of phylogeny.nodes) {
    const q = nodeQber(n)
    if (q == null) continue
    total += 1
    if (q >= 0.11) caught += 1
  }
  if (!total) return fallback
  return caught / total
}

export function averageQber(phylogeny) {
  if (!phylogeny?.nodes?.length) return null
  let sum = 0
  let count = 0
  for (const n of phylogeny.nodes) {
    const q = nodeQber(n)
    if (q == null) continue
    sum += q
    count += 1
  }
  return count ? sum / count : null
}

export function attackerCounts(phylogeny) {
  if (!phylogeny?.nodes?.length) return { aboveThreshold: 0, belowThreshold: 0, total: 0 }
  let above = 0
  let below = 0
  let total = 0
  for (const n of phylogeny.nodes) {
    const q = nodeQber(n)
    if (q == null) continue
    total += 1
    if (q >= 0.11) above += 1
    else below += 1
  }
  return { aboveThreshold: above, belowThreshold: below, total }
}

export const SAMPLE_RESULT = {
  initial_evasion_rate: 0.52,
  final_evasion_rate: 0.06,
  final_defender_accuracy: 0.96,
  phylogeny: SAMPLE_PHYLOGENY,
  total_elapsed_s: 28,
  // Comparison baseline: static-threshold detector's catch rate on the same attacks.
  // Hand-tuned to reflect a representative gap; sourced from poc/docs/RESULTS.md
  // narrative ("static threshold can't separate noisy clean from gentle attack").
  static_threshold_catch_rate: 0.62,
  ml_defender_catch_rate: 0.94,
  is_sample: true,
}
