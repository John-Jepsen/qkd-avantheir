"""
ML-Based Eavesdropper Detection for BB84 QKD

Replaces the hard 11% QBER threshold with a trained classifier that uses
multiple statistical features from the quantum channel:

  - QBER (overall estimated error rate)
  - Sift ratio (sifted bits / raw bits sent)
  - Block error variance (variance of per-block error rates)
  - Max burst length (longest consecutive error run)

The classifier can detect sophisticated partial-intercept attacks that stay
below the 11% QBER threshold but leave statistical fingerprints in the
block-level error distribution.

Usage:
    from ml_eavesdrop_classifier import EavesdropClassifier

    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=5000)
    clf.train()
    clf.save("eavesdrop_model.pkl")

    # Later:
    clf = EavesdropClassifier.load("eavesdrop_model.pkl")
    prediction = clf.predict(qber=0.08, sift_ratio=0.49,
                             error_variance=0.012, max_burst=3)
"""

import joblib
import numpy as np
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from bb84_simulator import BB84Protocol
from features import extract_features, FEATURE_NAMES


@dataclass
class DetectionResult:
    predicted_label: str          # "clean", "eavesdrop", "partial_intercept"
    confidence: float             # Probability of the predicted class
    probabilities: dict           # Per-class probabilities
    threshold_would_detect: bool  # Whether the 11% QBER threshold would catch it


LABELS = ["clean", "eavesdrop", "partial_intercept"]


class EavesdropClassifier:
    """
    Random Forest classifier for eavesdropper detection.

    Trained on simulated BB84 runs with three classes:
      - clean: no eavesdropper (background noise only)
      - eavesdrop: full intercept-resend attack
      - partial_intercept: Eve intercepts only a fraction of qubits
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100, max_depth=10, random_state=42
        )
        self.X_train = None
        self.y_train = None
        self.X_test = None
        self.y_test = None
        self.is_trained = False

    def generate_dataset(self, n_samples: int = 5000, n_bits: int = 4096):
        """
        Generate labeled training data from the BB84 simulator.

        Produces three classes by varying eavesdrop and error_rate parameters:
          - clean: error_rate in [0.005, 0.05], no eavesdrop
          - eavesdrop: full intercept-resend (error_rate + ~25% from Eve)
          - partial_intercept: simulated by elevated noise in [0.06, 0.10]
            representing Eve intercepting a fraction of qubits
        """
        features = []
        labels = []
        rng = np.random.default_rng(42)

        samples_per_class = n_samples // 3

        # Class 0: clean channel
        for _ in range(samples_per_class):
            noise = rng.uniform(0.005, 0.05)
            result = BB84Protocol(error_rate=noise, eavesdrop=False).run(n_bits=n_bits)
            features.append(self._extract(result))
            labels.append("clean")

        # Class 1: full intercept-resend eavesdropper
        for _ in range(samples_per_class):
            noise = rng.uniform(0.005, 0.03)
            result = BB84Protocol(error_rate=noise, eavesdrop=True).run(n_bits=n_bits)
            features.append(self._extract(result))
            labels.append("eavesdrop")

        # Class 2: partial intercept — Eve intercepts a fraction of qubits
        # using the real intercept-resend model. This produces naturally
        # distinct signatures: bimodal error distribution (intercepted blocks
        # have ~25% QBER, clean blocks have background noise only), clustered
        # error bursts, and higher error variance vs. uniform channel noise.
        for _ in range(samples_per_class):
            noise = rng.uniform(0.005, 0.03)
            fraction = rng.uniform(0.10, 0.50)
            result = BB84Protocol(
                error_rate=noise, eavesdrop=True,
                eavesdrop_fraction=fraction,
            ).run(n_bits=n_bits)
            features.append(self._extract(result))
            labels.append("partial_intercept")

        X = np.array(features)
        y = np.array(labels)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        print(f"Dataset: {len(self.X_train)} train, {len(self.X_test)} test")
        return self

    def train(self):
        """Train the Random Forest classifier."""
        if self.X_train is None:
            raise RuntimeError("Call generate_dataset() first")

        self.model.fit(self.X_train, self.y_train)
        self.is_trained = True

        y_pred = self.model.predict(self.X_test)
        print("\n=== Classification Report ===")
        print(classification_report(self.y_test, y_pred, target_names=LABELS))
        print("Confusion Matrix:")
        print(confusion_matrix(self.y_test, y_pred, labels=LABELS))

        importances = self.model.feature_importances_
        print("\nFeature Importances:")
        for name, imp in sorted(zip(FEATURE_NAMES, importances),
                                key=lambda x: -x[1]):
            print(f"  {name:20s} {imp:.4f}")

        return self

    def predict(self, qber: float, sift_ratio: float,
                error_variance: float, max_burst: int,
                low_block_fraction: float = 0.0,
                high_block_fraction: float = 0.0,
                error_autocorrelation: float = 0.0,
                sift_deviation: float = 0.0,
                variance_ratio: float = 0.0,
                block_entropy: float = 0.0,
                burst_qber_product: float = 0.0,
                block_kurtosis: float = 0.0) -> DetectionResult:
        """Classify a single BB84 run using 12 features."""
        if not self.is_trained:
            raise RuntimeError("Model not trained — call train() first")

        X = np.array([[qber, sift_ratio, error_variance, max_burst,
                        low_block_fraction, high_block_fraction,
                        error_autocorrelation, sift_deviation,
                        variance_ratio, block_entropy,
                        burst_qber_product, block_kurtosis]])
        proba = self.model.predict_proba(X)[0]
        classes = list(self.model.classes_)
        pred_idx = np.argmax(proba)

        return DetectionResult(
            predicted_label=classes[pred_idx],
            confidence=float(proba[pred_idx]),
            probabilities={c: float(p) for c, p in zip(classes, proba)},
            threshold_would_detect=qber > 0.11,
        )

    def predict_from_result(self, result) -> DetectionResult:
        """Classify directly from a BB84Result object."""
        feats = extract_features(result)
        return self.predict(
            qber=feats[0], sift_ratio=feats[1],
            error_variance=feats[2], max_burst=int(feats[3]),
            low_block_fraction=feats[4], high_block_fraction=feats[5],
            error_autocorrelation=feats[6], sift_deviation=feats[7],
            variance_ratio=feats[8], block_entropy=feats[9],
            burst_qber_product=feats[10], block_kurtosis=feats[11],
        )

    def save(self, path: str = "eavesdrop_model.pkl"):
        """Serialize the trained model to disk."""
        joblib.dump(self.model, path)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str = "eavesdrop_model.pkl") -> "EavesdropClassifier":
        """Load a previously trained model."""
        obj = cls()
        obj.model = joblib.load(path)
        obj.is_trained = True
        return obj

    @staticmethod
    def _extract(result) -> list[float]:
        """Extract ML features from a BB84Result (8-feature vector)."""
        return extract_features(result)


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("ML Eavesdropper Detection for BB84 QKD")
    print("=" * 55)

    # Train
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=600)  # Small for demo speed
    clf.train()

    # Test against live simulator runs
    print("\n=== Live Detection Tests ===\n")
    scenarios = [
        ("Clean channel (1% noise)", {"error_rate": 0.01, "eavesdrop": False}),
        ("Clean channel (4% noise)", {"error_rate": 0.04, "eavesdrop": False}),
        ("Partial intercept (~8%)",  {"error_rate": 0.08, "eavesdrop": False}),
        ("Full eavesdropper",        {"error_rate": 0.01, "eavesdrop": True}),
    ]

    for name, kwargs in scenarios:
        result = BB84Protocol(**kwargs).run(n_bits=4096)
        det = clf.predict_from_result(result)
        flag = " *** MISSED by threshold!" if (
            det.predicted_label != "clean" and not det.threshold_would_detect
        ) else ""
        print(f"  {name:30s}  QBER={result.qber:.3f}  "
              f"ML={det.predicted_label:20s} ({det.confidence:.1%})  "
              f"Threshold={'ABORT' if det.threshold_would_detect else 'PASS'}{flag}")
