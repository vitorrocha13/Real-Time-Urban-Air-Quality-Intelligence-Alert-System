"""
GreenPulse AI — Main Orchestrator
====================================
Starts all system components in parallel:
  1. Data Simulator       → writes JSONL sensor stream
  2. Pathway Pipeline     → reads stream, runs inference, writes enriched output
  3. FastAPI Server       → serves REST API from enriched stream
  4. (Dashboard)          → started separately via: streamlit run dashboard/dashboard.py

Usage:
    python main.py [--mode all|simulator|pipeline|api]

Notes:
  - Each component runs in a separate process.
  - Graceful shutdown on Ctrl+C terminates all children.
  - For production: use Docker Compose (see docs/workflow.md).
"""

import argparse
import multiprocessing
import sys
import time
from pathlib import Path
from loguru import logger

# ── Configure Logging ──────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> — {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/greenpulse.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG",
)

# ── Component Launchers ────────────────────────────────────────────────────────

def _run_simulator():
    """Entry point for the data simulator subprocess."""
    from app.data_simulator import DataSimulator
    sim = DataSimulator(
        output_path=Path("data/sensor_stream.jsonl"),
        interval_seconds=2.0,
        spike_probability=0.05,
    )
    sim.run()


def _run_pipeline():
    """Entry point for the Pathway streaming pipeline subprocess."""
    # Brief delay to let simulator create the initial file
    time.sleep(3)
    from app.pathway_pipeline import build_pipeline
    build_pipeline(
        input_path="data/sensor_stream.jsonl",
        output_path="data/enriched_stream.jsonl",
    )


def _run_api():
    """Entry point for the FastAPI server subprocess."""
    # Brief delay to let pipeline produce initial output
    time.sleep(6)
    import uvicorn
    uvicorn.run(
        "app.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="warning",
    )


# ── Process Manager ────────────────────────────────────────────────────────────

COMPONENTS = {
    "simulator": _run_simulator,
    "pipeline":  _run_pipeline,
    "api":       _run_api,
}


def start_all(mode: str = "all") -> None:
    """
    Launch selected components as independent processes.
    Blocks until Ctrl+C or any child exits unexpectedly.
    """
    Path("data").mkdir(exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

    # Pre-train / load model before forking (avoids race condition)
    logger.info("Initialising AI model…")
    from app.ai_model import ModelManager
    ModelManager()
    logger.info("AI model ready ✓")

    targets = list(COMPONENTS.keys()) if mode == "all" else [mode]
    processes: list[multiprocessing.Process] = []

    for name in targets:
        fn = COMPONENTS[name]
        p = multiprocessing.Process(target=fn, name=name, daemon=True)
        p.start()
        processes.append(p)
        logger.info(f"Started [{name}] — PID {p.pid}")

    if "api" in targets:
        logger.info("Dashboard: run separately →  streamlit run dashboard/dashboard.py")
        logger.info("API docs:                    http://localhost:8000/docs")
        logger.info("API latest:                  http://localhost:8000/api/v1/latest")

    # ── Monitor ──────────────────────────────────────────────────────────────
    try:
        while True:
            for p in processes:
                if not p.is_alive():
                    logger.error(f"Process [{p.name}] (PID {p.pid}) terminated unexpectedly!")
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Shutting down GreenPulse AI…")
    finally:
        for p in processes:
            if p.is_alive():
                p.terminate()
                logger.info(f"Terminated [{p.name}]")
        for p in processes:
            p.join(timeout=5)
        logger.info("All processes stopped. Goodbye.")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="GreenPulse AI — Real-Time Urban Air Quality System"
    )
    parser.add_argument(
        "--mode",
        choices=["all", "simulator", "pipeline", "api"],
        default="all",
        help="Which component(s) to start (default: all)",
    )
    args = parser.parse_args()
    start_all(mode=args.mode)


if __name__ == "__main__":
    main()
