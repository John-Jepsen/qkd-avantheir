"""
Multi-Class Attack Pattern Recognition for QKD

Extends the BB84 simulator with multiple attack models and trains a
classifier to distinguish attack signatures from their statistical
fingerprints. Supports five classes:

  1. clean           — no attack, background noise only
  2. intercept_resend — Eve intercepts every qubit (standard BB84 attack)
  3. beam_splitting   — Eve taps a fraction of photons from multi-photon pulses
  4. pns_attack       — Photon Number Splitting: Eve blocks single-photon pulses,
                        intercepts multi-photon ones
  5. trojan_horse     — Eve injects light into Bob's equipment, reads back-reflections

Each attack produces a distinct statistical signature in QBER, sift ratio,
error distribution, and timing characteristics.

Usage:
    from ml_attack_classifier import AttackClassifier

    clf = AttackClassifier()
    clf.generate_dataset(n_samples=3000)
    clf.train()
    result = clf.classify_from_bb84(bb84_result)
"""

import pickle
import numpy as np
from dataclasses import dataclass
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix

from bb84_simulator import BB84Protocol


@dataclass
class AttackDetectionResult:
    predicted_attack: str
    confidence: float
    probabilities: dict
    recommended_action: str


ATTACK_TYPES = [
    "clean",
    "intercept_resend",
    "beam_splitting",
    "pns_attack",
    "trojan_horse",
]

FEATURE_NAMES = [
    "qber",
    "sift_ratio",
    "error_variance",
    "max_burst_length",
    "low_block_fraction",   # Fraction of blocks with 0 errors
    "high_block_fraction",  # Fraction of blocks with >50% errors
    "error_autocorrelation",  # Correlation between consecutive block errors
    "sift_deviation",       # How far sift_ratio deviates from expected 0.5
]

# ── Attack simulation ─────────────────────────────────────────────────────────

def simulate_beam_splitting(n_bits: int = 4096, base_noise: float = 0.01,
                            tap_fraction: float = 0.15,
                            rng: np.random.Generator = None) -> dict:
    """
    Beam-splitting attack simulation.

    Eve uses a beam splitter to tap a fraction of multi-photon pulses.
    This adds moderate QBER with characteristic low error variance
    (errors are uniformly distributed, not bursty).
    """
    if rng is None:
        rng = np.random.default_rng()

    # Eve's tap introduces errors proportional to tap_fraction
    # but only on multi-photon pulses (~fraction of total)
    effective_noise = base_noise + tap_fraction * 0.15
    result = BB84Protocol(error_rate=effective_noise, eavesdrop=False).run(n_bits=n_bits)

    features = _extract_features(result)
    # Beam-splitting produces slightly lower sift ratio due to photon loss
    features[1] *= (1 - tap_fraction * 0.1)
    return {"features": features, "result": result}


def simulate_pns_attack(n_bits: int = 4096, base_noise: float = 0.01,
                         block_fraction: float = 0.3,
                         rng: np.random.Generator = None) -> dict:
    """
    Photon Number Splitting attack.

    Eve blocks single-photon pulses and intercepts multi-photon ones.
    This significantly reduces the sift ratio (fewer qubits get through)
    while keeping QBER relatively low on the surviving qubits.
    """
    if rng is None:
        rng = np.random.default_rng()

    # PNS: low QBER but significantly reduced sift ratio
    effective_noise = base_noise + 0.02
    result = BB84Protocol(error_rate=effective_noise, eavesdrop=False).run(n_bits=n_bits)

    features = _extract_features(result)
    # PNS dramatically reduces sift ratio
    features[1] *= (1 - block_fraction)
    # But keeps QBER low — the surviving qubits are less disturbed
    features[0] *= 0.8
    return {"features": features, "result": result}


def simulate_trojan_horse(n_bits: int = 4096, base_noise: float = 0.01,
                           injection_strength: float = 0.05,
                           rng: np.random.Generator = None) -> dict:
    """
    Trojan horse attack.

    Eve injects bright light into Bob's equipment and reads back-reflections.
    This causes distinctive error patterns: correlated errors in consecutive
    blocks (the injected light affects sequential measurements) and slightly
    elevated QBER with high autocorrelation.
    """
    if rng is None:
        rng = np.random.default_rng()

    effective_noise = base_noise + injection_strength
    result = BB84Protocol(error_rate=effective_noise, eavesdrop=False).run(n_bits=n_bits)

    features = _extract_features(result)
    # Trojan horse creates correlated errors — boost autocorrelation feature
    features[6] = min(1.0, features[6] + rng.uniform(0.2, 0.5))
    # Higher burst lengths from correlated injection
    features[3] = max(features[3], int(rng.integers(3, 7)))
    return {"features": features, "result": result}


def _extract_features(result) -> list[float]:
    """Extract the full feature vector from a BB84Result."""
    block_rates = result.block_error_rates or []

    # Basic features
    qber = result.qber
    sift_ratio = result.sift_ratio
    error_variance = result.error_variance
    max_burst = float(result.max_burst_length)

    # Block distribution features
    if block_rates:
        low_frac = sum(1 for r in block_rates if r == 0.0) / len(block_rates)
        high_frac = sum(1 for r in block_rates if r > 0.5) / len(block_rates)

        # Error autocorrelation (correlation of consecutive block error rates)
        if len(block_rates) > 2:
            br = np.array(block_rates)
            if br.std() > 1e-10:
                corr_val = np.corrcoef(br[:-1], br[1:])[0, 1]
                autocorr = float(corr_val) if np.isfinite(corr_val) else 0.0
            else:
                autocorr = 0.0
        else:
            autocorr = 0.0
    else:
        low_frac = 1.0
        high_frac = 0.0
        autocorr = 0.0

    sift_deviation = abs(sift_ratio - 0.5)

    return [qber, sift_ratio, error_variance, max_burst,
            low_frac, high_frac, autocorr, sift_deviation]


# ── Classifier ────────────────────────────────────────────────────────────────

class AttackClassifier:
    """
    Gradient Boosted multi-class classifier for QKD attack recognition.
    """

    ACTIONS = {
        "clean": "No action needed — channel is secure",
        "intercept_resend": "ABORT immediately — full eavesdropper detected. Rotate keys.",
        "beam_splitting": "Switch to decoy-state protocol to detect photon-number attacks",
        "pns_attack": "Enable decoy states + monitor photon statistics. Consider WCS source upgrade.",
        "trojan_horse": "Activate optical isolators. Check equipment for back-reflection leaks.",
    }

    def __init__(self):
        self.model = GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42
        )
        self.is_trained = False

    def generate_dataset(self, n_samples: int = 3000, n_bits: int = 4096):
        """Generate labeled training data across all attack types."""
        features = []
        labels = []
        rng = np.random.default_rng(42)
        per_class = n_samples // 5

        print(f"Generating {n_samples} samples ({per_class} per class)...")

        # Class 0: clean
        for _ in range(per_class):
            noise = rng.uniform(0.005, 0.04)
            result = BB84Protocol(error_rate=noise, eavesdrop=False).run(n_bits=n_bits)
            features.append(_extract_features(result))
            labels.append("clean")

        # Class 1: intercept-resend
        for _ in range(per_class):
            noise = rng.uniform(0.005, 0.03)
            result = BB84Protocol(error_rate=noise, eavesdrop=True).run(n_bits=n_bits)
            features.append(_extract_features(result))
            labels.append("intercept_resend")

        # Class 2: beam-splitting
        for _ in range(per_class):
            tap = rng.uniform(0.05, 0.25)
            noise = rng.uniform(0.005, 0.03)
            sim = simulate_beam_splitting(n_bits, noise, tap, rng)
            features.append(sim["features"])
            labels.append("beam_splitting")

        # Class 3: PNS
        for _ in range(per_class):
            block_frac = rng.uniform(0.15, 0.45)
            noise = rng.uniform(0.005, 0.03)
            sim = simulate_pns_attack(n_bits, noise, block_frac, rng)
            features.append(sim["features"])
            labels.append("pns_attack")

        # Class 4: Trojan horse
        for _ in range(per_class):
            strength = rng.uniform(0.02, 0.08)
            noise = rng.uniform(0.005, 0.03)
            sim = simulate_trojan_horse(n_bits, noise, strength, rng)
            features.append(sim["features"])
            labels.append("trojan_horse")

        X = np.array(features)
        y = np.array(labels)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        print(f"Dataset: {len(self.X_train)} train, {len(self.X_test)} test")
        return self

    def train(self):
        """Train the Gradient Boosting classifier."""
        if not hasattr(self, "X_train") or self.X_train is None:
            raise RuntimeError("Call generate_dataset() first")

        self.model.fit(self.X_train, self.y_train)
        self.is_trained = True

        y_pred = self.model.predict(self.X_test)
        print("\n=== Classification Report ===")
        print(classification_report(self.y_test, y_pred, target_names=ATTACK_TYPES))
        print("Confusion Matrix:")
        print(confusion_matrix(self.y_test, y_pred, labels=ATTACK_TYPES))

        importances = self.model.feature_importances_
        print("\nFeature Importances:")
        for name, imp in sorted(zip(FEATURE_NAMES, importances),
                                key=lambda x: -x[1]):
            print(f"  {name:24s} {imp:.4f}")
        return self

    def classify(self, features: list[float]) -> AttackDetectionResult:
        """Classify a single observation."""
        if not self.is_trained:
            raise RuntimeError("Model not trained")

        X = np.array([features])
        proba = self.model.predict_proba(X)[0]
        classes = list(self.model.classes_)
        pred_idx = np.argmax(proba)
        pred_label = classes[pred_idx]

        return AttackDetectionResult(
            predicted_attack=pred_label,
            confidence=float(proba[pred_idx]),
            probabilities={c: float(p) for c, p in zip(classes, proba)},
            recommended_action=self.ACTIONS.get(pred_label, "Investigate further"),
        )

    def classify_from_bb84(self, result) -> AttackDetectionResult:
        """Classify directly from a BB84Result."""
        return self.classify(_extract_features(result))

    def save(self, path: str = "attack_model.pkl"):
        with open(path, "wb") as f:
            pickle.dump(self.model, f)
        print(f"Model saved to {path}")

    @classmethod
    def load(cls, path: str = "attack_model.pkl") -> "AttackClassifier":
        obj = cls()
        with open(path, "rb") as f:
            obj.model = pickle.load(f)
        obj.is_trained = True
        return obj


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Multi-Class QKD Attack Pattern Recognition")
    print("=" * 55)

    clf = AttackClassifier()
    clf.generate_dataset(n_samples=1000)  # Reduced for demo speed
    clf.train()

    print("\n=== Live Attack Detection ===\n")
    rng = np.random.default_rng(123)

    tests = [
        ("Clean channel",
         lambda: _extract_features(
             BB84Protocol(error_rate=0.02).run(n_bits=4096))),
        ("Intercept-resend",
         lambda: _extract_features(
             BB84Protocol(error_rate=0.01, eavesdrop=True).run(n_bits=4096))),
        ("Beam-splitting (15% tap)",
         lambda: simulate_beam_splitting(4096, 0.01, 0.15, rng)["features"]),
        ("PNS attack (30% block)",
         lambda: simulate_pns_attack(4096, 0.01, 0.30, rng)["features"]),
        ("Trojan horse",
         lambda: simulate_trojan_horse(4096, 0.01, 0.05, rng)["features"]),
    ]

    for name, get_features in tests:
        features = get_features()
        det = clf.classify(features)
        print(f"  {name:30s} → {det.predicted_attack:20s} "
              f"({det.confidence:.1%})")
        print(f"    Action: {det.recommended_action}")
