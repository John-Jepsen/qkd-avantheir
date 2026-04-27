"""
Adversarial Evolution Gym for QKD ML Models

DEAP-based genetic algorithm that evolves attack strategies to evade
QKD ML classifiers. Defenders retrain each generation with adversarial
samples mixed in (co-evolutionary via warm_start).

Core loop:
  1. Initialize population of attack parameter vectors within physics bounds
  2. Evaluate fitness = evasion rate against current defender models
  3. Selection, crossover, mutation (all physics-constrained)
  4. Retrain defenders with adversarial samples (incremental via warm_start)
  5. Record lineage in phylogeny tree
  6. Repeat for N generations

Usage:
    from adversarial_gym import AdversarialGym
    gym = AdversarialGym(population_size=50, n_generations=20)
    results = gym.evolve(X_train, y_train, X_test, y_test, model)
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional, Callable

import numpy as np
from deap import base, creator, tools, algorithms
from sklearn.base import clone

from features import FEATURE_NAMES
from physics_constraints import (
    BOUNDS_LOW, BOUNDS_HIGH, enforce_covariance, clip_to_bounds,
)
from adversarial_eval import generate_perturbations, evaluate_evasion


# ── Phylogeny tree ──────────────────────────────────────────────────────────

@dataclass
class PhylogenyNode:
    node_id: int
    generation: int
    fitness: float
    features: list[float]
    parent_id: Optional[int] = None
    attack_type: str = "evolved"

    def to_dict(self):
        return {
            "id": self.node_id,
            "generation": self.generation,
            "fitness": round(self.fitness, 4),
            "features": {n: round(v, 4) for n, v in zip(FEATURE_NAMES, self.features)},
            "parent_id": self.parent_id,
            "attack_type": self.attack_type,
        }


class PhylogenyTree:
    """Records parent-child lineage of evolving attack strategies."""

    def __init__(self):
        self.nodes: list[PhylogenyNode] = []
        self._next_id = 0

    def add_node(self, generation: int, fitness: float, features: list[float],
                 parent_id: Optional[int] = None, attack_type: str = "evolved") -> int:
        node_id = self._next_id
        self._next_id += 1
        self.nodes.append(PhylogenyNode(
            node_id=node_id, generation=generation, fitness=fitness,
            features=features, parent_id=parent_id, attack_type=attack_type,
        ))
        return node_id

    def to_dict(self) -> dict:
        return {
            "total_nodes": len(self.nodes),
            "generations": max((n.generation for n in self.nodes), default=0) + 1,
            "nodes": [n.to_dict() for n in self.nodes],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ── Generation result ───────────────────────────────────────────────────────

@dataclass
class GenerationResult:
    generation: int
    best_fitness: float
    avg_fitness: float
    evasion_rate: float
    defender_accuracy: float
    population_size: int
    elapsed_s: float


@dataclass
class EvolutionResult:
    generations: list[GenerationResult]
    phylogeny: PhylogenyTree
    final_evasion_rate: float
    initial_evasion_rate: float
    final_defender_accuracy: float
    total_elapsed_s: float


# ── Gym ─────────────────────────────────────────────────────────────────────

class AdversarialGym:
    """
    DEAP-based evolutionary gym for QKD adversarial attack generation.

    Parameters
    ----------
    population_size : int
        Number of attack vectors per generation.
    n_generations : int
        Number of evolutionary generations to run.
    mutation_rate : float
        Probability of mutating each feature in an individual.
    crossover_rate : float
        Probability of crossover between two parents.
    epsilon : float
        Perturbation strength for generating adversarial samples.
    hardening_mix : float
        Fraction of adversarial samples mixed into defender retraining.
    on_generation : callable, optional
        Callback(GenerationResult) called after each generation.
    """

    def __init__(
        self,
        population_size: int = 50,
        n_generations: int = 20,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.5,
        epsilon: float = 0.15,
        hardening_mix: float = 0.3,
        on_generation: Optional[Callable] = None,
    ):
        self.population_size = population_size
        self.n_generations = n_generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.epsilon = epsilon
        self.hardening_mix = hardening_mix
        self.on_generation = on_generation
        self.rng = np.random.default_rng(42)

    def evolve(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model,
    ) -> EvolutionResult:
        """
        Run the full evolutionary loop.

        Parameters
        ----------
        X_train, y_train : Training data for defender retraining.
        X_test, y_test : Test data for evaluation.
        model : A fitted sklearn classifier (will be cloned for hardening).
        """
        n_features = len(FEATURE_NAMES)
        phylogeny = PhylogenyTree()
        generation_results = []
        total_t0 = time.time()

        # Set up DEAP
        if not hasattr(creator, "FitnessMax"):
            creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        if not hasattr(creator, "Individual"):
            creator.create("Individual", list, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()

        # Attribute generators: random within physics bounds
        def rand_attr(i):
            return float(self.rng.uniform(BOUNDS_LOW[i], BOUNDS_HIGH[i]))

        toolbox.register("individual", tools.initIterate, creator.Individual,
                         lambda: [rand_attr(i) for i in range(n_features)])
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Fitness: evasion rate against current defender
        current_model = clone(model)
        current_model.fit(X_train, y_train)

        def eval_fitness(individual):
            features = np.array(individual).reshape(1, -1)
            features = enforce_covariance(features)
            pred = current_model.predict(features)[0]
            # Fitness = 1 if model is fooled (predicts clean for an attack),
            # scaled by distance from clean centroid
            if pred == "clean":
                return (1.0,)
            else:
                # Partial credit: confidence of the wrong prediction
                proba = current_model.predict_proba(features)[0]
                classes = list(current_model.classes_)
                clean_idx = classes.index("clean") if "clean" in classes else 0
                return (float(proba[clean_idx]),)

        toolbox.register("evaluate", eval_fitness)
        toolbox.register("select", tools.selTournament, tournsize=3)

        # Crossover: blend crossover (interpolate between parents)
        def cx_blend(ind1, ind2, alpha=0.3):
            for i in range(len(ind1)):
                gamma = (1 + 2 * alpha) * self.rng.random() - alpha
                v1, v2 = ind1[i], ind2[i]
                ind1[i] = float(np.clip(v1 + gamma * (v2 - v1), BOUNDS_LOW[i], BOUNDS_HIGH[i]))
                ind2[i] = float(np.clip(v2 + gamma * (v1 - v2), BOUNDS_LOW[i], BOUNDS_HIGH[i]))
            return ind1, ind2

        toolbox.register("mate", cx_blend)

        # Mutation: gaussian within bounds
        def mut_gaussian(individual):
            feature_ranges = BOUNDS_HIGH - BOUNDS_LOW
            for i in range(len(individual)):
                if self.rng.random() < self.mutation_rate:
                    sigma = feature_ranges[i] * 0.1
                    individual[i] = float(np.clip(
                        individual[i] + self.rng.normal(0, sigma),
                        BOUNDS_LOW[i], BOUNDS_HIGH[i],
                    ))
            # Enforce covariance after mutation
            arr = enforce_covariance(np.array(individual))
            for i in range(len(individual)):
                individual[i] = float(arr[i])
            return (individual,)

        toolbox.register("mutate", mut_gaussian)

        # Initialize population
        pop = toolbox.population(n=self.population_size)

        # Enforce physics on initial population
        for ind in pop:
            arr = enforce_covariance(np.array(ind))
            for i in range(len(ind)):
                ind[i] = float(arr[i])

        # Measure initial evasion
        initial_eval = evaluate_evasion(
            current_model, X_test, y_test, epsilon=self.epsilon, rng=self.rng
        )
        initial_evasion = initial_eval["evasion_rate"]

        # Track node IDs for phylogeny
        ind_node_ids = {}

        # ── Evolution loop ──────────────────────────────────────────────────
        for gen in range(self.n_generations):
            gen_t0 = time.time()

            # Evaluate fitness
            fitnesses = list(map(toolbox.evaluate, pop))
            for ind, fit in zip(pop, fitnesses):
                ind.fitness.values = fit

            # Record phylogeny for top individuals
            sorted_pop = sorted(pop, key=lambda x: x.fitness.values[0], reverse=True)
            top_n = min(5, len(sorted_pop))
            for ind in sorted_pop[:top_n]:
                parent = ind_node_ids.get(id(ind))
                node_id = phylogeny.add_node(
                    generation=gen,
                    fitness=ind.fitness.values[0],
                    features=list(ind),
                    parent_id=parent,
                )
                ind_node_ids[id(ind)] = node_id

            # Stats
            fits = [ind.fitness.values[0] for ind in pop]
            best_fit = max(fits)
            avg_fit = sum(fits) / len(fits)

            # Current evasion rate and defender accuracy
            ev = evaluate_evasion(
                current_model, X_test, y_test, epsilon=self.epsilon, rng=self.rng
            )
            from sklearn.metrics import accuracy_score
            defender_acc = accuracy_score(y_test, current_model.predict(X_test))

            gen_result = GenerationResult(
                generation=gen, best_fitness=best_fit, avg_fitness=avg_fit,
                evasion_rate=ev["evasion_rate"], defender_accuracy=defender_acc,
                population_size=len(pop), elapsed_s=time.time() - gen_t0,
            )
            generation_results.append(gen_result)

            if self.on_generation:
                self.on_generation(gen_result)

            print(f"  Gen {gen:3d}: best={best_fit:.3f} avg={avg_fit:.3f} "
                  f"evasion={ev['evasion_rate']:.1%} acc={defender_acc:.1%}")

            # Selection
            offspring = toolbox.select(pop, len(pop))
            offspring = list(map(lambda x: toolbox.clone(x), offspring))

            # Track parent IDs for phylogeny
            for child, parent in zip(offspring, pop):
                if id(parent) in ind_node_ids:
                    ind_node_ids[id(child)] = ind_node_ids[id(parent)]

            # Crossover
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if self.rng.random() < self.crossover_rate:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values

            # Mutation
            for mutant in offspring:
                if self.rng.random() < self.mutation_rate:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values

            pop[:] = offspring

            # ── Defender hardening (co-evolutionary) ────────────────────────
            # Generate adversarial samples from current population
            pop_features = np.array([list(ind) for ind in pop])
            pop_features = enforce_covariance(pop_features)
            adv_labels = current_model.predict(X_train[:len(pop_features)])

            # Mix adversarial samples into training data
            n_adv = int(len(X_train) * self.hardening_mix)
            if n_adv > len(pop_features):
                adv_idx = self.rng.choice(len(pop_features), size=n_adv, replace=True)
            else:
                adv_idx = self.rng.choice(len(pop_features), size=n_adv, replace=False)

            X_aug = np.vstack([X_train, pop_features[adv_idx]])
            # For augmented labels, use the original training labels + "clean" labels
            # for adversarial samples (they're evolved to look clean, so train the
            # defender that these ARE attacks, not clean)
            y_adv_correct = np.array(["eavesdrop"] * n_adv)  # teach defender these are attacks
            y_aug = np.concatenate([y_train, y_adv_correct])

            # Incremental retraining with warm_start
            current_model.set_params(warm_start=True)
            current_model.set_params(n_estimators=current_model.n_estimators + 5)
            current_model.fit(X_aug, y_aug)

        # Final evaluation
        final_eval = evaluate_evasion(
            current_model, X_test, y_test, epsilon=self.epsilon, rng=self.rng
        )
        final_acc = accuracy_score(y_test, current_model.predict(X_test))

        return EvolutionResult(
            generations=generation_results,
            phylogeny=phylogeny,
            final_evasion_rate=final_eval["evasion_rate"],
            initial_evasion_rate=initial_evasion,
            final_defender_accuracy=final_acc,
            total_elapsed_s=time.time() - total_t0,
        )


# ── Demo ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from bb84_simulator import BB84Protocol
    from ml_eavesdrop_classifier import EavesdropClassifier
    import ml_eavesdrop_classifier

    # Fast training with classical backend
    orig = ml_eavesdrop_classifier.BB84Protocol
    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)
    ml_eavesdrop_classifier.BB84Protocol = FastProto

    print("Training baseline classifier...")
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=600, n_bits=1024)
    clf.train()
    ml_eavesdrop_classifier.BB84Protocol = orig

    print("\nStarting evolutionary gym...")
    gym = AdversarialGym(
        population_size=30,
        n_generations=10,
        epsilon=0.15,
    )
    result = gym.evolve(
        clf.X_train, clf.y_train,
        clf.X_test, clf.y_test,
        clf.model,
    )

    print(f"\n{'=' * 60}")
    print("EVOLUTION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Generations:          {len(result.generations)}")
    print(f"  Initial evasion:      {result.initial_evasion_rate:.1%}")
    print(f"  Final evasion:        {result.final_evasion_rate:.1%}")
    print(f"  Final defender acc:   {result.final_defender_accuracy:.1%}")
    print(f"  Phylogeny nodes:      {len(result.phylogeny.nodes)}")
    print(f"  Total time:           {result.total_elapsed_s:.1f}s")
