"""
Anomaly Detection on ETSI QKD 014 Key Management Traffic

Monitors key request patterns from the KME server and flags anomalous
behavior using an Isolation Forest model. Detects:

  - Unusual request rates (burst or suspiciously low)
  - Abnormal key sizes or counts per request
  - Timing anomalies (irregular inter-request intervals)
  - Unexpected SAE ID patterns (new or rarely-seen clients)

The system learns normal traffic patterns and flags deviations that may
indicate key exhaustion attacks, replay attempts, or unauthorized access.

Usage:
    from ml_kme_anomaly import KMEAnomalyDetector

    detector = KMEAnomalyDetector()
    detector.fit(normal_traffic)
    results = detector.detect(new_traffic)
"""

import numpy as np
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


@dataclass
class TrafficRecord:
    """Single key management API request."""
    timestamp: float        # Unix epoch seconds
    endpoint: str           # "enc_keys", "dec_keys", "status"
    sae_id: str
    keys_requested: int
    key_size_bits: int
    keys_returned: int
    response_time_ms: float


@dataclass
class AnomalyResult:
    is_anomaly: bool
    anomaly_score: float        # Lower = more anomalous (Isolation Forest convention)
    features: dict              # The computed feature values
    explanation: str            # Human-readable reason


FEATURE_NAMES = [
    "request_rate_1min",        # Requests in last 60s window
    "mean_keys_requested",      # Avg keys per request in window
    "mean_key_size",            # Avg key size in window
    "inter_request_std",        # Std dev of inter-request intervals
    "enc_dec_ratio",            # Ratio of enc_keys to dec_keys requests
    "unique_sae_count",         # Distinct SAE IDs in window
    "max_burst_rate",           # Max requests in any 10s sub-window
    "failed_ratio",             # Fraction of requests returning 0 keys
]


class KMEAnomalyDetector:
    """
    Isolation Forest anomaly detector for KME traffic patterns.

    Processes sliding windows of traffic records into statistical features,
    then classifies each window as normal or anomalous.
    """

    def __init__(self, contamination: float = 0.05, window_size: int = 60):
        self.model = IsolationForest(
            n_estimators=100, contamination=contamination,
            random_state=42, n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.window_size = window_size  # seconds
        self.is_trained = False

    def generate_normal_traffic(self, n_records: int = 2000,
                                seed: int = 42) -> list[TrafficRecord]:
        """
        Generate synthetic normal KME traffic.

        Normal pattern: steady request rate (~1-3/min), consistent key sizes,
        balanced enc/dec ratio, few distinct SAEs.
        """
        rng = np.random.default_rng(seed)
        records = []
        t = 0.0

        sae_ids = [f"sae-{i:03d}" for i in range(5)]

        for _ in range(n_records):
            # Normal inter-request interval: 20-60 seconds
            t += rng.exponential(30)
            endpoint = rng.choice(["enc_keys", "dec_keys", "status"],
                                  p=[0.45, 0.45, 0.10])
            records.append(TrafficRecord(
                timestamp=t,
                endpoint=endpoint,
                sae_id=rng.choice(sae_ids),
                keys_requested=int(rng.integers(1, 5)),
                key_size_bits=int(rng.choice([128, 256, 256, 256, 512])),
                keys_returned=int(rng.integers(1, 5)),
                response_time_ms=float(rng.normal(50, 10)),
            ))

        return records

    def generate_anomalous_traffic(self, n_records: int = 200,
                                   seed: int = 99) -> list[TrafficRecord]:
        """
        Generate synthetic anomalous traffic patterns:
          - Burst attacks (many requests in short period)
          - Key exhaustion (requesting max keys repeatedly)
          - Unknown SAE IDs
          - Size probing (unusual key sizes)
        """
        rng = np.random.default_rng(seed)
        records = []
        t = 0.0

        for _ in range(n_records):
            attack_type = rng.choice(["burst", "exhaustion", "unknown_sae", "probe"])

            if attack_type == "burst":
                t += rng.exponential(2)  # Very fast requests
                records.append(TrafficRecord(
                    timestamp=t, endpoint="enc_keys",
                    sae_id="sae-001",
                    keys_requested=int(rng.integers(10, 20)),
                    key_size_bits=256,
                    keys_returned=int(rng.integers(10, 20)),
                    response_time_ms=float(rng.normal(200, 50)),
                ))
            elif attack_type == "exhaustion":
                t += rng.exponential(10)
                records.append(TrafficRecord(
                    timestamp=t, endpoint="enc_keys",
                    sae_id="sae-002",
                    keys_requested=20,  # Max per request
                    key_size_bits=1024,  # Max size
                    keys_returned=20,
                    response_time_ms=float(rng.normal(500, 100)),
                ))
            elif attack_type == "unknown_sae":
                t += rng.exponential(15)
                records.append(TrafficRecord(
                    timestamp=t, endpoint="enc_keys",
                    sae_id=f"sae-unknown-{rng.integers(100, 999)}",
                    keys_requested=int(rng.integers(1, 5)),
                    key_size_bits=256,
                    keys_returned=0,  # Likely rejected
                    response_time_ms=float(rng.normal(20, 5)),
                ))
            else:  # probe
                t += rng.exponential(20)
                records.append(TrafficRecord(
                    timestamp=t, endpoint="enc_keys",
                    sae_id="sae-003",
                    keys_requested=1,
                    key_size_bits=int(rng.choice([64, 65, 96, 1024])),
                    keys_returned=int(rng.choice([0, 1])),
                    response_time_ms=float(rng.normal(30, 10)),
                ))

        return records

    def _extract_window_features(self, records: list[TrafficRecord],
                                 window_start: float,
                                 window_end: float) -> list[float]:
        """Compute statistical features for a time window."""
        window = [r for r in records
                  if window_start <= r.timestamp < window_end]

        if len(window) < 2:
            return [0.0] * len(FEATURE_NAMES)

        duration = window_end - window_start

        # Request rate
        request_rate = len(window) / (duration / 60.0) if duration > 0 else 0

        # Key statistics
        mean_keys = np.mean([r.keys_requested for r in window])
        mean_size = np.mean([r.key_size_bits for r in window])

        # Inter-request timing
        timestamps = sorted(r.timestamp for r in window)
        intervals = np.diff(timestamps)
        inter_std = float(np.std(intervals)) if len(intervals) > 0 else 0

        # Endpoint ratio
        enc_count = sum(1 for r in window if r.endpoint == "enc_keys")
        dec_count = sum(1 for r in window if r.endpoint == "dec_keys")
        enc_dec_ratio = enc_count / max(dec_count, 1)

        # Unique SAEs
        unique_saes = len(set(r.sae_id for r in window))

        # Burst detection (max requests in any 10s sub-window)
        max_burst = 0
        for r in window:
            burst = sum(1 for r2 in window
                        if r.timestamp <= r2.timestamp < r.timestamp + 10)
            max_burst = max(max_burst, burst)

        # Failed ratio
        failed = sum(1 for r in window if r.keys_returned == 0)
        failed_ratio = failed / len(window)

        return [
            request_rate, float(mean_keys), float(mean_size),
            inter_std, enc_dec_ratio, float(unique_saes),
            float(max_burst), failed_ratio,
        ]

    def _records_to_features(self, records: list[TrafficRecord],
                             stride: int = 30) -> np.ndarray:
        """Convert a traffic log into windowed feature matrix."""
        if not records:
            return np.empty((0, len(FEATURE_NAMES)))

        t_min = records[0].timestamp
        t_max = records[-1].timestamp
        features = []

        t = t_min
        while t + self.window_size <= t_max:
            feat = self._extract_window_features(records, t, t + self.window_size)
            features.append(feat)
            t += stride

        return np.array(features) if features else np.empty((0, len(FEATURE_NAMES)))

    def fit(self, normal_records: list[TrafficRecord]):
        """Train the Isolation Forest on normal traffic patterns."""
        X = self._records_to_features(normal_records)
        if len(X) == 0:
            raise RuntimeError("Not enough records to extract features")

        self.scaler.fit(X)
        X_scaled = self.scaler.transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True

        scores = self.model.decision_function(X_scaled)
        print(f"Trained on {len(X)} windows from {len(normal_records)} records")
        print(f"  Normal score range: [{scores.min():.3f}, {scores.max():.3f}]")
        return self

    def detect(self, records: list[TrafficRecord]) -> list[AnomalyResult]:
        """Classify traffic windows as normal or anomalous."""
        if not self.is_trained:
            raise RuntimeError("Call fit() first")

        X = self._records_to_features(records)
        if len(X) == 0:
            return []

        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        scores = self.model.decision_function(X_scaled)

        results = []
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            feat_dict = {name: float(X[i, j])
                         for j, name in enumerate(FEATURE_NAMES)}
            explanation = self._explain(feat_dict, pred == -1)
            results.append(AnomalyResult(
                is_anomaly=(pred == -1),
                anomaly_score=float(score),
                features=feat_dict,
                explanation=explanation,
            ))
        return results

    def _explain(self, features: dict, is_anomaly: bool) -> str:
        """Generate a human-readable explanation for the detection."""
        if not is_anomaly:
            return "Normal traffic pattern"

        reasons = []
        if features["request_rate_1min"] > 10:
            reasons.append(f"high request rate ({features['request_rate_1min']:.1f}/min)")
        if features["max_burst_rate"] > 5:
            reasons.append(f"burst detected ({features['max_burst_rate']:.0f} in 10s)")
        if features["mean_keys_requested"] > 10:
            reasons.append(f"large key requests (avg {features['mean_keys_requested']:.1f})")
        if features["unique_sae_count"] > 8:
            reasons.append(f"many SAE IDs ({features['unique_sae_count']:.0f})")
        if features["failed_ratio"] > 0.3:
            reasons.append(f"high failure rate ({features['failed_ratio']:.0%})")
        if features["mean_key_size"] > 800:
            reasons.append(f"unusual key sizes (avg {features['mean_key_size']:.0f} bits)")

        return "Anomaly: " + ("; ".join(reasons) if reasons else "unusual pattern")


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("KME Traffic Anomaly Detection")
    print("=" * 55)

    detector = KMEAnomalyDetector(contamination=0.05)

    # Generate and train on normal traffic
    print("\nGenerating normal traffic (2000 records)...")
    normal = detector.generate_normal_traffic(n_records=2000)
    print(f"  Time span: {normal[-1].timestamp - normal[0].timestamp:.0f}s")
    detector.fit(normal)

    # Test on normal traffic
    print("\nTesting on normal traffic...")
    normal_results = detector.detect(normal)
    n_anom = sum(1 for r in normal_results if r.is_anomaly)
    print(f"  Windows: {len(normal_results)}, "
          f"Anomalies: {n_anom} ({n_anom / max(len(normal_results), 1):.1%})")

    # Test on anomalous traffic
    print("\nGenerating anomalous traffic (200 records)...")
    anomalous = detector.generate_anomalous_traffic(n_records=200)
    anom_results = detector.detect(anomalous)
    n_anom = sum(1 for r in anom_results if r.is_anomaly)
    print(f"  Windows: {len(anom_results)}, "
          f"Anomalies: {n_anom} ({n_anom / max(len(anom_results), 1):.1%})")

    # Show sample anomalies
    anomalies = [r for r in anom_results if r.is_anomaly]
    if anomalies:
        print(f"\nSample anomaly explanations:")
        for a in anomalies[:5]:
            print(f"  Score={a.anomaly_score:+.3f}  {a.explanation}")
