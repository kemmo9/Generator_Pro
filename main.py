import os
import json
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from rq import Queue
import redis

# --- Configuration ---
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

# --- App Initialization & Middleware ---
app = FastAPI()

# This middleware is essential for storing the user's login session in a secure cookie.
# You MUST set APP_SECRET_KEY in your Render Environment Variables.
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY"))

# Mount static files (CSS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Auth0 OAuth Configuration ---
oauth = OAuth()
oauth.register(
    name='auth0',
    client_id=os.getenv('AUTH0_CLIENT_ID'),
    client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
    server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid profile email'}
)

# --- Authentication Routes (The New Tactic) ---
@app.get('/login')
async def login(request: Request):
    """Redirects the user to Auth0's hosted login page."""
    redirect_uri = "https://www.makeaclip.pro/callback" # Use the live URL
    return await oauth.auth0.authorize_redirect(request, redirect_uri)

@app.get('/logout')
async def logout(request: Request):
    """Logs the user out, clears the session cookie, and redirects."""
    request.session.clear()
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')
    # This URL must be in the "Allowed Logout URLs" in your Auth0 dashboard
    return_to_url = "https://www.makeaclip.pro"
    logout_url = f"https://{auth0_domain}/v2/logout?client_id={client_id}&returnTo={return_to_url}"
    return RedirectResponse(url=logout_url)

@app.get('/callback')
async def callback(request: Request):
    """
    Handles the redirect from Auth0 after login.
    Fetches the user's token and stores their info in the session.
    """
    token = await oauth.auth0.authorize_access_token(request)
    request.session['user'] = token['userinfo']
    return RedirectResponse(url="/") # Redirect back to the main page

# --- Page and API Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    Serves the main index page. It passes the user's information from the
    session cookie to the template if they are logged in.
    """
    user = request.session.get('user')
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "user": user}
    )

@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...)):
    """
    Queues the video generation task. Now checks for a valid session
    instead of a bearer token.
    """
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    dialogue_data = payload.get("dialogue", [])
    options_data = payload.get("options", {})
    if not dialogue_data:
        raise HTTPException(status_code=400, detail="Dialogue data is empty.")
    
    job = q.enqueue('tasks.create_video_task', dialogue_data, options_data, job_timeout='15m', result_ttl=3600)
    return {"job_id": job.id}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = q.fetch_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response = {"job_id": job.id, "status": job.get_status(), "progress": job.meta.get('progress', 'Waiting...'), "result": job.result}
    if job.is_failed:
        response["progress"] = f"Job Failed: {job.exc_info}"
    return response

@app.get("/health")
async def health_check():
    return {"status": "ok"}
