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

const ATTACK_TYPES = ['intercept_resend', 'beam_splitting', 'pns_attack', 'trojan_horse']

function buildSamplePhylogeny() {
  const nodes = []
  let id = 0
  // Generation 0: seed population, no parent
  for (let i = 0; i < 6; i++) {
    nodes.push({
      id: id++,
      parent_id: null,
      generation: 0,
      attack_type: ATTACK_TYPES[i % ATTACK_TYPES.length],
      fitness: 0.2 + Math.random() * 0.25,
      features: { qber: 0.12 + Math.random() * 0.05 },
    })
  }
  // Generations 1-9: each has 4-6 children, parents drawn from previous gen
  for (let g = 1; g < 10; g++) {
    const prevGen = nodes.filter(n => n.generation === g - 1)
    const childCount = 4 + Math.floor(Math.random() * 3)
    for (let c = 0; c < childCount; c++) {
      const parent = prevGen[Math.floor(Math.random() * prevGen.length)]
      nodes.push({
        id: id++,
        parent_id: parent.id,
        generation: g,
        attack_type: Math.random() < 0.4 ? 'evolved' : parent.attack_type,
        fitness: Math.max(0.05, parent.fitness - 0.02 - Math.random() * 0.03),
        features: { qber: 0.11 + Math.random() * 0.06 },
      })
    }
  }
  return { nodes, total_nodes: nodes.length }
}

export const SAMPLE_PHYLOGENY = buildSamplePhylogeny()

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
