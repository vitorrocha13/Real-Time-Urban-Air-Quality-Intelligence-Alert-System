import threading
from app.data_simulator import start_data_stream
from app.pathway_pipeline import run_pathway_pipeline
from app.api_server import start_api

def main():
    threading.Thread(target=start_data_stream, daemon=True).start()
    threading.Thread(target=run_pathway_pipeline, daemon=True).start()
    start_api()

if __name__ == "__main__":
    main()
