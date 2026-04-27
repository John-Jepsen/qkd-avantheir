"""Tests for adversarial evolutionary gym."""

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

from adversarial_gym import AdversarialGym, PhylogenyTree
from physics_constraints import validate_features


@pytest.fixture(scope="module")
def gym_data():
    """Generate labeled dataset for gym testing."""
    rng = np.random.default_rng(42)
    n = 200
    X = rng.uniform(0, 0.3, size=(n, 8))
    X[:, 1] = rng.uniform(0.4, 0.55, size=n)
    X[:, 7] = np.abs(X[:, 1] - 0.5)
    y = np.array(["clean"] * 100 + ["eavesdrop"] * 100)
    X[100:, 0] = rng.uniform(0.15, 0.3, size=100)

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X[:160], y[:160])

    return X[:160], y[:160], X[160:], y[160:], model


def test_phylogeny_tree_add_and_export():
    tree = PhylogenyTree()
    id1 = tree.add_node(0, 0.5, [0.1] * 8)
    id2 = tree.add_node(1, 0.7, [0.2] * 8, parent_id=id1)
    assert len(tree.nodes) == 2
    d = tree.to_dict()
    assert d["total_nodes"] == 2
    assert d["nodes"][1]["parent_id"] == id1


def test_phylogeny_tree_json():
    tree = PhylogenyTree()
    tree.add_node(0, 0.5, [0.1] * 8)
    j = tree.to_json()
    assert '"total_nodes": 1' in j


def test_gym_evolves(gym_data):
    X_train, y_train, X_test, y_test, model = gym_data

    gym = AdversarialGym(
        population_size=10,
        n_generations=3,
        epsilon=0.15,
    )
    result = gym.evolve(X_train, y_train, X_test, y_test, model)

    assert len(result.generations) == 3
    assert result.phylogeny is not None
    assert len(result.phylogeny.nodes) > 0
    assert result.total_elapsed_s > 0


def test_gym_produces_generation_results(gym_data):
    X_train, y_train, X_test, y_test, model = gym_data

    gym = AdversarialGym(population_size=10, n_generations=2)
    result = gym.evolve(X_train, y_train, X_test, y_test, model)

    gen = result.generations[0]
    assert 0.0 <= gen.best_fitness <= 1.0
    assert 0.0 <= gen.avg_fitness <= 1.0
    assert 0.0 <= gen.evasion_rate <= 1.0
    assert 0.0 <= gen.defender_accuracy <= 1.0


def test_gym_callback_fires(gym_data):
    X_train, y_train, X_test, y_test, model = gym_data
    called = []

    gym = AdversarialGym(
        population_size=10,
        n_generations=2,
        on_generation=lambda g: called.append(g.generation),
    )
    gym.evolve(X_train, y_train, X_test, y_test, model)

    assert called == [0, 1]
