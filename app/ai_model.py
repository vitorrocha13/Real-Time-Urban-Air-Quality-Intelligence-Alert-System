import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from config.settings import MODELS_DIR

MODEL_PATH = MODELS_DIR / "aqi_risk_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
LABELS = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}

def _gen(n=5000):
    rng = np.random.default_rng(42)
    X = np.column_stack([
        rng.uniform(0,300,n),
        rng.uniform(0,500,n),
        rng.uniform(0,200,n),
        rng.uniform(0,50,n),
        rng.uniform(10,45,n),
        rng.uniform(20,95,n),
    ])
    aqi = X[:,0]*0.35 + X[:,1]*0.25 + X[:,2]*0.25 + X[:,3]*0.15
    y = np.where(aqi < 50, 0, np.where(aqi < 150, 1, 2))
    return X,y

def train_and_save_model():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    X,y = _gen()
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(Xs,y)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

def _load():
    if not MODEL_PATH.exists() or not SCALER_PATH.exists():
        train_and_save_model()
    return joblib.load(MODEL_PATH), joblib.load(SCALER_PATH)

_MODEL, _SCALER = _load()

def predict_aqi_risk(pm25, pm10, no2, co, temp, humidity):
    x = np.array([[pm25, pm10, no2, co, temp, humidity]])
    x = _SCALER.transform(x)
    return LABELS[int(_MODEL.predict(x)[0])]
