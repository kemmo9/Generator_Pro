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

# Import from tasks.py
from tasks import PREMIUM_STYLES, create_video_task, create_reddit_video_task, create_reddit_preview_image

# --- App Initialization & Config ---
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "a_very_long_and_super_secret_string_for_local_testing"))
stripe.api_key = os.getenv("STRIPE_SECRET_KEY"); STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET = os.getenv('AUTH0_DOMAIN'), os.getenv('AUTH0_CLIENT_ID'), os.getenv('AUTH0_CLIENT_SECRET')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

conn = redis.from_url(REDIS_URL); q = Queue(connection=conn)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

oauth = OAuth()
oauth.register(
    name='auth0', client_id=AUTH0_CLIENT_ID, client_secret=AUTH0_CLIENT_SECRET,
    server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
    client_kwargs={'scope': 'openid profile email update:users'}
)

# --- User Session & Page Routes ---
async def get_user(request: Request): return request.session.get('user')

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)):
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)):
    return templates.TemplateResponse("pricing.html", {"request": request, "user": user, "stripe_publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY")})

@app.get('/favicon.ico', include_in_schema=False)
async def favicon(): return FileResponse(os.path.join("static", "favicon.ico"))

# --- Auth Routes ---
@app.get('/login')
async def login(request: Request):
    return await oauth.auth0.authorize_redirect(request, "https://www.makeaclip.pro/callback")

@app.get('/logout')
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url=f"https://{AUTH0_DOMAIN}/v2/logout?client_id={AUTH0_CLIENT_ID}&returnTo=https://www.makeaclip.pro")

@app.get('/callback')
async def callback(request: Request):
    token = await oauth.auth0.authorize_access_token(request); request.session['user'] = token['userinfo']; return RedirectResponse(url="/")

# --- API Routes ---
@app.post("/api/generate-reddit-preview")
async def generate_reddit_preview(data: dict = Body(...)):
    """Generates and returns a static preview image for the Reddit editor."""
    try:
        image_path = create_reddit_preview_image(data)
        return FileResponse(image_path, media_type="image/png",_headers={"X-Delete-After-Use": "true"})
    except Exception as e:
        print(f"Error generating preview: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate preview image.")

@app.post("/api/create-checkout-session")
async def create_checkout_session(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    if not user: raise HTTPException(status_code=401, detail="Must be logged in.")
    try:
        session = stripe.checkout.Session.create(
            line_items=[{'price': payload.get("price_id"), 'quantity': 1}], mode='subscription',
            success_url="https://www.makeaclip.pro/pricing?checkout_status=success",
            cancel_url="https://www.makeaclip.pro/pricing?checkout_status=cancel",
            client_reference_id=user['sub']
        )
        return JSONResponse({'id': session.id})
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    # TODO: Add logic to update the user's tier in Auth0 Management API
    return JSONResponse({'status': 'success'})

@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    if not user: raise HTTPException(status_code=401, detail="Not authenticated")
    options = payload.get("options", {}); selected_style = options.get("subtitleStyle")
    user_tier = user.get("https://makeaclip.pro/tier", "free") 

    if selected_style in PREMIUM_STYLES and user_tier == "free":
        raise HTTPException(status_code=403, detail=f"'{selected_style.replace('_', ' ').title()}' is premium. Please upgrade.")
    
    template = options.get("template")
    if template == "reddit":
        job = q.enqueue(create_reddit_video_task, payload.get("reddit_data", {}), options, job_timeout='5m')
    elif template == "character":
        job = q.enqueue(create_video_task, payload.get("dialogue_data", []), options, job_timeout='5m')
    else: raise HTTPException(status_code=400, detail="Invalid template specified.")
    
    return JSONResponse({"job_id": job.id})

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = q.fetch_job(job_id)
    if not job: raise HTTPException(status_code=404, detail="Job not found.")
    response = {"status": job.get_status(), "progress": job.meta.get('progress', 'In queue...'), "result": job.result}
    if job.is_failed: response["progress"] = f"Job Failed: {job.exc_info or 'Unknown error'}"
    return JSONResponse(response)

@app.get("/health")
async def health_check(): return {"status": "ok"}
