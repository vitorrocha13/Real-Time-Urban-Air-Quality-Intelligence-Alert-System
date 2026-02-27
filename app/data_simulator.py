import json, random, time
from datetime import datetime
from config.settings import LIVE_SENSORS_FILE

CITIES = ["Mumbai","Delhi","Chennai","Bengaluru","Hyderabad"]

def generate_reading(city):
    hour = datetime.now().hour
    traffic = 1.5 if hour in range(8,11) or hour in range(17,21) else 1.0
    base = random.uniform(20,180)*traffic
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "station_id": f"{city[:3].upper()}-{random.randint(1,5):03d}",
        "pm25": round(base,2),
        "pm10": round(base*random.uniform(1.2,2.0),2),
        "no2": round(random.uniform(5,150)*traffic,2),
        "co": round(random.uniform(0.5,30)*traffic,2),
        "temperature": round(random.uniform(18,42),2),
        "humidity": round(random.uniform(25,90),2),
        "city": city
    }

def start_data_stream(interval_secs=1.0):
    LIVE_SENSORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LIVE_SENSORS_FILE.open("a", encoding="utf-8") as f:
        while True:
            for city in CITIES:
                f.write(json.dumps(generate_reading(city))+"\n")
                f.flush()
            time.sleep(interval_secs)
