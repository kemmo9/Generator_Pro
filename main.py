# ... (all your imports and setup code at the top of main.py) ...

# This set should be imported from your tasks file or defined here
# to check against.
PREMIUM_STYLES = {
    "glow_purple", "retro_wave", "comic_book", "valorant", 
    "subtle_gradient", "fire", "professional", "horror"
}

# ... (all your other routes like /login, /pricing, etc.) ...

# --- MODIFIED: The generate-video endpoint now checks for subscription status ---
@app.post("/api/generate-video")
async def queue_video_task(request: Request, payload: dict = Body(...)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    options_data = payload.get("options", {})
    selected_style = options_data.get("subtitleStyle")
    
    # --- THIS IS THE ENFORCEMENT LOGIC ---
    # We will get the user's tier from the session (which we will set up next)
    # For now, let's assume a free user for demonstration. In the final step, we'll
    # get this from the Auth0 metadata via the user session.
    user_tier = user.get("https://makeaclip.pro/tier", "free") # Default to 'free' if no tier is set

    if selected_style in PREMIUM_STYLES and user_tier == "free":
        raise HTTPException(
            status_code=403,  # 403 Forbidden
            detail="You must have a Pro or Platinum subscription to use this premium subtitle style. Please upgrade on the pricing page."
        )

    dialogue_data = payload.get("dialogue", [])
    if not dialogue_data:
        raise HTTPException(status_code=400, detail="Dialogue data is empty.")
    
    job = q.enqueue('tasks.create_video_task', dialogue_data, options_data, job_timeout='15m', result_ttl=3600)
    return {"job_id": job.id}

# ... (the rest of your main.py file) ...
