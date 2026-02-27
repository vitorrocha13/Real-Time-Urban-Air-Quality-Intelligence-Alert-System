# GreenPulse AI — Developer Workflow

## Quick Start (Local)

### 1. Install dependencies
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start everything with one command
```bash
python main.py
```

This starts:
- Data Simulator (writes `data/sensor_stream.jsonl`)
- Pathway Pipeline (reads stream → infers → writes `data/enriched_stream.jsonl`)
- FastAPI Server on `http://localhost:8000`

### 3. Open the Dashboard
```bash
# In a separate terminal:
streamlit run dashboard/dashboard.py
```
Visit: `http://localhost:8501`

### 4. Explore the API
Visit: `http://localhost:8000/docs`

---

## Component-by-Component Start

```bash
# Terminal 1 — Simulator only
python -m app.data_simulator --interval 2.0 --spike-prob 0.05

# Terminal 2 — Pathway Pipeline only
python -m app.pathway_pipeline

# Terminal 3 — API only
python main.py --mode api

# Terminal 4 — Dashboard
streamlit run dashboard/dashboard.py
```

---

## Retrain the AI Model

```bash
python app/ai_model.py
# Model saved to models/risk_classifier.joblib
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# API server
API_HOST=0.0.0.0
API_PORT=8000

# Simulator
SIMULATOR_INTERVAL=2.0
SPIKE_PROBABILITY=0.05

# Pathway
INPUT_STREAM=data/sensor_stream.jsonl
OUTPUT_STREAM=data/enriched_stream.jsonl
```

---

## Docker Compose (Production)

```yaml
# docker-compose.yml (reference — not included in repo)
version: "3.9"
services:
  simulator:
    build: .
    command: python -m app.data_simulator
    volumes: [./data:/app/data]

  pipeline:
    build: .
    command: python -m app.pathway_pipeline
    volumes: [./data:/app/data, ./models:/app/models]
    depends_on: [simulator]

  api:
    build: .
    command: uvicorn app.api_server:app --host 0.0.0.0 --port 8000
    ports: ["8000:8000"]
    volumes: [./data:/app/data, ./models:/app/models]
    depends_on: [pipeline]

  dashboard:
    build: .
    command: streamlit run dashboard/dashboard.py --server.port 8501
    ports: ["8501:8501"]
    depends_on: [api]
```

---

## Testing Individual Components

```bash
# Smoke-test the AI model
python app/ai_model.py

# Generate 50 records and exit
python -m app.data_simulator --max-records 50 --output data/test.jsonl

# Test API prediction endpoint
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"city":"Delhi","pm25":180,"pm10":250,"no2":95,"co":4.5,"temperature":18,"humidity":85}'
```
