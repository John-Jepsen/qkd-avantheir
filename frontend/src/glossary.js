// Plain-English definitions for the jargon used in the dashboard.
// Used by the Tooltip component (hover help) and the Glossary accordion.

export const GLOSSARY = {
  qkd: {
    label: 'QKD',
    short: 'Quantum Key Distribution. Two parties share a random secret using single photons; physics guarantees an eavesdropper leaves fingerprints.',
  },
  bb84: {
    label: 'BB84',
    short: 'The original 1984 QKD protocol. Alice sends single photons; Bob measures them; they compare bases publicly and keep only matching bits.',
  },
  qber: {
    label: 'QBER',
    short: 'Quantum Bit Error Rate — how often Alice and Bob disagree on bits they should share. Above ~11% and they must abort: it means someone is listening.',
  },
  kme: {
    label: 'KME',
    short: 'Key Management Entity. The vendor-supplied REST server that hands out QKD-derived keys to applications via the ETSI 014 standard.',
  },
  evasion_rate: {
    label: 'Evasion rate',
    short: 'Fraction of attacks the defender failed to flag. Lower is better for the defender. 0% = perfect detector; 100% = blind detector.',
  },
  defender_accuracy: {
    label: 'Defender accuracy',
    short: 'Fraction of all decisions the ML detector got right (clean called clean, attack called attack). Higher is better.',
  },
  fitness: {
    label: 'Fitness',
    short: 'How well an attacker fooled the defender on this generation. Higher fitness = sneakier attack.',
  },
  generation: {
    label: 'Generation',
    short: 'One round of the co-evolution loop: attackers try, defender retrains, repeat.',
  },
  epsilon: {
    label: 'Epsilon',
    short: 'How aggressively attackers are allowed to perturb their signal. 0.01 = barely; 0.5 = wildly. Bounded by QKD physics either way.',
  },
  population: {
    label: 'Population',
    short: 'Number of attacker candidates evaluated per generation. Bigger = more diverse search, slower run.',
  },
  hardening: {
    label: 'Hardening',
    short: 'Showing the defender the latest evolved attacks during retraining so it stops falling for them.',
  },
  hardening_mix: {
    label: 'Hardening mix',
    short: 'What fraction of the defender\'s next training set is fresh adversarial examples vs original data. 0.3 means 30% adversarial.',
  },
  phylogeny: {
    label: 'Phylogeny',
    short: 'The family tree of attacks across generations — which attacker descended from which.',
  },
  perturbation: {
    label: 'Perturbation',
    short: 'A small change to a clean QKD signal designed to push it across the defender\'s decision boundary without triggering the physics-bounded checks.',
  },
  intercept_resend: {
    label: 'Intercept-resend',
    short: 'The textbook BB84 attack: Eve measures every photon and re-sends a fresh one to Bob. Lifts QBER to ~25% — easy to spot.',
  },
  pns_attack: {
    label: 'PNS attack',
    short: 'Photon-number-splitting. Eve siphons one photon from each pulse when more than one is sent. Stealthy unless decoy-state is used.',
  },
  beam_splitting: {
    label: 'Beam splitting',
    short: 'Eve taps a fraction of the channel using a beam splitter. Information-theoretic eavesdropping limited by the splitting ratio.',
  },
  trojan_horse: {
    label: 'Trojan horse',
    short: 'Eve sends bright probe pulses into Alice\'s device and reads the reflections. Hardware-side-channel attack, defeated by optical isolators.',
  },
}

export const GLOSSARY_ORDER = [
  'qkd', 'bb84', 'qber', 'kme', 'generation', 'population', 'epsilon',
  'fitness', 'evasion_rate', 'defender_accuracy', 'hardening', 'hardening_mix',
  'phylogeny', 'perturbation', 'intercept_resend', 'pns_attack',
  'beam_splitting', 'trojan_horse',
]
