"""
GreenPulse AI — Pathway Streaming Pipeline
============================================
Core real-time orchestration layer.

Data flow:
  JSONL file (streaming) → schema validation → feature engineering
  → AQI calculation → AI model inference → output JSONL stream

Key Pathway behaviours leveraged:
  - pw.io.jsonlines.read(mode="streaming")   : watches file for new lines
  - pw.apply()                                : pure-function UDF per row
  - pw.io.jsonlines.write()                  : writes enriched stream out
  - Auto-recomputation on every new record — no manual trigger required
"""

import pathway as pw
from loguru import logger
from pathlib import Path

from app.ai_model import ModelManager


# ── Input Schema ───────────────────────────────────────────────────────────────

class SensorSchema(pw.Schema):
    """
    Typed schema for incoming sensor JSONL records.
    Pathway enforces types; malformed records are skipped automatically.
    """
    timestamp:   str
    city:        str
    sensor_id:   str
    pm25:        float
    pm10:        float
    no2:         float
    co:          float
    temperature: float
    humidity:    float


# ── Inference UDF ──────────────────────────────────────────────────────────────

# Instantiate ModelManager once — loaded at pipeline startup, not per-record.
_model_manager = ModelManager()


def _run_inference(
    timestamp: str,
    city: str,
    sensor_id: str,
    pm25: float,
    pm10: float,
    no2: float,
    co: float,
    temperature: float,
    humidity: float,
) -> str:
    """
    Pathway UDF: called automatically for every new or updated record.

    Returns a JSON string (Pathway pw.apply works best with scalar returns;
    we serialise the enriched dict and deserialise at the output writer stage).
    """
    import json

    record = {
        "timestamp":   timestamp,
        "city":        city,
        "sensor_id":   sensor_id,
        "pm25":        pm25,
        "pm10":        pm10,
        "no2":         no2,
        "co":          co,
        "temperature": temperature,
        "humidity":    humidity,
    }

    try:
        result = _model_manager.process_record(record)
    except Exception as exc:
        logger.error(f"Inference failed for record {sensor_id}@{city}: {exc}")
        result = {**record, "aqi": -1.0, "risk_level": "ERROR", "alert": str(exc)}

    return json.dumps(result)


# ── Pipeline Builder ───────────────────────────────────────────────────────────

def build_pipeline(
    input_path: str,
    output_path: str,
) -> None:
    """
    Construct and run the Pathway streaming pipeline.

    Args:
        input_path  : path to JSONL file written by DataSimulator
        output_path : path where enriched results are written as JSONL
    """
    logger.info(f"Building Pathway pipeline | input={input_path} → output={output_path}")

    # ── Step 1: Ingest streaming JSONL ────────────────────────────────────────
    # mode="streaming" tells Pathway to watch for new lines continuously.
    # This is the core auto-recomputation hook — no polling required.
    sensor_stream = pw.io.jsonlines.read(
        path=input_path,
        schema=SensorSchema,
        mode="streaming",
        autocommit_duration_ms=500,   # flush every 500 ms
    )

    # ── Step 2: AI Inference via pw.apply ─────────────────────────────────────
    # pw.apply calls _run_inference for EACH new row automatically.
    # Pathway's reactive engine propagates updates immediately.
    enriched_json = pw.apply(
        _run_inference,
        sensor_stream.timestamp,
        sensor_stream.city,
        sensor_stream.sensor_id,
        sensor_stream.pm25,
        sensor_stream.pm10,
        sensor_stream.no2,
        sensor_stream.co,
        sensor_stream.temperature,
        sensor_stream.humidity,
    )

    # ── Step 3: Unpack enriched JSON into table columns ───────────────────────
    enriched_table = sensor_stream.select(
        raw_result=enriched_json,
        timestamp=sensor_stream.timestamp,
        city=sensor_stream.city,
        sensor_id=sensor_stream.sensor_id,
        pm25=sensor_stream.pm25,
        pm10=sensor_stream.pm10,
        no2=sensor_stream.no2,
        co=sensor_stream.co,
        temperature=sensor_stream.temperature,
        humidity=sensor_stream.humidity,
    )

    # Extend with parsed inference fields using another pw.apply layer
    def _extract_field(json_str: str, field: str):
        import json as _json
        try:
            return str(_json.loads(json_str).get(field, ""))
        except Exception:
            return ""

    output_table = enriched_table.select(
        *pw.this,
        aqi=pw.apply(lambda j: float(__import__("json").loads(j).get("aqi", 0.0)), enriched_json),
        category=pw.apply(lambda j: str(__import__("json").loads(j).get("category", "")), enriched_json),
        risk_level=pw.apply(lambda j: str(__import__("json").loads(j).get("risk_level", "")), enriched_json),
        risk_code=pw.apply(lambda j: int(__import__("json").loads(j).get("risk_code", 0)), enriched_json),
        confidence=pw.apply(lambda j: float(__import__("json").loads(j).get("confidence", 0.0)), enriched_json),
        alert=pw.apply(lambda j: str(__import__("json").loads(j).get("alert") or ""), enriched_json),
    )

    # ── Step 4: Write enriched stream to output JSONL ─────────────────────────
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pw.io.jsonlines.write(output_table, output_path)

    # ── Step 5: Run forever — Pathway blocks here, processing updates ─────────
    logger.info("Pathway pipeline running — auto-processing new records…")
    pw.run(monitoring_level=pw.MonitoringLevel.NONE)


# ── Module Entry Point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_pipeline(
        input_path="data/sensor_stream.jsonl",
        output_path="data/enriched_stream.jsonl",
    )
