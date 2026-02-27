"""
GreenPulse AI — FastAPI Server
================================
Exposes enriched air-quality data via REST endpoints.

Endpoints:
  GET  /                        Health check
  GET  /api/v1/latest           Most recent record per city
  GET  /api/v1/city/{city}      Full history for a city
  GET  /api/v1/alerts           Active HIGH/MEDIUM alerts
  GET  /api/v1/stats            Aggregate statistics
  POST /api/v1/predict          On-demand inference for a raw record
  GET  /api/v1/cities           List monitored cities
"""

import json
from pathlib import Path
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.ai_model import ModelManager

# ── App Initialisation ─────────────────────────────────────────────────────────

app = FastAPI(
    title="GreenPulse AI",
    description="Real-Time Urban Air Quality Intelligence & Alert System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_model_manager = ModelManager()
ENRICHED_STREAM_PATH = Path("data/enriched_stream.jsonl")


# ── Data Access Layer ──────────────────────────────────────────────────────────

def _load_stream(max_lines: int = 5000) -> list[dict]:
    """
    Read the enriched JSONL stream.
    Loads last `max_lines` to keep memory bounded.
    """
    if not ENRICHED_STREAM_PATH.exists():
        return []

    lines = []
    with open(ENRICHED_STREAM_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return lines[-max_lines:]


def _latest_per_city(records: list[dict]) -> dict[str, dict]:
    """Return the most recent record for each city."""
    latest: dict[str, dict] = {}
    for rec in records:
        city = rec.get("city", "Unknown")
        if city not in latest or rec.get("timestamp", "") > latest[city].get("timestamp", ""):
            latest[city] = rec
    return latest


# ── Request / Response Models ──────────────────────────────────────────────────

class PredictRequest(BaseModel):
    city:        str   = Field(..., example="Delhi")
    sensor_id:   str   = Field(default="manual-01")
    timestamp:   Optional[str] = None
    pm25:        float = Field(..., ge=0, le=1000, example=145.0)
    pm10:        float = Field(..., ge=0, le=1000, example=220.0)
    no2:         float = Field(..., ge=0, le=500,  example=78.0)
    co:          float = Field(..., ge=0, le=50,   example=3.2)
    temperature: float = Field(..., ge=-20, le=60, example=22.0)
    humidity:    float = Field(..., ge=0, le=100,  example=75.0)


class PredictResponse(BaseModel):
    city:        str
    sensor_id:   str
    pm25:        float
    pm10:        float
    no2:         float
    co:          float
    temperature: float
    humidity:    float
    aqi:         float
    category:    str
    risk_level:  str
    risk_code:   int
    confidence:  float
    alert:       Optional[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
def health_check():
    """Service health check."""
    return {
        "service": "GreenPulse AI",
        "version": "1.0.0",
        "status":  "operational",
        "stream":  ENRICHED_STREAM_PATH.exists(),
    }


@app.get("/api/v1/cities", tags=["data"])
def list_cities():
    """Return list of cities currently present in the stream."""
    records = _load_stream()
    cities = sorted({r.get("city") for r in records if r.get("city")})
    return {"cities": cities, "count": len(cities)}


@app.get("/api/v1/latest", tags=["data"])
def get_latest():
    """
    Most recent sensor reading + AI inference per city.
    Refreshes on every API call — data is pulled live from the Pathway output stream.
    """
    records = _load_stream()
    if not records:
        return {"message": "No data yet — ensure pipeline and simulator are running.", "data": {}}

    latest = _latest_per_city(records)
    return {
        "count": len(latest),
        "data":  list(latest.values()),
    }


@app.get("/api/v1/city/{city}", tags=["data"])
def get_city_history(
    city: str,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Full history for a specific city (most recent `limit` records)."""
    records = _load_stream()
    city_records = [r for r in records if r.get("city", "").lower() == city.lower()]

    if not city_records:
        raise HTTPException(status_code=404, detail=f"No data found for city: {city}")

    return {
        "city":    city,
        "count":   len(city_records[-limit:]),
        "records": city_records[-limit:],
    }


@app.get("/api/v1/alerts", tags=["alerts"])
def get_active_alerts(
    risk_level: Optional[str] = Query(default=None, description="Filter: HIGH, MEDIUM"),
):
    """
    Active alerts from the most recent reading per city.
    Optionally filter by risk_level.
    """
    records = _load_stream()
    latest = _latest_per_city(records)

    alerts = []
    for rec in latest.values():
        rl = rec.get("risk_level", "")
        if risk_level and rl != risk_level.upper():
            continue
        if rl in ("HIGH", "MEDIUM") and rec.get("alert"):
            alerts.append({
                "city":       rec.get("city"),
                "sensor_id":  rec.get("sensor_id"),
                "timestamp":  rec.get("timestamp"),
                "aqi":        rec.get("aqi"),
                "category":   rec.get("category"),
                "risk_level": rl,
                "confidence": rec.get("confidence"),
                "alert":      rec.get("alert"),
            })

    alerts.sort(key=lambda x: x.get("aqi", 0), reverse=True)
    return {"alert_count": len(alerts), "alerts": alerts}


@app.get("/api/v1/stats", tags=["analytics"])
def get_stats():
    """
    Aggregate statistics across all cities and time.
    Useful for dashboard summary cards.
    """
    records = _load_stream()
    if not records:
        return {"message": "No data yet."}

    aqi_values = [r["aqi"] for r in records if "aqi" in r and r["aqi"] >= 0]
    risk_counts = defaultdict(int)
    for r in records:
        risk_counts[r.get("risk_level", "UNKNOWN")] += 1

    latest = _latest_per_city(records)
    high_risk_cities = [c for c, r in latest.items() if r.get("risk_level") == "HIGH"]

    return {
        "total_records":      len(records),
        "cities_monitored":   len(latest),
        "high_risk_cities":   high_risk_cities,
        "risk_distribution":  dict(risk_counts),
        "aqi_stats": {
            "min":    round(min(aqi_values), 2) if aqi_values else None,
            "max":    round(max(aqi_values), 2) if aqi_values else None,
            "mean":   round(sum(aqi_values) / len(aqi_values), 2) if aqi_values else None,
        },
    }


@app.post("/api/v1/predict", response_model=PredictResponse, tags=["inference"])
def predict(req: PredictRequest):
    """
    On-demand AI inference for a raw sensor record.
    Does NOT require the streaming pipeline to be running.
    """
    from datetime import datetime, timezone

    record = req.model_dump()
    if not record.get("timestamp"):
        record["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        result = _model_manager.process_record(record)
    except Exception as exc:
        logger.error(f"Prediction error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    return PredictResponse(**result)


# ── Dev Server ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api_server:app", host="0.0.0.0", port=8000, reload=False)
