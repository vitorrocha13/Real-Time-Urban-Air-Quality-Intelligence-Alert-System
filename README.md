# 🌿 GreenPulse AI
### Real-Time Urban Air Quality Intelligence & Alert System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Pathway](https://img.shields.io/badge/Pathway-streaming-green.svg)](https://pathway.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST-009688.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🏙️ Problem Statement

India's rapidly urbanising cities face a silent public health crisis: **air pollution kills over 1.6 million Indians annually** (IHME, 2019). Yet most air quality monitoring systems are:

- **Batch-oriented** — updated hourly or daily, not in real time
- **Reactive, not predictive** — no AI risk classification
- **Siloed** — no unified API for downstream consumption
- **Passive** — no alert generation for at-risk populations

GreenPulse AI addresses all four gaps with a production-grade real-time intelligence platform.

---

## 🎯 What It Does

| Input                                  | Output                              |
|----------------------------------------|-------------------------------------|
| PM2.5, PM10, NO2, CO per sensor        | CPCB-standard AQI score (0–500)     |
| Temperature, Humidity                  | AI risk label: LOW / MEDIUM / HIGH  |
| City identifier, Sensor ID, Timestamp  | Live alert messages                 |
|                                        | REST API + live dashboard           |

---

## 🏗️ Architecture

```
Live Sensor Data / Simulator
         │
         ▼  (JSONL append stream)
┌─────────────────────────┐
│   Pathway Streaming     │  ← pw.io.jsonlines.read(mode="streaming")
│       Pipeline          │  ← pw.apply() → auto-inference per record
│                         │  ← pw.io.jsonlines.write() → enriched stream
└────────────┬────────────┘
             │
             ▼  (enriched JSONL stream)
┌─────────────────────────┐
│   FastAPI REST API      │  ← /api/v1/latest, /alerts, /stats, /predict
└────────────┬────────────┘
             │
             ▼  (HTTP polling)
┌─────────────────────────┐
│  Streamlit Dashboard    │  ← AQI gauges, trend charts, alert feed
└─────────────────────────┘
```

### How Pathway Powers Real-Time Operation

Pathway is the **core streaming engine** — not an add-on. Here's what makes it real-time:

1. **`pw.io.jsonlines.read(mode="streaming")`** — Pathway watches the input file at the OS level. Every new line appended by the simulator is ingested within milliseconds, without any polling loop in application code.

2. **`pw.apply()`** — A functional UDF applied to every row. When Pathway detects a new record, it automatically calls the inference function and propagates the result downstream. Zero manual triggering.

3. **Reactive Dataflow Graph** — Pathway builds a DAG of transformations. New data flows through the entire graph automatically — schema validation → feature extraction → AQI calculation → AI inference → output write — in a single reactive chain.

4. **`pw.run()`** — Blocks and drives the event loop. No `while True`, no `sleep`, no scheduler.

---

## 📁 Repository Structure

```
Real-Time-Urban-Air-Quality-Intelligence-Alert-System/
│
├── app/
│   ├── __init__.py
│   ├── pathway_pipeline.py     # Pathway streaming engine
│   ├── ai_model.py             # AQI calc + RandomForest inference
│   ├── api_server.py           # FastAPI REST layer
│   └── data_simulator.py       # JSONL sensor stream generator
│
├── dashboard/
│   └── dashboard.py            # Streamlit live dashboard
│
├── data/                       # Runtime JSONL streams (git-ignored)
├── models/                     # Persisted sklearn model (git-ignored)
├── logs/                       # Application logs (git-ignored)
│
├── docs/
│   ├── architecture.md         # System architecture + diagrams
│   └── workflow.md             # Developer setup + runbook
│
├── requirements.txt
├── main.py                     # Orchestrator — starts all components
├── README.md
└── LICENSE
```

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- pip / virtualenv

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-org/Real-Time-Urban-Air-Quality-Intelligence-Alert-System.git
cd Real-Time-Urban-Air-Quality-Intelligence-Alert-System

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import pathway; import fastapi; import streamlit; print('All dependencies OK')"
```

---

## ▶️ Running the System

### Option A — Full stack (one command)

```bash
python main.py
```

Starts simulator, Pathway pipeline, and FastAPI server in parallel.

### Option B — Individual components

```bash
# Terminal 1: Data simulator
python -m app.data_simulator --interval 2.0

# Terminal 2: Pathway pipeline
python app/pathway_pipeline.py

# Terminal 3: API server
uvicorn app.api_server:app --port 8000

# Terminal 4: Dashboard
streamlit run dashboard/dashboard.py
```

### Access points

| Service          | URL                                   |
|------------------|---------------------------------------|
| Dashboard        | http://localhost:8501                 |
| API Docs         | http://localhost:8000/docs            |
| Latest readings  | http://localhost:8000/api/v1/latest   |
| Active alerts    | http://localhost:8000/api/v1/alerts   |

---

## 🔌 API Endpoints

| Method | Endpoint                    | Description                              |
|--------|-----------------------------|------------------------------------------|
| GET    | `/`                         | Health check                             |
| GET    | `/api/v1/latest`            | Latest reading + AI result per city      |
| GET    | `/api/v1/city/{city}`       | Full history for a specific city         |
| GET    | `/api/v1/alerts`            | Active HIGH/MEDIUM alerts                |
| GET    | `/api/v1/stats`             | Aggregate statistics                     |
| POST   | `/api/v1/predict`           | On-demand inference (no pipeline needed) |
| GET    | `/api/v1/cities`            | List monitored cities                    |

### Example: On-demand prediction

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Delhi",
    "pm25": 180.0,
    "pm10": 250.0,
    "no2": 95.0,
    "co": 4.5,
    "temperature": 18.0,
    "humidity": 85.0
  }'
```

Response:
```json
{
  "city": "Delhi",
  "aqi": 312.5,
  "category": "Very Poor",
  "risk_level": "HIGH",
  "confidence": 94.5,
  "alert": "🚨 HIGH RISK ALERT — Delhi | AQI: 312.5 (Very Poor) | PM2.5: 180.0 µg/m³"
}
```

---

## 🤖 AI Model

**Algorithm:** scikit-learn RandomForestClassifier (200 trees)

**Features:** PM2.5, PM10, NO2, CO, Temperature, Humidity, AQI

**Classes:**
| Code | Label  | AQI Range | Description                          |
|------|--------|-----------|--------------------------------------|
| 0    | LOW    | 0–100     | Safe for general population          |
| 1    | MEDIUM | 101–250   | Caution for sensitive groups         |
| 2    | HIGH   | 251–500   | Immediate health risk                |

**Training data:** 10,000 synthetic records calibrated to Indian city profiles (Delhi winter smog, Mumbai coastal, Bengaluru tech-corridor).

**Persistence:** Serialised with joblib → `models/risk_classifier.joblib`. Auto-trains on first run if no model found.

---

## 🛠 Tech Stack

| Layer            | Technology                    | Role                              |
|------------------|-------------------------------|-----------------------------------|
| Streaming Engine | Pathway 0.14+                 | Real-time dataflow orchestration  |
| ML Inference     | scikit-learn RandomForest     | Risk classification               |
| AQI Calculation  | Custom (CPCB standard)        | AQI score from pollutant readings |
| REST API         | FastAPI + Uvicorn             | Data serving + on-demand predict  |
| Dashboard        | Streamlit + Plotly            | Live visualisation                |
| Data Format      | JSONL                         | Streaming-friendly line protocol  |
| Serialisation    | joblib                        | Model persistence                 |

---

## 🔮 Future Scalability

| Enhancement                    | Technology                            |
|--------------------------------|---------------------------------------|
| Replace file with message queue| Apache Kafka + Pathway Kafka connector|
| Multi-region deployment        | Kubernetes + Pathway distributed mode |
| Deep learning model            | ONNX Runtime (PyTorch model export)   |
| Historical analytics           | TimescaleDB / ClickHouse              |
| Push notifications             | Firebase Cloud Messaging              |
| Map visualisation              | Kepler.gl / Mapbox                    |
| Government data integration    | CPCB API, OpenAQ API                  |
| Mobile app                     | Flutter + GreenPulse REST API         |

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Pathway](https://pathway.com) — real-time streaming framework
- [CPCB](https://cpcb.nic.in) — AQI methodology and breakpoints
- [OpenAQ](https://openaq.org) — open air quality data standards

---

<p align="center">Built with ❤️ for cleaner Indian cities</p>
