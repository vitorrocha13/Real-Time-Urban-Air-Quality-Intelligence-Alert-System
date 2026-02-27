import json, time, random, os
from datetime import datetime

CITIES = ["Delhi","Mumbai","Chennai","Bengaluru","Hyderabad"]
FILE = "./data/live_sensors.jsonl"

def generate(city):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "station_id": f"{city[:3]}-{random.randint(1,5)}",
        "pm25": random.uniform(20,300),
        "pm10": random.uniform(20,500),
        "no2": random.uniform(5,150),
        "co": random.uniform(1,30),
        "temperature": random.uniform(18,42),
        "humidity": random.uniform(20,90),
        "city": city
    }

def start_data_stream():
    os.makedirs("data",exist_ok=True)

    with open(FILE,"a") as f:
        while True:
            for city in CITIES:
                r = generate(city)
                f.write(json.dumps(r)+"\n")
                f.flush()   # VERY IMPORTANT → Pathway detects changes
            time.sleep(1)
