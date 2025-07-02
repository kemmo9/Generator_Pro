import os
import json
import stripe
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request, Body, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from rq import Queue
import redis

# Import the premium styles set from tasks
from tasks import PREMIUM_STYLES

# --- Configuration & Initialization ---
app = FastAPI()

# THIS IS THE CRITICAL FIX for Render startup issues.
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("APP_SECRET_KEY", "a_very_long_and_super_secret_string_for_local_testing")
)

# Load secrets and configurations from environment variables
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

# Initialize Redis Queue
conn = redis.from_url(REDIS_URL)
q = Queue(connection=conn)

# Mount static files (CSS, images) and configure templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Configure Auth0 OAuth client
oauth = OAuth()
oauth.register(
    name='auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid profile email update:users'}
)

# --- User Session Dependency ---
async def get_user(request: Request):
    """A dependency that gets the current user from the session, if they exist."""
    return request.session.get('user')

# --- Page Rendering Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)):
    """Serves the main editor page."""
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)):
    """Serves the pricing page."""
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    return templates.TemplateResponse(
        "pricing.html", 
        {"request": request, "user": user, "stripe_publishable_key": stripe_publishable_key}
    )

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    """Serves a blank icon to prevent 404 errors in the browser console."""
    return FileResponse(os.path.join("static", "favicon.ico"))

# --- Authentication Routes ---
@app.get('/login')
async def login(request: Request):
    """Redirects the user to the Auth0 login page."""
    redirect_uri = "https://www.makeaclip.pro/callback"
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
    request.session['user'] = token['userinfo']
    return RedirectResponse(url="/")

# --- API Routes ---
@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    """Creates a Stripe checkout session for a subscription."""
    if not user:
        raise HTTPException(status_code=401, detail="You must be logged in to subscribe.")
    
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[{'price': payload.get("price_id"), 'quantity': 1}],
            mode='subscription',
            success_url="https://www.makeaclip.pro/pricing?checkout_status=success",
            cancel_url="https://www.makeaclip.pro/pricing?checkout_status=cancel",
            client_reference_id=user['sub']
        )
        return JSONResponse({'id': checkout_session.id})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    """Listens for successful payments from Stripe."""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        auth0_user_id = session.get('client_reference_id')
        # TODO: Add logic here to update the user's tier in Auth0 Management API
        print(f"Payment successful for user: {auth0_user_id}. Their tier needs to be updated.")

    return JSONResponse({'status': 'success'})

@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    """Queues a video generation task after checking user authentication and tier."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    options_data = payload.get("options", {})
    selected_style = options_data.get("subtitleStyle")
    user_tier = user.get("https://makeaclip.pro/tier", "free") 

    if selected_style in PREMIUM_STYLES and user_tier == "free":
        raise HTTPException(
            status_code=403, 
            detail=f"'{selected_style.replace('_', ' ').title()}' is a premium style. Please upgrade to use it."
        )
    
    template = options_data.get("template")
    if template == "reddit":
        job = q.enqueue('tasks.create_reddit_video_task', payload.get("reddit_data", {}), options_data)
    elif template == "character":
        job = q.enqueue('tasks.create_video_task', payload.get("dialogue_data", []), options_data)
    else:
        raise HTTPException(status_code=400, detail="Invalid template specified.")
    
    return {"job_id": job.id}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Checks the status of a video generation job."""
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
    """A simple health check endpoint for Render."""
    return {"status": "ok"}
