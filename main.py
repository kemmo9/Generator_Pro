import os
import json
import stripe
from authlib.integrations.starlette_client import OAuth
from fastapi import FastAPI, Request, Body, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from rq import Queue
import redis

# --- Configuration & Initialization ---
app = FastAPI()

# --- THIS IS THE CRITICAL FIX ---
# We provide a default, non-secure key so the app can always start.
# You MUST set a real, secure key in your Render Environment Variables for production.
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("APP_SECRET_KEY", "a_dummy_secret_key_for_startup_only")
)

# Stripe API Key (loaded from Render's secrets)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Redis Queue for video processing
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
conn = redis.from_url(redis_url)
q = Queue(connection=conn)

# Static files and templates
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

# --- Re-adding all your routes ---

async def get_user(request: Request):
    return request.session.get('user')

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)):
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    return templates.TemplateResponse(
        "pricing.html", 
        {"request": request, "user": user, "stripe_publishable_key": stripe_publishable_key}
    )

@app.get('/login')
async def login(request: Request):
    redirect_uri = "https://www.makeaclip.pro/callback"
    return await oauth.auth0.authorize_redirect(request, redirect_uri)

@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    client_id = os.getenv('AUTH0_CLIENT_ID')
    return_to_url = "https://www.makeaclip.pro"
    logout_url = f"https://{auth0_domain}/v2/logout?client_id={client_id}&returnTo={return_to_url}"
    return RedirectResponse(url=logout_url)

@app.get('/callback')
async def callback(request: Request):
    token = await oauth.auth0.authorize_access_token(request)
    request.session['user'] = token['userinfo']
    return RedirectResponse(url="/")

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request, payload: dict = Body(...)):
    user = await get_user(request)
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
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Webhook error")
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        auth0_user_id = session.get('client_reference_id')
        print(f"Payment successful for user: {auth0_user_id}.")
    return JSONResponse({'status': 'success'})

@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...)):
    if not request.session.get('user'):
        raise HTTPException(status_code=401, detail="Not authenticated")
    dialogue_data = payload.get("dialogue", [])
    job = q.enqueue('tasks.create_video_task', dialogue_data, payload.get("options", {}))
    return {"job_id": job.id}

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = q.fetch_job(job_id)
    if job is None: return HTTPException(status_code=404)
    return {"status": job.get_status(), "progress": job.meta.get('progress', ''), "result": job.result}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
