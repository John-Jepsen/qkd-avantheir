"""
QKD Adaptive Security Pipeline — REST API

Unifies the full closed-loop pipeline behind a FastAPI service:

  BB84 simulation → ML eavesdrop detection → attack classification
  → noise forecasting → parameter tuning → KME anomaly detection

Endpoints:
  POST /analyze          Run BB84 + all ML models, return unified security report
  POST /forecast         QBER forecast for next N rounds
  POST /recommend        Optimal BB84 params for a given noise level
  POST /detect-anomaly   Classify a KME traffic window
  POST /adversarial-eval Run adversarial evaluation (evasion + hardening)
  POST /evolution/start  Start evolutionary gym (runs async, streams via WS)
  GET  /evolution/status Current evolution state
  GET  /attack-tree      Phylogeny tree from last evolution run
  WS   /ws/evolution     WebSocket for live evolution updates
  GET  /health           Pipeline status (loaded models, data stats)
  GET  /models           Details on each loaded model

Startup:
  - Loads eavesdrop_model.pkl, attack_model.pkl, param_tuner_model.pkl
  - Trains noise predictor (ARIMA) from noise_series_dataset.csv
  - Trains KME anomaly detector (Isolation Forest) from kme_anomaly_dataset.csv

Usage:
  pip install fastapi uvicorn
  cd implementation/
  uvicorn api:app --reload --port 8000
  # Docs at http://127.0.0.1:8000/docs
"""

import csv
import os
import time
import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from dataclasses import asdict

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ── Local imports ────────────────────────────────────────────────────────────

from bb84_simulator import BB84Protocol
from ml_eavesdrop_classifier import EavesdropClassifier
from ml_attack_classifier import (
    AttackClassifier,
    _extract_features as extract_attack_features,
)
from ml_noise_predictor import NoisePredictor
from ml_parameter_tuner import ParameterTuner
from ml_kme_anomaly import KMEAnomalyDetector, TrafficRecord, FEATURE_NAMES as KME_FEATURES
from metrics import MetricsCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── Global model references (populated at startup) ──────────────────────────

eavesdrop_clf: EavesdropClassifier | None = None
attack_clf: AttackClassifier | None = None
param_tuner: ParameterTuner | None = None
noise_predictor: NoisePredictor | None = None
kme_detector: KMEAnomalyDetector | None = None
metrics_collector: MetricsCollector | None = None
startup_errors: list[str] = []


# ── Startup / shutdown ──────────────────────────────────────────────────────

def _load_pkl_models():
    """Load pre-trained pickle models."""
    global eavesdrop_clf, attack_clf, param_tuner

    path = os.path.join(DATA_DIR, "eavesdrop_model.pkl")
    if os.path.exists(path):
        eavesdrop_clf = EavesdropClassifier.load(path)
        log.info("Loaded eavesdrop classifier from %s", path)
    else:
        startup_errors.append(f"Missing {path} — run train_all_models.py first")

    path = os.path.join(DATA_DIR, "attack_model.pkl")
    if os.path.exists(path):
        attack_clf = AttackClassifier.load(path)
        log.info("Loaded attack classifier from %s", path)
    else:
        startup_errors.append(f"Missing {path} — run train_all_models.py first")

    path = os.path.join(DATA_DIR, "param_tuner_model.pkl")
    if os.path.exists(path):
        param_tuner = ParameterTuner.load(path)
        log.info("Loaded parameter tuner from %s", path)
    else:
        startup_errors.append(f"Missing {path} — run train_all_models.py first")


def _train_noise_predictor():
    """Fit ARIMA on the noise series CSV."""
    global noise_predictor

    path = os.path.join(DATA_DIR, "noise_series_dataset.csv")
    if not os.path.exists(path):
        startup_errors.append(f"Missing {path} — run train_all_models.py first")
        return

    series = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            series.append(float(row["qber"]))

    arr = np.array(series)
    noise_predictor = NoisePredictor(alert_threshold=0.09)
    noise_predictor.fit(arr)
    log.info("Trained noise predictor on %d data points", len(arr))


def _train_kme_anomaly_detector():
    """Fit Isolation Forest on the KME anomaly CSV (normal rows only)."""
    global kme_detector

    path = os.path.join(DATA_DIR, "kme_anomaly_dataset.csv")
    if not os.path.exists(path):
        startup_errors.append(f"Missing {path} — run train_all_models.py first")
        return

    normal_features = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["label"] == "normal":
                normal_features.append([float(row[feat]) for feat in KME_FEATURES])

    if len(normal_features) < 10:
        startup_errors.append("Not enough normal KME traffic data to train anomaly detector")
        return

    X = np.array(normal_features)
    kme_detector = KMEAnomalyDetector(contamination=0.05)
    kme_detector.scaler.fit(X)
    X_scaled = kme_detector.scaler.transform(X)
    kme_detector.model.fit(X_scaled)
    kme_detector.is_trained = True
    log.info("Trained KME anomaly detector on %d normal windows", len(normal_features))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models at startup."""
    t0 = time.time()
    log.info("Loading pipeline models...")
    _load_pkl_models()
    _train_noise_predictor()
    _train_kme_anomaly_detector()

    global metrics_collector
    metrics_collector = MetricsCollector()

    elapsed = time.time() - t0
    loaded = sum(1 for m in [eavesdrop_clf, attack_clf, param_tuner,
                              noise_predictor, kme_detector] if m is not None)
    log.info("Pipeline ready: %d/5 models loaded in %.1fs", loaded, elapsed)
    if startup_errors:
        for err in startup_errors:
            log.warning("STARTUP: %s", err)

    yield  # app runs

    log.info("Shutting down pipeline")


# ── FastAPI app ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="QKD Adaptive Security Pipeline",
    description=(
        "Closed-loop adaptive security analysis for quantum key distribution. "
        "Runs BB84 simulation through ML eavesdrop detection, attack classification, "
        "noise forecasting, and parameter tuning."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    n_bits: int = Field(4096, ge=512, le=65536, description="Raw qubits to send")
    error_rate: float = Field(0.01, ge=0.0, le=0.5, description="Channel noise rate")
    eavesdrop: bool = Field(False, description="Simulate intercept-resend attack")
    backend: str = Field("qiskit", description="'qiskit' or 'classical'")

class ForecastRequest(BaseModel):
    steps: int = Field(20, ge=1, le=100, description="Rounds to forecast ahead")

class RecommendRequest(BaseModel):
    observed_noise: float = Field(..., ge=0.0, le=0.5, description="Current observed QBER")

class AnomalyRequest(BaseModel):
    request_rate_1min: float = Field(..., description="Requests in last 60s")
    mean_keys_requested: float = Field(..., description="Avg keys per request")
    mean_key_size: float = Field(..., description="Avg key size in bits")
    inter_request_std: float = Field(..., description="Std dev of inter-request intervals")
    enc_dec_ratio: float = Field(..., description="Ratio of enc_keys to dec_keys")
    unique_sae_count: float = Field(..., description="Distinct SAE IDs in window")
    max_burst_rate: float = Field(..., description="Max requests in any 10s window")
    failed_ratio: float = Field(..., description="Fraction of requests returning 0 keys")


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/analyze", summary="Full pipeline analysis",
          description="Run BB84 simulation and feed results through all ML models")
def analyze(req: AnalyzeRequest):
    """
    Run the complete closed-loop pipeline:
      1. BB84 quantum key exchange simulation
      2. ML eavesdrop detection (Random Forest)
      3. Multi-class attack classification (Gradient Boosted)
      4. Parameter recommendation for current noise
      5. Metrics recording
    Returns a unified security report.
    """
    # 1. Run BB84
    t0 = time.time()
    proto = BB84Protocol(
        error_rate=req.error_rate,
        eavesdrop=req.eavesdrop,
        backend=req.backend,
    )
    result = proto.run(n_bits=req.n_bits)
    sim_ms = (time.time() - t0) * 1000

    # Record metrics
    if metrics_collector:
        metrics_collector.record_session(result, duration_ms=sim_ms)

    # Build base response
    response = {
        "simulation": {
            "backend": result.backend_used,
            "raw_bits": result.raw_bits,
            "sifted_bits": result.sifted_bits,
            "sift_ratio": round(result.sift_ratio, 4),
            "qber": round(result.qber, 4),
            "qber_pct": f"{result.qber * 100:.2f}%",
            "secure": result.secure,
            "eavesdropper_detected": result.eavesdropper_detected,
            "key_length_bits": result.key_length_bits,
            "final_key_hex": result.final_key.hex() if result.final_key else None,
            "simulation_ms": round(sim_ms, 1),
        },
        "ml_analysis": {},
        "recommended_actions": [],
    }

    # 2. Eavesdrop detection
    if eavesdrop_clf:
        det = eavesdrop_clf.predict_from_result(result)
        response["ml_analysis"]["eavesdrop_detection"] = {
            "predicted_label": det.predicted_label,
            "confidence": round(det.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in det.probabilities.items()},
            "threshold_would_detect": det.threshold_would_detect,
        }
        if det.predicted_label != "clean":
            response["recommended_actions"].append(
                f"Eavesdrop detected ({det.predicted_label}, {det.confidence:.0%} confidence)"
            )

    # 3. Attack classification
    if attack_clf:
        det = attack_clf.classify_from_bb84(result)
        response["ml_analysis"]["attack_classification"] = {
            "predicted_attack": det.predicted_attack,
            "confidence": round(det.confidence, 4),
            "probabilities": {k: round(v, 4) for k, v in det.probabilities.items()},
            "recommended_action": det.recommended_action,
        }
        if det.predicted_attack != "clean":
            response["recommended_actions"].append(det.recommended_action)

    # 4. Parameter recommendation
    if param_tuner:
        rec = param_tuner.recommend(observed_noise=result.qber)
        response["ml_analysis"]["parameter_recommendation"] = {
            "recommended_n_bits": rec.recommended_n_bits,
            "recommended_sample_fraction": rec.recommended_sample_fraction,
            "recommended_block_size": rec.recommended_block_size,
            "predicted_key_rate": round(rec.predicted_key_rate, 6),
            "top_candidates": rec.all_candidates,
        }

    # 5. Overall verdict
    if not result.secure:
        response["verdict"] = "ABORT"
        response["recommended_actions"].insert(0, "Protocol aborted — QBER exceeded threshold")
    elif any(a.get("predicted_label", a.get("predicted_attack", "clean")) != "clean"
             for a in response["ml_analysis"].values()
             if isinstance(a, dict) and ("predicted_label" in a or "predicted_attack" in a)):
        response["verdict"] = "WARNING"
    else:
        response["verdict"] = "SECURE"

    if not response["recommended_actions"]:
        response["recommended_actions"].append("No action needed — channel is secure")

    return response


@app.post("/forecast", summary="QBER noise forecast",
          description="Forecast future QBER values using ARIMA time-series model")
def forecast(req: ForecastRequest):
    if noise_predictor is None:
        raise HTTPException(503, "Noise predictor not loaded — missing training data")

    fc = noise_predictor.forecast(steps=req.steps)
    return {
        "steps_ahead": fc.steps_ahead,
        "predicted_qber": [round(v, 6) for v in fc.predicted_qber],
        "confidence_lower": [round(v, 6) for v in fc.confidence_lower],
        "confidence_upper": [round(v, 6) for v in fc.confidence_upper],
        "alert": fc.alert,
        "alert_step": fc.alert_step if fc.alert else None,
        "alert_threshold": noise_predictor.alert_threshold,
    }


@app.post("/recommend", summary="Parameter recommendation",
          description="Get optimal BB84 parameters for a given noise level")
def recommend(req: RecommendRequest):
    if param_tuner is None:
        raise HTTPException(503, "Parameter tuner not loaded — missing model file")

    rec = param_tuner.recommend(observed_noise=req.observed_noise)
    return {
        "observed_noise": rec.observed_noise,
        "recommended": {
            "n_bits": rec.recommended_n_bits,
            "sample_fraction": rec.recommended_sample_fraction,
            "block_size": rec.recommended_block_size,
        },
        "predicted_key_rate": round(rec.predicted_key_rate, 6),
        "top_candidates": rec.all_candidates,
    }


@app.post("/detect-anomaly", summary="KME traffic anomaly detection",
          description="Classify a KME traffic window as normal or anomalous")
def detect_anomaly(req: AnomalyRequest):
    if kme_detector is None:
        raise HTTPException(503, "KME anomaly detector not loaded — missing training data")

    features = np.array([[
        req.request_rate_1min,
        req.mean_keys_requested,
        req.mean_key_size,
        req.inter_request_std,
        req.enc_dec_ratio,
        req.unique_sae_count,
        req.max_burst_rate,
        req.failed_ratio,
    ]])

    X_scaled = kme_detector.scaler.transform(features)
    prediction = kme_detector.model.predict(X_scaled)[0]
    score = kme_detector.model.decision_function(X_scaled)[0]

    feat_dict = {name: float(features[0, i]) for i, name in enumerate(KME_FEATURES)}
    explanation = kme_detector._explain(feat_dict, prediction == -1)

    return {
        "is_anomaly": bool(prediction == -1),
        "anomaly_score": round(float(score), 4),
        "explanation": explanation,
        "features": feat_dict,
    }


@app.get("/health", summary="Pipeline health check")
def health():
    models = {
        "eavesdrop_classifier": eavesdrop_clf is not None,
        "attack_classifier": attack_clf is not None,
        "parameter_tuner": param_tuner is not None,
        "noise_predictor": noise_predictor is not None,
        "kme_anomaly_detector": kme_detector is not None,
    }
    loaded = sum(models.values())
    total, secure, aborted = (
        metrics_collector.session_counts() if metrics_collector else (0, 0, 0)
    )

    return {
        "status": "healthy" if loaded == 5 else "degraded",
        "models_loaded": f"{loaded}/5",
        "models": models,
        "startup_errors": startup_errors if startup_errors else None,
        "session_stats": {
            "total": total,
            "secure": secure,
            "aborted": aborted,
        },
    }


@app.get("/models", summary="Model details")
def model_details():
    details = {}

    if eavesdrop_clf:
        details["eavesdrop_classifier"] = {
            "algorithm": "Random Forest (100 estimators, max_depth=10)",
            "features": ["qber", "sift_ratio", "error_variance", "max_burst_length"],
            "classes": ["clean", "eavesdrop", "partial_intercept"],
            "source": "eavesdrop_model.pkl",
        }

    if attack_clf:
        details["attack_classifier"] = {
            "algorithm": "Gradient Boosted (200 estimators, max_depth=5)",
            "features": [
                "qber", "sift_ratio", "error_variance", "max_burst_length",
                "low_block_fraction", "high_block_fraction",
                "error_autocorrelation", "sift_deviation",
            ],
            "classes": ["clean", "intercept_resend", "beam_splitting",
                        "pns_attack", "trojan_horse"],
            "source": "attack_model.pkl",
        }

    if param_tuner:
        details["parameter_tuner"] = {
            "algorithm": "Gradient Boosted Regression (200 estimators)",
            "features": ["noise_level", "n_bits", "sample_fraction", "block_size"],
            "target": "key_rate (bits per raw qubit)",
            "source": "param_tuner_model.pkl",
        }

    if noise_predictor:
        details["noise_predictor"] = {
            "algorithm": "ARIMA(2,1,2)",
            "alert_threshold": noise_predictor.alert_threshold,
            "history_length": len(noise_predictor.history) if noise_predictor.history is not None else 0,
            "source": "noise_series_dataset.csv (trained at startup)",
        }

    if kme_detector:
        details["kme_anomaly_detector"] = {
            "algorithm": "Isolation Forest (100 estimators, contamination=5%)",
            "features": list(KME_FEATURES),
            "source": "kme_anomaly_dataset.csv (trained at startup)",
        }

    return {"models": details, "total": len(details)}


# ── Adversarial endpoints ──────────────────────────────────────────────────

evolution_state: dict = {"status": "idle", "result": None, "generations": []}
evolution_ws_clients: list[WebSocket] = []


class AdversarialEvalRequest(BaseModel):
    epsilon: float = Field(0.15, ge=0.01, le=0.5, description="Perturbation strength")
    n_trials: int = Field(5, ge=1, le=20, description="Perturbation trials per sample")


class EvolutionStartRequest(BaseModel):
    population_size: int = Field(30, ge=10, le=200)
    n_generations: int = Field(10, ge=1, le=200)
    epsilon: float = Field(0.15, ge=0.01, le=0.5)
    hardening_mix: float = Field(0.3, ge=0.0, le=0.8)


@app.post("/adversarial-eval", summary="Adversarial evaluation",
          description="Measure evasion rates before and after hardening")
def adversarial_eval(req: AdversarialEvalRequest):

    from adversarial_eval import evaluate_evasion, generate_perturbations, adversarial_retrain
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score

    # Need training data — generate small set with classical backend
    from ml_eavesdrop_classifier import EavesdropClassifier
    import ml_eavesdrop_classifier
    from bb84_simulator import BB84Protocol

    orig = ml_eavesdrop_classifier.BB84Protocol
    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)

    ml_eavesdrop_classifier.BB84Protocol = FastProto
    temp_clf = EavesdropClassifier()
    temp_clf.generate_dataset(n_samples=300, n_bits=1024)
    temp_clf.train()
    ml_eavesdrop_classifier.BB84Protocol = orig

    X_test, y_test = temp_clf.X_test, temp_clf.y_test
    X_train, y_train = temp_clf.X_train, temp_clf.y_train

    # Before
    before = evaluate_evasion(temp_clf.model, X_test, y_test, epsilon=req.epsilon,
                              n_trials=req.n_trials)
    baseline_acc = accuracy_score(y_test, temp_clf.model.predict(X_test))

    # Harden
    X_adv = generate_perturbations(X_train, epsilon=req.epsilon)
    y_adv = temp_clf.model.predict(X_train)
    hardened = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    hardened.fit(X_train, y_train)
    adversarial_retrain(hardened, X_train, y_train, X_adv, y_adv)

    # After
    after = evaluate_evasion(hardened, X_test, y_test, epsilon=req.epsilon,
                             n_trials=req.n_trials)
    hardened_acc = accuracy_score(y_test, hardened.predict(X_test))

    return {
        "epsilon": req.epsilon,
        "before": {
            "evasion_rate": round(before["evasion_rate"], 4),
            "accuracy": round(baseline_acc, 4),
        },
        "after": {
            "evasion_rate": round(after["evasion_rate"], 4),
            "accuracy": round(hardened_acc, 4),
        },
        "improvement": round(float(before["evasion_rate"] - after["evasion_rate"]), 4),
        "hardening_effective": bool(after["evasion_rate"] < before["evasion_rate"]),
    }


def _run_evolution_background(req: EvolutionStartRequest):
    """Run evolution in a background thread and broadcast via WebSocket."""
    global evolution_state

    from adversarial_gym import AdversarialGym
    from ml_eavesdrop_classifier import EavesdropClassifier
    from bb84_simulator import BB84Protocol
    import ml_eavesdrop_classifier

    evolution_state = {"status": "training", "result": None, "generations": []}

    # Train classifier
    orig = ml_eavesdrop_classifier.BB84Protocol
    class FastProto:
        def __init__(self, **kw):
            kw["backend"] = "classical"
            self._p = BB84Protocol(**kw)
        def run(self, **kw):
            return self._p.run(**kw)

    ml_eavesdrop_classifier.BB84Protocol = FastProto
    clf = EavesdropClassifier()
    clf.generate_dataset(n_samples=600, n_bits=1024)
    clf.train()
    ml_eavesdrop_classifier.BB84Protocol = orig

    evolution_state["status"] = "evolving"

    def on_gen(gen_result):
        gen_data = {
            "generation": gen_result.generation,
            "best_fitness": round(gen_result.best_fitness, 4),
            "avg_fitness": round(gen_result.avg_fitness, 4),
            "evasion_rate": round(gen_result.evasion_rate, 4),
            "defender_accuracy": round(gen_result.defender_accuracy, 4),
        }
        evolution_state["generations"].append(gen_data)
        # Broadcast to WebSocket clients
        for ws in list(evolution_ws_clients):
            try:
                asyncio.run(ws.send_json({"type": "generation", "data": gen_data}))
            except Exception:
                evolution_ws_clients.remove(ws)

    gym = AdversarialGym(
        population_size=req.population_size,
        n_generations=req.n_generations,
        epsilon=req.epsilon,
        hardening_mix=req.hardening_mix,
        on_generation=on_gen,
    )

    result = gym.evolve(clf.X_train, clf.y_train, clf.X_test, clf.y_test, clf.model)

    evolution_state["status"] = "complete"
    evolution_state["result"] = {
        "initial_evasion_rate": round(result.initial_evasion_rate, 4),
        "final_evasion_rate": round(result.final_evasion_rate, 4),
        "final_defender_accuracy": round(result.final_defender_accuracy, 4),
        "total_elapsed_s": round(result.total_elapsed_s, 1),
        "phylogeny": result.phylogeny.to_dict(),
    }

    # Broadcast completion
    for ws in list(evolution_ws_clients):
        try:
            asyncio.run(ws.send_json({"type": "complete", "data": evolution_state["result"]}))
        except Exception:
            evolution_ws_clients.remove(ws)


@app.post("/evolution/start", summary="Start evolutionary gym",
          description="Launch evolution in background. Monitor via /ws/evolution or /evolution/status")
def start_evolution(req: EvolutionStartRequest):
    if evolution_state.get("status") == "evolving":
        raise HTTPException(409, "Evolution already running")

    thread = threading.Thread(target=_run_evolution_background, args=(req,), daemon=True)
    thread.start()

    return {"status": "started", "config": req.model_dump()}


@app.get("/evolution/status", summary="Evolution status")
def get_evolution_status():
    return {
        "status": evolution_state.get("status", "idle"),
        "generations_completed": len(evolution_state.get("generations", [])),
        "generations": evolution_state.get("generations", []),
        "result": evolution_state.get("result"),
    }


@app.get("/attack-tree", summary="Attack phylogeny tree")
def get_attack_tree():
    result = evolution_state.get("result")
    if result is None or "phylogeny" not in result:
        raise HTTPException(404, "No evolution has been run yet")
    return result["phylogeny"]


@app.websocket("/ws/evolution")
async def websocket_evolution(ws: WebSocket):
    await ws.accept()
    evolution_ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        evolution_ws_clients.remove(ws)
