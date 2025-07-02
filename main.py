import os
from fastapi import FastAPI, Request, Body, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from rq import Queue
import redis
from tasks import PREMIUM_STYLES

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("APP_SECRET_KEY", "a-super-secret-key"))
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
conn = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
q = Queue(connection=conn)
oauth = OAuth()
oauth.register(name='auth0', client_id=os.getenv('AUTH0_CLIENT_ID'), client_secret=os.getenv('AUTH0_CLIENT_SECRET'), server_metadata_url=f"https://{os.getenv('AUTH0_DOMAIN')}/.well-known/openid-configuration", client_kwargs={'scope': 'openid profile email'})

async def get_user(request: Request): return request.session.get('user')

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, user: dict = Depends(get_user)): return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/pricing", response_class=HTMLResponse)
async def read_pricing(request: Request, user: dict = Depends(get_user)): return templates.TemplateResponse("pricing.html", {"request": request, "user": user})

@app.get('/favicon.ico', include_in_schema=False)
async def favicon(): return FileResponse(os.path.join(os.path.dirname(__file__), "static", "favicon.ico"))

@app.get('/login')
async def login(request: Request): return await oauth.auth0.authorize_redirect(request, request.url_for('callback'))

@app.get('/logout')
async def logout(request: Request): request.session.clear(); return RedirectResponse(url="/")

@app.get('/callback')
async def callback(request: Request): token = await oauth.auth0.authorize_access_token(request); request.session['user'] = token['userinfo']; return RedirectResponse(url="/")

@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...), user: dict = Depends(get_user)):
    if not user: raise HTTPException(status_code=401)
    options = payload.get("options", {})
    if options.get("subtitleStyle") in PREMIUM_STYLES and user.get("tier", "free") == "free": raise HTTPException(status_code=403, detail="Premium style.")
    job = q.enqueue(f'tasks.create_{options.get("template", "character")}_video_task', payload.get("dialogue_data", []) if options.get("template") == "character" else payload.get("reddit_data", {}), options)
    return JSONResponse({"job_id": job.id})

@app.get("/api/job-status/{job_id}")
async def get_job_status(job_id: str):
    job = q.fetch_job(job_id);
    if not job: raise HTTPException(status_code=404)
    return JSONResponse({"status": job.get_status(), "progress": job.meta.get('progress', ''), "result": job.result})

@app.get("/health")
async def health_check(): return {"status": "ok"}
