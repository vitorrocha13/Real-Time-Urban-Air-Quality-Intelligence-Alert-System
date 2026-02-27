# GreenPulse AI — System Architecture

## Overview

GreenPulse AI is a real-time streaming intelligence platform built around
Pathway's reactive dataflow engine. Every component is decoupled and
communicates through append-only JSONL streams.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GreenPulse AI Platform                       │
│                                                                     │
│  ┌──────────────────┐     JSONL stream      ┌───────────────────┐  │
│  │  Data Simulator  │ ──────────────────────►│ Pathway Pipeline  │  │
│  │                  │  data/sensor_          │                   │  │
│  │  • 8 Indian      │  stream.jsonl          │ • Schema validate │  │
│  │    cities        │                        │ • pw.io.jsonlines │  │
│  │  • PM2.5/PM10    │                        │   .read(mode=     │  │
│  │  • NO2, CO       │                        │   "streaming")    │  │
│  │  • Temp/Humidity │                        │                   │  │
│  │  • Spike inject  │                        │ • AQI calculation │  │
│  └──────────────────┘                        │ • pw.apply() UDF  │  │
│                                              │   → AI inference  │  │
│                                              │                   │  │
│                                              │ • pw.io.jsonlines │  │
│                                              │   .write() output │  │
│                                              └────────┬──────────┘  │
│                                                       │             │
│                                              data/enriched_         │
│                                              stream.jsonl           │
│                                                       │             │
│  ┌──────────────────┐                        ┌────────▼──────────┐  │
│  │ Streamlit        │◄──── REST API ─────────│  FastAPI Server   │  │
│  │ Dashboard        │   localhost:8000        │                   │  │
│  │                  │                        │ • /api/v1/latest  │  │
│  │ • AQI gauges     │                        │ • /api/v1/alerts  │  │
│  │ • Risk map       │                        │ • /api/v1/city/X  │  │
│  │ • Trend charts   │                        │ • /api/v1/stats   │  │
│  │ • Alert feed     │                        │ • /api/v1/predict │  │
│  │ • Auto-refresh   │                        └───────────────────┘  │
│  └──────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. Data Simulator (`app/data_simulator.py`)
- Generates realistic sensor readings using city-specific pollution profiles
- Applies diurnal variation (rush-hour peaks, overnight lows)
- Appends one record per city every N seconds to `data/sensor_stream.jsonl`
- Supports probabilistic pollution spike injection for demo purposes

### 2. Pathway Pipeline (`app/pathway_pipeline.py`)
- Core streaming engine — no polling, no batch loops
- `pw.io.jsonlines.read(mode="streaming")` watches the input file continuously
- `pw.apply()` calls the inference UDF for every new record automatically
- Output written to `data/enriched_stream.jsonl` via `pw.io.jsonlines.write()`
- Auto-recomputation is guaranteed by Pathway's reactive dataflow graph

### 3. AI Model (`app/ai_model.py`)
- `AQICalculator`: CPCB-standard linear interpolation for AQI from PM2.5/PM10
- `RiskClassifier`: sklearn Pipeline (StandardScaler + RandomForestClassifier)
- Trained on synthetic data covering LOW/MEDIUM/HIGH Indian city scenarios
- `ModelManager`: singleton facade, thread-safe, loaded once at startup

### 4. FastAPI Server (`app/api_server.py`)
- Reads enriched JSONL stream on every request (no in-memory state)
- Stateless — horizontally scalable
- Provides endpoints for dashboard, external integrations, and on-demand inference

### 5. Streamlit Dashboard (`dashboard/dashboard.py`)
- Polls FastAPI every N seconds (configurable in sidebar)
- Plotly gauges, trend charts, bar charts, pie charts
- Alert feed with colour-coded severity

---

## Data Flow

```
Simulator writes        Pathway detects       Inference runs
record to JSONL   →     new line instantly  →  per record via
                        (streaming mode)       pw.apply()
                                                    │
Dashboard pulls    ←    FastAPI reads        ←  Enriched record
via REST                enriched JSONL           written to output
```

---

## Scaling Considerations

| Layer         | Scaling Strategy                                  |
|---------------|---------------------------------------------------|
| Simulator     | Replace with Kafka/MQTT consumer in production    |
| Pathway       | Native distributed mode; add Kafka source         |
| AI Model      | Swap RandomForest for ONNX-optimised deep model   |
| FastAPI       | Docker + Kubernetes, add Redis cache              |
| Dashboard     | Multi-user: switch to Grafana + Prometheus        |
