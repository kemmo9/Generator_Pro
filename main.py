import os
import redis
from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rq import Queue
from typing import Dict, List

# --- Configuration ---
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

# --- App Initialization ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate-video")
async def queue_video_task(payload: Dict = Body(...)):
    # UPDATED: We now expect a 'dialogue' key with a list of objects
    dialogue_data = payload.get("dialogue", [])
    if not dialogue_data:
        raise HTTPException(status_code=400, detail="Dialogue data is empty.")
    
    # We pass the entire list to the worker task
    job = q.enqueue('tasks.create_video_task', dialogue_data, job_timeout='10m', result_ttl=3600)
    
    return JSONResponse({"job_id": job.id})

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {"job_id": job.id, "status": job.get_status(), "result": None}
    
    if job.is_finished:
        response["result"] = job.result
    
    return JSONResponse(response)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
