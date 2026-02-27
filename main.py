import threading
from data_simulator import start_data_stream
from pathway_pipeline import run_pathway_pipeline
from api_server import start_api

if __name__ == "__main__":

    threading.Thread(target=start_data_stream, daemon=True).start()
    threading.Thread(target=run_pathway_pipeline, daemon=True).start()

    start_api()