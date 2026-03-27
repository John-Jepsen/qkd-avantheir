"""
Train all ML models and export labeled datasets to CSV.

Generates full-size training data from the BB84 simulator, trains each
model, saves trained models (.pkl) and labeled datasets (.csv) to the
data/ directory.

Usage:
    source .venv/bin/activate
    python train_all_models.py
"""

import os
import sys
import time
import csv
import numpy as np

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def save_csv(path, header, rows):
    """Write rows to a CSV file."""
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  Saved {len(rows)} rows → {path}")


# ── 1. Eavesdropper Classifier ───────────────────────────────────────────────

def train_eavesdrop_classifier():
    print("\n" + "=" * 60)
    print("1/5  EAVESDROPPER CLASSIFIER (Random Forest)")
    print("=" * 60)

    from ml_eavesdrop_classifier import EavesdropClassifier, FEATURE_NAMES

    clf = EavesdropClassifier()
    t0 = time.time()
    clf.generate_dataset(n_samples=6000, n_bits=4096)
    clf.train()
    elapsed = time.time() - t0
    print(f"  Training time: {elapsed:.1f}s")

    # Save model
    clf.save(os.path.join(DATA_DIR, "eavesdrop_model.pkl"))

    # Export labeled dataset
    header = FEATURE_NAMES + ["label"]
    rows = []
    for x, y in zip(clf.X_train, clf.y_train):
        rows.append(list(x) + [y])
    for x, y in zip(clf.X_test, clf.y_test):
        rows.append(list(x) + [y])
    save_csv(os.path.join(DATA_DIR, "eavesdrop_dataset.csv"), header, rows)

    return clf


# ── 2. Parameter Tuner ───────────────────────────────────────────────────────

def train_parameter_tuner():
    print("\n" + "=" * 60)
    print("2/5  PARAMETER TUNER (Gradient Boosted Regression)")
    print("=" * 60)

    from ml_parameter_tuner import ParameterTuner, FEATURE_NAMES

    tuner = ParameterTuner()
    t0 = time.time()
    tuner.generate_dataset(trials_per_combo=3)
    tuner.train()
    elapsed = time.time() - t0
    print(f"  Training time: {elapsed:.1f}s")

    tuner.save(os.path.join(DATA_DIR, "param_tuner_model.pkl"))

    header = FEATURE_NAMES + ["key_rate"]
    rows = []
    for x, y in zip(tuner.X_train, tuner.y_train):
        rows.append(list(x) + [y])
    for x, y in zip(tuner.X_test, tuner.y_test):
        rows.append(list(x) + [y])
    save_csv(os.path.join(DATA_DIR, "param_tuner_dataset.csv"), header, rows)

    return tuner


# ── 3. Noise Predictor ───────────────────────────────────────────────────────

def train_noise_predictor():
    print("\n" + "=" * 60)
    print("3/5  NOISE PREDICTOR (ARIMA Time-Series)")
    print("=" * 60)

    from ml_noise_predictor import NoisePredictor

    predictor = NoisePredictor(alert_threshold=0.09)

    # Generate multiple noise series with different seeds for variety
    all_series = []
    for seed in range(5):
        print(f"  Generating series {seed + 1}/5 (seed={seed})...")
        series = predictor.generate_noise_series(n_rounds=500, seed=seed)
        all_series.append(series)

    # Fit on the longest combined series
    combined = np.concatenate(all_series)
    print(f"  Combined series: {len(combined)} data points")

    t0 = time.time()
    predictor.fit(combined)
    elapsed = time.time() - t0
    print(f"  Fit time: {elapsed:.1f}s")

    # Forecast
    fc = predictor.forecast(steps=20)
    print(f"  Forecast (next 5): {', '.join(f'{v:.4f}' for v in fc.predicted_qber[:5])}")
    if fc.alert:
        print(f"  ALERT at step {fc.alert_step + 1}")

    # Walk-forward validation on first series
    print("  Running walk-forward validation...")
    metrics = predictor.rolling_forecast(all_series[0], window=100, steps=5)
    print(f"  MAE={metrics['mae']:.5f}, RMSE={metrics['rmse']:.5f}")

    # Export all series as labeled CSV
    header = ["series_id", "round", "qber"]
    rows = []
    for sid, series in enumerate(all_series):
        for rnd, val in enumerate(series):
            rows.append([sid, rnd, val])
    save_csv(os.path.join(DATA_DIR, "noise_series_dataset.csv"), header, rows)

    # Export forecast
    header = ["step", "predicted_qber", "ci_lower", "ci_upper"]
    rows = []
    for i in range(fc.steps_ahead):
        rows.append([i + 1, fc.predicted_qber[i],
                     fc.confidence_lower[i], fc.confidence_upper[i]])
    save_csv(os.path.join(DATA_DIR, "noise_forecast.csv"), header, rows)

    return predictor


# ── 4. KME Anomaly Detector ──────────────────────────────────────────────────

def train_kme_anomaly():
    print("\n" + "=" * 60)
    print("4/5  KME ANOMALY DETECTOR (Isolation Forest)")
    print("=" * 60)

    from ml_kme_anomaly import KMEAnomalyDetector, FEATURE_NAMES

    detector = KMEAnomalyDetector(contamination=0.05)

    t0 = time.time()
    print("  Generating normal traffic (5000 records)...")
    normal = detector.generate_normal_traffic(n_records=5000)
    detector.fit(normal)

    print("  Generating anomalous traffic (500 records)...")
    anomalous = detector.generate_anomalous_traffic(n_records=500)
    elapsed = time.time() - t0
    print(f"  Training time: {elapsed:.1f}s")

    # Evaluate
    normal_results = detector.detect(normal)
    anom_results = detector.detect(anomalous)
    normal_fp = sum(1 for r in normal_results if r.is_anomaly)
    anom_tp = sum(1 for r in anom_results if r.is_anomaly)
    print(f"  Normal: {len(normal_results)} windows, "
          f"FP={normal_fp} ({normal_fp / max(len(normal_results), 1):.1%})")
    print(f"  Attack: {len(anom_results)} windows, "
          f"TP={anom_tp} ({anom_tp / max(len(anom_results), 1):.1%})")

    # Export labeled traffic features
    header = FEATURE_NAMES + ["label", "anomaly_score"]
    rows = []
    for r in normal_results:
        rows.append([r.features[f] for f in FEATURE_NAMES] +
                    ["normal", r.anomaly_score])
    for r in anom_results:
        rows.append([r.features[f] for f in FEATURE_NAMES] +
                    ["anomalous", r.anomaly_score])
    save_csv(os.path.join(DATA_DIR, "kme_anomaly_dataset.csv"), header, rows)

    return detector


# ── 5. Attack Pattern Classifier ─────────────────────────────────────────────

def train_attack_classifier():
    print("\n" + "=" * 60)
    print("5/5  ATTACK PATTERN CLASSIFIER (Gradient Boosted)")
    print("=" * 60)

    from ml_attack_classifier import AttackClassifier, FEATURE_NAMES

    clf = AttackClassifier()
    t0 = time.time()
    clf.generate_dataset(n_samples=5000, n_bits=4096)
    clf.train()
    elapsed = time.time() - t0
    print(f"  Training time: {elapsed:.1f}s")

    clf.save(os.path.join(DATA_DIR, "attack_model.pkl"))

    header = FEATURE_NAMES + ["label"]
    rows = []
    for x, y in zip(clf.X_train, clf.y_train):
        rows.append(list(x) + [y])
    for x, y in zip(clf.X_test, clf.y_test):
        rows.append(list(x) + [y])
    save_csv(os.path.join(DATA_DIR, "attack_dataset.csv"), header, rows)

    return clf


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("QKD ML Training Pipeline")
    print("Generating labeled datasets and training all models...")
    print(f"Output directory: {DATA_DIR}")

    total_t0 = time.time()

    train_eavesdrop_classifier()
    train_parameter_tuner()
    train_noise_predictor()
    train_kme_anomaly()
    train_attack_classifier()

    total_elapsed = time.time() - total_t0

    print("\n" + "=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Total time: {total_elapsed:.1f}s")
    print(f"\nOutput files in {DATA_DIR}/:")
    for f in sorted(os.listdir(DATA_DIR)):
        size = os.path.getsize(os.path.join(DATA_DIR, f))
        if size > 1024 * 1024:
            print(f"  {f:40s} {size / 1024 / 1024:.1f} MB")
        else:
            print(f"  {f:40s} {size / 1024:.1f} KB")
