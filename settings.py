from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

LIVE_SENSORS_FILE = DATA_DIR / "live_sensors.jsonl"
PREDICTIONS_FILE = DATA_DIR / "predictions_out.jsonl"

API_HOST = "0.0.0.0"
API_PORT = 8000
