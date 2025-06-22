import os
import redis
from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from rq import Queue
from typing import Dict

# --- Configuration ---
# Connect to the Redis queue provided by Render
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
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/generate-video")
async def queue_video_task(payload: Dict = Body(...)):
    """Accepts a script, and enqueues it as a job for the worker."""
    script = payload.get("script", "")
    if not script:
        raise HTTPException(status_code=400, detail="Script is empty.")
    
    # Enqueue the job. 'tasks.create_video_task' is the function to run.
    # The result_ttl keeps the job result info for 1 hour.
    job = q.enqueue('tasks.create_video_task', script, job_timeout='10m', result_ttl=3600)
    
    # Return the Job ID to the frontend
    return JSONResponse({"job_id": job.id})

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Fetches the status of a job and the result if it's finished."""
    job = q.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {
        "job_id": job.id,
        "status": job.get_status(),
        "result": None
    }
    
    if job.is_finished:
        response["result"] = job.result
    
    return JSONResponse(response)

@app.get("/health")
async def health_check():
    """A simple endpoint for Render to check if the service is alive."""
    return {"status": "ok"}