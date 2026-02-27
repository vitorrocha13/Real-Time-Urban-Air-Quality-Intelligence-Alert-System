from fastapi import FastAPI
import json, os

app = FastAPI()

def read_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(l) for l in f.readlines()[-100:]]

@app.get("/api/predictions")
def predictions():
    return {"data": read_jsonl("./data/predictions.jsonl")}

def start_api():
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)