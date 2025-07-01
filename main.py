import os
import json
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request, Body, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from rq import Queue
import redis

# This import will now work correctly because tasks.py is complete.
from tasks import PREMIUM_STYLES

# --- Configuration & Initialization ---
app = FastAPI()

# This middleware is essential for storing the user's login session in a secure cookie.
# You MUST set APP_SECRET_KEY in your Render Environment Variables for production.
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("APP_SECRET_KEY", "a_very_long_and_super_secret_string_for_local_testing")
)

# Load secrets and configurations from environment variables
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Initialize Redis Queue for background jobs
conn = redis.from_url(REDIS_URL)
q = Queue(connection=conn)

# Mount the 'static' directory to serve CSS, images, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")
# Set up Jinja2 to find HTML files in the 'templates' directory
templates = Jinja2Templates(directory="templates")

# Configure the Auth0 OAuth client
oauth = OAuth()
oauth.register(
    name='auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid profile email'} # Request basic user info
)

# --- User Session Dependency ---
async def get_user(request: Request):
    """A dependency that gets the current user from the session, if they exist."""
    return request.session.get('user')

# --- Page Rendering Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)):
    """Serves the main editor page (index.html)."""
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)):
    """Serves the pricing page (pricing.html)."""
    # Note: We are not passing Stripe keys yet, as payment logic is postponed.
    return templates.TemplateResponse("pricing.html", {"request": request, "user": user})

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    """Serves the favicon to prevent 404 errors in the browser console."""
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "favicon.ico"))

# --- Authentication Routes ---
@app.get('/login')
async def login(request: Request):
    """Redirects the user to the Auth0 universal login page."""
    redirect_uri = "https://www.makeaclip.pro/callback" # Must be in "Allowed Callback URLs"
    return await oauth.auth0.authorize_redirect(request, redirect_uri)

@app.get('/logout')
async def logout(request: Request):
    """Clears the user session and redirects to Auth0's logout endpoint."""
    request.session.clear()
    logout_url = f"https://{AUTH0_DOMAIN}/v2/logout?client_id={AUTH0_CLIENT_ID}&returnTo=https://www.makeaclip.pro"
    return RedirectResponse(url=logout_url)

@app.get('/callback')
async def callback(request: Request):
    """Handles the redirect from Auth0 after a successful login."""
    token = await oauth.auth0.authorize_access_token(request)
    request.session['user'] = token['userinfo'] # Store user data in the secure session cookie
    return RedirectResponse(url="/")

# --- API Routes ---
@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    """Queues a video generation task after checking authentication and template type."""
    if not user: 
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    
    options_data = payload.get("options", {})
    selected_style = options_data.get("subtitleStyle")
    
    # Placeholder for tier logic. For now, everyone is a "pro" user to allow testing.
    user_tier = "pro" 

    if selected_style in PREMIUM_STYLES and user_tier == "free":
        raise HTTPException(status_code=403, detail=f"'{selected_style}' is a premium style. Please upgrade.")
    
    template = options_data.get("template")
    if template == "reddit":
        job = q.enqueue('tasks.create_reddit_video_task', payload.get("reddit_data", {}), options_data, job_timeout='20m')
    elif template == "character":
        job = q.enqueue('tasks.create_video_task', payload.get("dialogue_data", []), options_data, job_timeout='15m')
    else:
        raise HTTPException(status_code=400, detail="Invalid template specified.")
    
    return JSONResponse({"job_id": job.id})

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Checks the status of a video generation job in the Redis queue."""
    job = q.fetch_job(job_id)
    if job is None: 
        raise HTTPException(status_code=404, detail="Job not found.")
    
    response_data = {
        "job_id": job.id, 
        "status": job.get_status(), 
        "progress": job.meta.get('progress', 'In queue...'), 
        "result": job.result
    }
    if job.is_failed: 
        response_data["progress"] = f"Job Failed: {job.exc_info or 'Unknown error'}"
        
    return JSONResponse(response_data)

@app.get("/health")
async def health_check():
    """A simple health check endpoint for Render's monitoring."""
    return {"status": "ok"}
