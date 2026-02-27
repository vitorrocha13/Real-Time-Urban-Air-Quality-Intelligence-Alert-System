import json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from config.settings import API_HOST, API_PORT, PREDICTIONS_FILE

app = FastAPI(title="GreenPulse AI API")

def read_latest_jsonl(path, n=100):
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    out = []
    for l in lines[-n:]:
        if l.strip():
            out.append(json.loads(l))
    return out

@app.get("/health")
async def health():
    return {"status":"running","service":"GreenPulse AI"}

@app.get("/api/predictions")
async def predictions():
    data = read_latest_jsonl(PREDICTIONS_FILE, 100)
    return JSONResponse({"status":"ok","count":len(data),"data":data})

def start_api():
    uvicorn.run(app, host=API_HOST, port=API_PORT)
