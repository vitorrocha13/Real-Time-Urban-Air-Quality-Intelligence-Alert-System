import pathway as pw
from ai_model import predict_aqi_risk

class SensorSchema(pw.Schema):
    timestamp: str
    station_id: str
    pm25: float
    pm10: float
    no2: float
    co: float
    temperature: float
    humidity: float
    city: str

def run_pathway_pipeline():

    raw = pw.io.jsonlines.read(
        "./data/live_sensors.jsonl",
        schema=SensorSchema,
        mode="streaming"   # REQUIRED
    )

    enriched = raw.select(
        *pw.this,
        aqi_score=pw.apply(
            lambda pm25,pm10,no2,co:
            pm25*0.35 + pm10*0.25 + no2*0.25 + co*0.15,
            pw.this.pm25,
            pw.this.pm10,
            pw.this.no2,
            pw.this.co
        )
    )

    predicted = enriched.select(
        *pw.this,
        risk_level=pw.apply(
            predict_aqi_risk,
            pw.this.pm25,
            pw.this.pm10,
            pw.this.no2,
            pw.this.co,
            pw.this.temperature,
            pw.this.humidity
        )
    )

    pw.io.jsonlines.write(predicted,"./data/predictions.jsonl")

    pw.run()
