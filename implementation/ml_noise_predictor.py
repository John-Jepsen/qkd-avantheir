"""
Channel Noise Prediction for QKD via Time-Series Forecasting

Models the quantum channel as having time-varying noise and uses ARIMA
to forecast future QBER values. This enables proactive parameter adjustment
(e.g., increase n_bits before noise rises) rather than reactive threshold
aborts.

The simulator generates a synthetic time-series where noise follows a
combination of:
  - Slow drift (sinusoidal with period ~100 rounds)
  - Random walk component (Brownian motion)
  - Sudden spikes (Poisson-distributed disturbances)

Usage:
    from ml_noise_predictor import NoisePredictor

    predictor = NoisePredictor()
    series = predictor.generate_noise_series(n_rounds=500)
    predictor.fit(series)
    forecast = predictor.forecast(steps=20)
"""

import warnings
import numpy as np
from dataclasses import dataclass
from statsmodels.tsa.arima.model import ARIMA


@dataclass
class NoiseForecast:
    predicted_qber: list[float]      # Forecasted QBER values
    confidence_lower: list[float]    # 95% CI lower bound
    confidence_upper: list[float]    # 95% CI upper bound
    steps_ahead: int
    alert: bool                      # True if any forecast exceeds alert threshold
    alert_step: int                  # First step that exceeds threshold (-1 if none)


class NoisePredictor:
    """
    ARIMA-based QBER time-series forecaster for quantum channels.

    Generates realistic time-varying noise series from the BB84 simulator,
    fits an ARIMA model, and forecasts future QBER to enable proactive
    protocol adjustments.
    """

    def __init__(self, alert_threshold: float = 0.09):
        self.alert_threshold = alert_threshold
        self.model_fit = None
        self.history = None

    def generate_noise_series(self, n_rounds: int = 500,
                              base_noise: float = 0.03,
                              seed: int = 42) -> np.ndarray:
        """
        Generate a synthetic time-varying QBER series.

        Components:
          - Sinusoidal drift (models temperature/alignment fluctuations)
          - Random walk (models gradual fiber degradation)
          - Poisson spikes (models sudden disturbances like vibration)
        """
        rng = np.random.default_rng(seed)

        t = np.arange(n_rounds)

        # Slow sinusoidal drift (period ~100 rounds, amplitude ~1%)
        drift = 0.01 * np.sin(2 * np.pi * t / 100)

        # Random walk (cumulative small perturbations)
        walk = np.cumsum(rng.normal(0, 0.001, n_rounds))
        walk = walk - walk.mean()  # Center around zero

        # Poisson spikes (sudden disturbances)
        spike_times = rng.poisson(0.05, n_rounds)
        spikes = spike_times * rng.uniform(0.02, 0.05, n_rounds)

        # Combine and clip to valid QBER range
        series = base_noise + drift + walk + spikes
        series = np.clip(series, 0.001, 0.15)

        return series

    def generate_series_from_simulator(self, n_rounds: int = 200,
                                       n_bits: int = 4096,
                                       seed: int = 42) -> np.ndarray:
        """
        Generate a QBER series by running the BB84 simulator with
        time-varying noise at each round.
        """
        from bb84_simulator import BB84Protocol

        noise_levels = self.generate_noise_series(n_rounds, seed=seed)
        qber_series = []

        for i, noise in enumerate(noise_levels):
            proto = BB84Protocol(error_rate=float(noise), eavesdrop=False)
            result = proto.run(n_bits=n_bits)
            qber_series.append(result.qber)
            if (i + 1) % 50 == 0:
                print(f"  Simulated {i + 1}/{n_rounds} rounds...")

        return np.array(qber_series)

    def fit(self, series: np.ndarray, order: tuple = (2, 1, 2)):
        """
        Fit an ARIMA model to the observed QBER series.

        Default order (2,1,2) works well for the noise model's combination
        of drift and random walk components.
        """
        self.history = series.copy()
        self.model_fit = ARIMA(series, order=order).fit()

        aic = self.model_fit.aic
        bic = self.model_fit.bic
        print(f"ARIMA{order} fitted — AIC={aic:.1f}, BIC={bic:.1f}")
        return self

    def forecast(self, steps: int = 20) -> NoiseForecast:
        """Forecast future QBER values with confidence intervals."""
        if self.model_fit is None:
            raise RuntimeError("Call fit() first")

        fc = self.model_fit.get_forecast(steps=steps)
        mean = fc.predicted_mean
        ci = fc.conf_int(alpha=0.05)

        predicted = list(np.clip(mean, 0, 1))
        ci_array = np.asarray(ci)
        lower = list(np.clip(ci_array[:, 0], 0, 1))
        upper = list(np.clip(ci_array[:, 1], 0, 1))

        # Check for alert
        alert_step = -1
        for i, val in enumerate(predicted):
            if val > self.alert_threshold:
                alert_step = i
                break

        return NoiseForecast(
            predicted_qber=predicted,
            confidence_lower=lower,
            confidence_upper=upper,
            steps_ahead=steps,
            alert=alert_step >= 0,
            alert_step=alert_step,
        )

    def rolling_forecast(self, series: np.ndarray, window: int = 100,
                         steps: int = 5) -> dict:
        """
        Walk-forward validation: fit on a rolling window and forecast ahead.
        Returns actual vs predicted for evaluation.
        """
        actuals = []
        predictions = []

        for i in range(window, len(series) - steps):
            train = series[i - window:i]
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = ARIMA(train, order=(2, 1, 2)).fit()
                    fc = model.get_forecast(steps=steps)
                    pred = fc.predicted_mean.iloc[-1]
            except Exception:
                pred = train[-1]  # Fallback to last observed value

            actual = series[i + steps - 1]
            actuals.append(actual)
            predictions.append(pred)

        actuals = np.array(actuals)
        predictions = np.array(predictions)
        mae = np.mean(np.abs(actuals - predictions))
        rmse = np.sqrt(np.mean((actuals - predictions) ** 2))

        return {
            "actuals": actuals,
            "predictions": predictions,
            "mae": mae,
            "rmse": rmse,
            "n_forecasts": len(actuals),
        }


# ── Demo ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("QKD Channel Noise Prediction")
    print("=" * 55)

    predictor = NoisePredictor(alert_threshold=0.09)

    # Generate synthetic noise series
    print("\nGenerating synthetic noise time-series (500 rounds)...")
    series = predictor.generate_noise_series(n_rounds=500)
    print(f"  Mean QBER:  {series.mean():.4f}")
    print(f"  Std QBER:   {series.std():.4f}")
    print(f"  Min/Max:    {series.min():.4f} / {series.max():.4f}")

    # Fit ARIMA
    print("\nFitting ARIMA model...")
    predictor.fit(series)

    # Forecast
    print("\nForecasting next 20 rounds...")
    fc = predictor.forecast(steps=20)
    print(f"  Predicted QBER (next 5): "
          f"{', '.join(f'{v:.4f}' for v in fc.predicted_qber[:5])}")
    print(f"  95% CI width (step 1):   "
          f"[{fc.confidence_lower[0]:.4f}, {fc.confidence_upper[0]:.4f}]")
    if fc.alert:
        print(f"  ALERT: QBER predicted to exceed {predictor.alert_threshold} "
              f"at step {fc.alert_step + 1}")
    else:
        print(f"  No alert — all forecasts below {predictor.alert_threshold}")

    # Rolling validation
    print("\nRunning walk-forward validation (window=100, 5-step ahead)...")
    metrics = predictor.rolling_forecast(series, window=100, steps=5)
    print(f"  Forecasts: {metrics['n_forecasts']}")
    print(f"  MAE:  {metrics['mae']:.5f}")
    print(f"  RMSE: {metrics['rmse']:.5f}")
