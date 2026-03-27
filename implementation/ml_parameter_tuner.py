"""
Adaptive BB84 Protocol Parameter Tuning via ML

Uses a trained regression model to recommend optimal protocol parameters
(n_bits, sample_fraction, block_size) that maximize the secure key rate
for a given observed channel noise level.

Approach:
  1. Grid-search the simulator across parameter combos and noise levels
  2. Record the resulting key rate (final_key bits / raw qubits sent)
  3. Train a gradient-boosted regressor to predict key rate from
     (noise_level, n_bits, sample_fraction, block_size)
  4. At runtime, sweep candidate parameters through the model and pick
     the combo with the highest predicted key rate

Usage:
    from ml_parameter_tuner import ParameterTuner

    tuner = ParameterTuner()
    tuner.generate_dataset()
    tuner.train()
    rec = tuner.recommend(observed_noise=0.03)
    print(rec)
"""

import pickle
import numpy as np
from dataclasses import dataclass
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from bb84_simulator import BB84Protocol


@dataclass
class ParameterRecommendation:
    observed_noise: float
    recommended_n_bits: int
    recommended_sample_fraction: float
    recommended_block_size: int
    predicted_key_rate: float
    all_candidates: list  # Top-5 parameter combos with predicted rates


# ── Parameter search space ────────────────────────────────────────────────────
NOISE_LEVELS = np.arange(0.005, 0.10, 0.005)
N_BITS_OPTIONS = [2048, 4096, 8192, 16384]
SAMPLE_FRACTIONS = [0.05, 0.08, 0.10, 0.15, 0.20]
BLOCK_SIZES = [4, 8, 16]
FEATURE_NAMES = ["noise_level", "n_bits", "sample_fraction", "block_size"]


class ParameterTuner:
    """
    Gradient Boosted Regressor that predicts key rate from protocol parameters.

    Key rate = (final_key_bits / raw_qubits_sent), measuring the protocol's
    efficiency at converting raw quantum transmissions into usable key material.
    """

    def __init__(self):
        self.model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42
        )
        self.is_trained = False

    def generate_dataset(self, trials_per_combo: int = 3):
        """
        Run the BB84 simulator across a grid of parameters and noise levels.
        Each combo is run multiple times to average out randomness.
        """
        features = []
        targets = []
        total = (len(NOISE_LEVELS) * len(N_BITS_OPTIONS) *
                 len(SAMPLE_FRACTIONS) * len(BLOCK_SIZES) * trials_per_combo)
        count = 0

        print(f"Generating {total} simulation runs...")

        for noise in NOISE_LEVELS:
            for n_bits in N_BITS_OPTIONS:
                for sf in SAMPLE_FRACTIONS:
                    for bs in BLOCK_SIZES:
                        for _ in range(trials_per_combo):
                            proto = BB84Protocol(
                                error_rate=float(noise),
                                eavesdrop=False,
                                sample_fraction=sf,
                            )
                            # Override block size for error correction
                            result = proto.run(n_bits=n_bits)

                            # Key rate: usable key bits per raw qubit sent
                            if result.secure:
                                key_rate = result.key_length_bits / n_bits
                            else:
                                key_rate = 0.0

                            features.append([float(noise), n_bits, sf, bs])
                            targets.append(key_rate)
                            count += 1

                        if count % 300 == 0:
                            print(f"  {count}/{total} runs complete...")

        X = np.array(features)
        y = np.array(targets)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        print(f"Dataset: {len(self.X_train)} train, {len(self.X_test)} test")
        return self

    def train(self):
        """Train the Gradient Boosting Regressor."""
        if not hasattr(self, "X_train") or self.X_train is None:
            raise RuntimeError("Call generate_dataset() first")

        self.model.fit(self.X_train, self.y_train)
        self.is_trained = True

        y_pred = self.model.predict(self.X_test)
        rmse = np.sqrt(mean_squared_error(self.y_test, y_pred))
        r2 = r2_score(self.y_test, y_pred)
        print(f"\n=== Model Performance ===")
        print(f"  RMSE: {rmse:.6f}")
        print(f"  R²:   {r2:.4f}")

        importances = self.model.feature_importances_
        print("\nFeature Importances:")
        for name, imp in sorted(zip(FEATURE_NAMES, importances),
                                key=lambda x: -x[1]):
            print(f"  {name:20s} {imp:.4f}")
        return self

    def recommend(self, observed_noise: float) -> ParameterRecommendation:
        """
        Given an observed noise level, predict the best parameter combination.
        Sweeps all candidate combos through the model and ranks by predicted key rate.
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained — call train() first")

        candidates = []
        for n_bits in N_BITS_OPTIONS:
            for sf in SAMPLE_FRACTIONS:
                for bs in BLOCK_SIZES:
                    candidates.append([observed_noise, n_bits, sf, bs])

        X_cand = np.array(candidates)
        predicted_rates = self.model.predict(X_cand)

        # Rank by predicted key rate
        ranked = sorted(zip(candidates, predicted_rates),
                        key=lambda x: -x[1])
        best = ranked[0]

        return ParameterRecommendation(
            observed_noise=observed_noise,
            recommended_n_bits=int(best[0][1]),
            recommended_sample_fraction=best[0][2],
            recommended_block_size=int(best[0][3]),
            predicted_key_rate=float(best[1]),
            all_candidates=[
                {
                    "n_bits": int(c[1]),
                    "sample_fraction": c[2],
                    "block_size": int(c[3]),
                    "predicted_key_rate": float(r),
                }
                for c, r in ranked[:5]
            ],
        )

    def save(self, path: str = "param_tuner_model.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str = "param_tuner_model.pkl") -> "ParameterTuner":
        obj = cls()
        with open(path, "rb") as f:
            obj.model = pickle.load(f)
        obj.is_trained = True
        return obj


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Adaptive BB84 Parameter Tuning")
    print("=" * 55)

    tuner = ParameterTuner()
    tuner.generate_dataset(trials_per_combo=2)  # Reduced for demo speed
    tuner.train()

    print("\n=== Parameter Recommendations ===\n")
    for noise in [0.01, 0.03, 0.05, 0.08]:
        rec = tuner.recommend(observed_noise=noise)
        print(f"  Noise={noise:.2f}  →  n_bits={rec.recommended_n_bits:>5}, "
              f"sample_frac={rec.recommended_sample_fraction:.2f}, "
              f"block_size={rec.recommended_block_size:>2}, "
              f"predicted_rate={rec.predicted_key_rate:.4f}")
