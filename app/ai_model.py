import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib, os

MODEL_PATH = "./models/aqi_model.pkl"
SCALER_PATH = "./models/scaler.pkl"

def train_model():
    np.random.seed(42)
    n = 5000

    X = np.column_stack([
        np.random.uniform(0,300,n),
        np.random.uniform(0,500,n),
        np.random.uniform(0,200,n),
        np.random.uniform(0,50,n),
        np.random.uniform(10,45,n),
        np.random.uniform(20,95,n),
    ])

    aqi = X[:,0]*0.35 + X[:,1]*0.25 + X[:,2]*0.25 + X[:,3]*0.15
    y = np.where(aqi<50,0,np.where(aqi<150,1,2))

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model = RandomForestClassifier(n_estimators=100)
    model.fit(Xs,y)

    os.makedirs("models",exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)

if not os.path.exists(MODEL_PATH):
    train_model()

model = joblib.load(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

LABELS = {0:"LOW",1:"MEDIUM",2:"HIGH"}

def predict_aqi_risk(pm25,pm10,no2,co,temp,humidity):
    x = np.array([[pm25,pm10,no2,co,temp,humidity]])
    x = scaler.transform(x)
    pred = model.predict(x)[0]
    return LABELS[pred]
