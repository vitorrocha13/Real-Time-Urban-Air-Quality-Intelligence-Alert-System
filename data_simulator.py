"""
GreenPulse AI — Data Simulator
================================
Simulates real-time sensor streams for Indian cities by writing
JSONL records to a file that Pathway reads in streaming mode.

Design:
  - Each city gets a realistic pollution profile (seasonal + time-of-day)
  - Records are appended at configurable intervals
  - Supports burst mode (inject HIGH-risk spike for demo)
"""

import json
import time
import random
import argparse
import math
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

# ── City Profiles ──────────────────────────────────────────────────────────────

CITY_PROFILES = {
    "Delhi": {
        "base_pm25":   90.0,
        "base_pm10":  150.0,
        "base_no2":    60.0,
        "base_co":      3.5,
        "base_temp":   22.0,
        "base_humidity": 65.0,
        "variability": 1.8,   # High — industrial + traffic
    },
    "Mumbai": {
        "base_pm25":   50.0,
        "base_pm10":   80.0,
        "base_no2":    45.0,
        "base_co":      2.0,
        "base_temp":   30.0,
        "base_humidity": 78.0,
        "variability": 1.2,
    },
    "Bengaluru": {
        "base_pm25":   35.0,
        "base_pm10":   60.0,
        "base_no2":    38.0,
        "base_co":      1.5,
        "base_temp":   25.0,
        "base_humidity": 62.0,
        "variability": 1.0,
    },
    "Chennai": {
        "base_pm25":   40.0,
        "base_pm10":   70.0,
        "base_no2":    42.0,
        "base_co":      1.8,
        "base_temp":   33.0,
        "base_humidity": 80.0,
        "variability": 1.1,
    },
    "Hyderabad": {
        "base_pm25":   55.0,
        "base_pm10":   90.0,
        "base_no2":    50.0,
        "base_co":      2.2,
        "base_temp":   28.0,
        "base_humidity": 58.0,
        "variability": 1.3,
    },
    "Kolkata": {
        "base_pm25":   75.0,
        "base_pm10":  120.0,
        "base_no2":    55.0,
        "base_co":      3.0,
        "base_temp":   27.0,
        "base_humidity": 72.0,
        "variability": 1.5,
    },
    "Pune": {
        "base_pm25":   38.0,
        "base_pm10":   65.0,
        "base_no2":    35.0,
        "base_co":      1.4,
        "base_temp":   26.0,
        "base_humidity": 55.0,
        "variability": 1.0,
    },
    "Ahmedabad": {
        "base_pm25":   65.0,
        "base_pm10":  110.0,
        "base_no2":    52.0,
        "base_co":      2.8,
        "base_temp":   30.0,
        "base_humidity": 48.0,
        "variability": 1.4,
    },
}


# ── Noise and Pattern Helpers ──────────────────────────────────────────────────

def _diurnal_factor(hour: int) -> float:
    """
    Returns a multiplier mimicking real-world pollution peaks:
      - Rush hour morning spike (8–10 AM)
      - Afternoon lull (2–4 PM)
      - Evening rush spike (6–9 PM)
      - Overnight low
    """
    # Sine curve biased toward daytime traffic peaks
    cycle = 1.0 + 0.4 * math.sin(math.pi * (hour - 6) / 12)
    # Extra morning rush
    if 7 <= hour <= 10:
        cycle *= 1.25
    # Extra evening rush
    if 18 <= hour <= 21:
        cycle *= 1.20
    return max(0.6, min(cycle, 2.0))


def _gaussian_noise(scale: float) -> float:
    return random.gauss(0, scale)


# ── Record Generator ───────────────────────────────────────────────────────────

def generate_record(city: str, spike: bool = False) -> dict:
    """
    Generate one realistic sensor reading for `city`.

    Args:
        city  : city name (must be in CITY_PROFILES)
        spike : if True, simulate a HIGH-risk pollution event

    Returns:
        dict matching the expected Pathway schema
    """
    profile = CITY_PROFILES[city]
    v = profile["variability"]
    now = datetime.now(timezone.utc)
    hour = now.hour

    diurnal = _diurnal_factor(hour)
    spike_mult = random.uniform(2.5, 4.5) if spike else 1.0

    def noisy(base: float, noise_pct: float = 0.15) -> float:
        raw = base * diurnal * spike_mult + _gaussian_noise(base * noise_pct * v)
        return round(max(0.0, raw), 2)

    return {
        "timestamp":   now.isoformat(),
        "city":        city,
        "sensor_id":   f"{city.lower()[:3]}-{random.randint(1, 10):02d}",
        "pm25":        noisy(profile["base_pm25"]),
        "pm10":        noisy(profile["base_pm10"]),
        "no2":         noisy(profile["base_no2"]),
        "co":          noisy(profile["base_co"], noise_pct=0.10),
        "temperature": round(profile["base_temp"] + _gaussian_noise(2.5), 1),
        "humidity":    round(
            max(10.0, min(100.0, profile["base_humidity"] + _gaussian_noise(5.0))), 1
        ),
    }


# ── Simulator Main Loop ────────────────────────────────────────────────────────

class DataSimulator:
    """
    Continuously writes sensor records to an output JSONL file.
    Pathway's streaming reader picks up new lines automatically.
    """

    def __init__(
        self,
        output_path: Path,
        interval_seconds: float = 2.0,
        cities: list[str] | None = None,
        spike_probability: float = 0.05,
    ):
        self.output_path = output_path
        self.interval = interval_seconds
        self.cities = cities or list(CITY_PROFILES.keys())
        self.spike_prob = spike_probability
        self._record_count = 0

    def _write_record(self, record: dict) -> None:
        with open(self.output_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        self._record_count += 1

    def run(self, max_records: int | None = None) -> None:
        """
        Start streaming. Writes one record per city per tick.

        Args:
            max_records: stop after N total records (None = run forever)
        """
        logger.info(
            f"DataSimulator started → {self.output_path} | "
            f"interval={self.interval}s | cities={self.cities}"
        )
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            while True:
                for city in self.cities:
                    spike = random.random() < self.spike_prob
                    record = generate_record(city, spike=spike)
                    self._write_record(record)

                    if spike:
                        logger.warning(f"🚨 Pollution SPIKE injected — {city}")

                logger.debug(f"Batch written | total records: {self._record_count}")

                if max_records and self._record_count >= max_records:
                    logger.info(f"Reached max_records={max_records}. Stopping.")
                    break

                time.sleep(self.interval)

        except KeyboardInterrupt:
            logger.info("DataSimulator stopped by user.")


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="GreenPulse Data Simulator")
    parser.add_argument(
        "--output", type=str, default="data/sensor_stream.jsonl",
        help="Output JSONL file path"
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="Seconds between record batches"
    )
    parser.add_argument(
        "--cities", nargs="+", default=None,
        help="City subset (default: all)"
    )
    parser.add_argument(
        "--spike-prob", type=float, default=0.05,
        help="Probability of injecting a pollution spike per city per tick"
    )
    parser.add_argument(
        "--max-records", type=int, default=None,
        help="Stop after N records (default: run indefinitely)"
    )
    args = parser.parse_args()

    simulator = DataSimulator(
        output_path=Path(args.output),
        interval_seconds=args.interval,
        cities=args.cities,
        spike_probability=args.spike_prob,
    )
    simulator.run(max_records=args.max_records)


if __name__ == "__main__":
    main()
