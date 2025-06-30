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

# Session Middleware for user login
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY"))

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
    client_kwargs={'scope': 'openid profile email update:users'} # IMPORTANT: Add update:users scope
)

# --- Authentication & User Session Management ---
async def get_user(request: Request):
    """Dependency to get the current user from the session, if any."""
    return request.session.get('user')

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)):
    # Pass the Stripe Publishable key to the pricing page template
    stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
    return templates.TemplateResponse(
        "pricing.html", 
        {"request": request, "user": user, "stripe_publishable_key": stripe_publishable_key}
    )

# --- Stripe API Routes ---
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
            # This links the Stripe session to the Auth0 user ID
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the 'checkout.session.completed' event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        auth0_user_id = session.get('client_reference_id')
        # TODO: Here you will add the code to update the user's metadata in Auth0
        print(f"Payment successful for user: {auth0_user_id}. Need to update their Auth0 profile.")

    return JSONResponse({'status': 'success'})

# ... (keep all your other routes like /login, /logout, /callback, api/generate-video, etc.) ...
