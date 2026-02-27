"""
GreenPulse AI — AI Model Module
================================
Handles training, persistence, and inference for the air quality
risk classification model using scikit-learn RandomForestClassifier.

Architecture:
  - AQICalculator   : Computes AQI score from raw pollutant readings
  - RiskClassifier  : Trains / loads RandomForest, runs inference
  - ModelManager    : Singleton facade for the pipeline
"""

import os
import numpy as np
import joblib
from pathlib import Path
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# ── Constants ──────────────────────────────────────────────────────────────────

MODEL_PATH = Path(__file__).parent.parent / "models" / "risk_classifier.joblib"

RISK_LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}

# AQI breakpoints for PM2.5 (µg/m³) — Indian CPCB standard
PM25_BREAKPOINTS = [
    (0,    30,    0,    50),    # Good
    (30,   60,    51,   100),   # Satisfactory
    (60,   90,    101,  200),   # Moderate
    (90,   120,   201,  300),   # Poor
    (120,  250,   301,  400),   # Very Poor
    (250,  500,   401,  500),   # Severe
]

# Feature columns used for inference (order matters)
FEATURE_COLUMNS = ["pm25", "pm10", "no2", "co", "temperature", "humidity", "aqi"]


# ── AQI Calculation ────────────────────────────────────────────────────────────

class AQICalculator:
    """
    Computes AQI from PM2.5 concentration using CPCB linear interpolation.
    Extends easily to multi-pollutant AQI (PM10, NO2, etc.).
    """

    @staticmethod
    def _linear_interpolate(c: float, breakpoints: list) -> float:
        """
        Linear interpolation between AQI sub-index breakpoints.
        Formula: AQI = ((I_hi - I_lo) / (C_hi - C_lo)) * (C - C_lo) + I_lo
        """
        for c_lo, c_hi, i_lo, i_hi in breakpoints:
            if c_lo <= c <= c_hi:
                return ((i_hi - i_lo) / (c_hi - c_lo)) * (c - c_lo) + i_lo
        # Clamp to max if exceeds highest breakpoint
        return 500.0

    @staticmethod
    def calculate(pm25: float, pm10: float = 0.0) -> float:
        """
        Calculate composite AQI score.
        Returns float in range [0, 500].
        """
        aqi_pm25 = AQICalculator._linear_interpolate(
            max(0.0, pm25), PM25_BREAKPOINTS
        )
        # PM10 sub-index (simplified)
        aqi_pm10 = min(pm10 / 2.0, 500.0) if pm10 > 0 else 0.0
        return round(max(aqi_pm25, aqi_pm10), 2)

    @staticmethod
    def aqi_to_category(aqi: float) -> str:
        """Map AQI score to CPCB category string."""
        if aqi <= 50:   return "Good"
        if aqi <= 100:  return "Satisfactory"
        if aqi <= 200:  return "Moderate"
        if aqi <= 300:  return "Poor"
        if aqi <= 400:  return "Very Poor"
        return "Severe"


# ── Risk Classifier ────────────────────────────────────────────────────────────

class RiskClassifier:
    """
    Wraps a scikit-learn Pipeline (StandardScaler + RandomForestClassifier).
    Supports:
      - Synthetic training data generation (no external dataset required)
      - Model persistence via joblib
      - Single-record inference returning label + probability
    """

    def __init__(self):
        self.pipeline: Pipeline | None = None
        self._ensure_model()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_pipeline(self) -> Pipeline:
        """Construct the sklearn Pipeline."""
        return Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_split=5,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ])

    def _generate_synthetic_data(self, n_samples: int = 10_000):
        """
        Generate realistic synthetic training data covering Indian city
        pollution scenarios (monsoon, winter smog, industrial zones).
        """
        rng = np.random.default_rng(42)

        # --- LOW risk zone (clean days) ---
        n_low = n_samples // 3
        X_low = np.column_stack([
            rng.uniform(0, 30, n_low),       # pm25
            rng.uniform(0, 50, n_low),        # pm10
            rng.uniform(10, 40, n_low),       # no2
            rng.uniform(0.1, 1.0, n_low),     # co
            rng.uniform(20, 35, n_low),       # temperature
            rng.uniform(40, 80, n_low),       # humidity
            rng.uniform(0, 100, n_low),       # aqi
        ])
        y_low = np.zeros(n_low, dtype=int)

        # --- MEDIUM risk zone ---
        n_med = n_samples // 3
        X_med = np.column_stack([
            rng.uniform(31, 90, n_med),
            rng.uniform(51, 150, n_med),
            rng.uniform(40, 80, n_med),
            rng.uniform(1.0, 3.0, n_med),
            rng.uniform(15, 40, n_med),
            rng.uniform(50, 90, n_med),
            rng.uniform(101, 250, n_med),
        ])
        y_med = np.ones(n_med, dtype=int)

        # --- HIGH risk zone (Delhi winter, industrial smog) ---
        n_high = n_samples - n_low - n_med
        X_high = np.column_stack([
            rng.uniform(91, 500, n_high),
            rng.uniform(151, 600, n_high),
            rng.uniform(80, 200, n_high),
            rng.uniform(3.0, 10.0, n_high),
            rng.uniform(5, 30, n_high),
            rng.uniform(60, 99, n_high),
            rng.uniform(251, 500, n_high),
        ])
        y_high = np.full(n_high, 2, dtype=int)

        X = np.vstack([X_low, X_med, X_high])
        y = np.concatenate([y_low, y_med, y_high])

        # Shuffle
        idx = rng.permutation(len(y))
        return X[idx], y[idx]

    # ── Public API ───────────────────────────────────────────────────────────

    def train(self) -> None:
        """Train on synthetic data and persist model to disk."""
        logger.info("Training RiskClassifier on synthetic data…")
        X, y = self._generate_synthetic_data()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X_train, y_train)

        # Evaluation
        y_pred = self.pipeline.predict(X_test)
        report = classification_report(y_test, y_pred, target_names=list(RISK_LABELS.values()))
        logger.info(f"Model evaluation:\n{report}")

        # Persist
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, MODEL_PATH)
        logger.info(f"Model saved → {MODEL_PATH}")

    def load(self) -> bool:
        """Load persisted model. Returns True on success."""
        if MODEL_PATH.exists():
            self.pipeline = joblib.load(MODEL_PATH)
            logger.info(f"Model loaded from {MODEL_PATH}")
            return True
        return False

    def _ensure_model(self) -> None:
        """Load existing model or train a new one."""
        if not self.load():
            logger.warning("No saved model found — training from scratch.")
            self.train()

    def predict(self, features: dict) -> dict:
        """
        Run inference on a single record.

        Args:
            features: dict with keys matching FEATURE_COLUMNS

        Returns:
            dict with risk_level (str), risk_code (int), confidence (float)
        """
        if self.pipeline is None:
            raise RuntimeError("Model is not loaded.")

        vector = np.array([[features[col] for col in FEATURE_COLUMNS]])
        risk_code = int(self.pipeline.predict(vector)[0])
        probabilities = self.pipeline.predict_proba(vector)[0]
        confidence = round(float(probabilities[risk_code]) * 100, 2)

        return {
            "risk_level": RISK_LABELS[risk_code],
            "risk_code": risk_code,
            "confidence": confidence,
        }


# ── Singleton Facade ───────────────────────────────────────────────────────────

class ModelManager:
    """
    Thread-safe singleton wrapping AQICalculator + RiskClassifier.
    Used by both Pathway pipeline and FastAPI server.
    """

    _instance: "ModelManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.aqi_calc = AQICalculator()
        self.classifier = RiskClassifier()
        self._initialized = True

    def process_record(self, record: dict) -> dict:
        """
        Full inference pipeline for one sensor record.

        Steps:
          1. Calculate AQI
          2. Classify risk
          3. Generate alert if HIGH
          4. Return enriched record
        """
        aqi = self.aqi_calc.calculate(
            pm25=record.get("pm25", 0.0),
            pm10=record.get("pm10", 0.0),
        )
        category = self.aqi_calc.aqi_to_category(aqi)

        features = {
            "pm25":        record.get("pm25", 0.0),
            "pm10":        record.get("pm10", 0.0),
            "no2":         record.get("no2", 0.0),
            "co":          record.get("co", 0.0),
            "temperature": record.get("temperature", 25.0),
            "humidity":    record.get("humidity", 60.0),
            "aqi":         aqi,
        }

        prediction = self.classifier.predict(features)

        alert = None
        if prediction["risk_level"] == "HIGH":
            alert = (
                f"🚨 HIGH RISK ALERT — {record.get('city', 'Unknown')} | "
                f"AQI: {aqi} ({category}) | "
                f"PM2.5: {record.get('pm25')} µg/m³"
            )
        elif prediction["risk_level"] == "MEDIUM":
            alert = (
                f"⚠️  MODERATE ALERT — {record.get('city', 'Unknown')} | "
                f"AQI: {aqi} ({category})"
            )

        return {
            **record,
            "aqi":        aqi,
            "category":   category,
            "risk_level": prediction["risk_level"],
            "risk_code":  prediction["risk_code"],
            "confidence": prediction["confidence"],
            "alert":      alert,
        }


# ── Module entry point (re-train) ──────────────────────────────────────────────

if __name__ == "__main__":
    mgr = ModelManager()
    logger.info("ModelManager ready. Running smoke test…")
    test_record = {
        "city": "Delhi",
        "pm25": 180.0, "pm10": 250.0, "no2": 95.0,
        "co": 4.5, "temperature": 18.0, "humidity": 85.0,
    }
    result = mgr.process_record(test_record)
    logger.info(f"Smoke test result: {result}")
