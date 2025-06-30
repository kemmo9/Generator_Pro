import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from rq import get_current_job

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- Centralized Style Definitions ---

# This dictionary is now the single source of truth for all style properties.
# Fonts should be installed on the worker or be common system fonts.
# For custom fonts, you would need to ensure they are loaded into your Render environment.
SUBTITLE_STYLES = {
    # Free Tiers
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    "yellow": {"fontsize": 45, "color": "yellow", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3},
    "crisp_white": {"fontsize": 38, "color": "white", "font": "Arial-Bold"}, # A cleaner free option
    "minimalist": {"fontsize": 32, "color": "#E0E0E0", "font": "Arial"}, # Simple and small

    # Premium Tiers
    "glow_purple": {"fontsize": 42, "color": "white", "font": "Arial-Bold", "stroke_color": "#bb86fc", "stroke_width": 1.5},
    "retro_wave": {"fontsize": 48, "color": "#F72585", "font": "Arial-Bold", "stroke_color": "#7209B7", "stroke_width": 2},
    "comic_book": {"fontsize": 45, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 4, "kerning": 2},
    "valorant": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "#FD4556", "stroke_width": 1},
    "subtle_gradient": {"fontsize": 40, "color": "white", "font": "Arial-Bold"}, # Gradient applied via special handling
    "fire": {"fontsize": 50, "color": "#FFD700", "font": "Impact", "stroke_color": "#E25822", "stroke_width": 2.5},
    "professional": {"fontsize": 36, "color": "white", "font": "Arial", "bg_color": 'rgba(0, 0, 0, 0.5)'}, # With a background bar
    "horror": {"fontsize": 55, "color": "#A40606", "font": "Arial-Bold"},
}

# This set defines which styles require a subscription.
PREMIUM_STYLES = {
    "glow_purple", "retro_wave", "comic_book", "valorant", 
    "subtle_gradient", "fire", "professional", "horror"
}

# (The rest of your config remains the same)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = { "peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq" }
CHARACTER_IMAGE_PATHS = { "peter": "static/peter.png", "brian": "static/brian.png" }
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    # ... etc
}
cloudinary.config(...)

def update_job_progress(message: str):
    # ... (no changes here)

def download_file(url, local_filename):
    # ... (no changes here)

def generate_audio_elevenlabs(text, voice_id, filename):
    # ... (no changes here)

def create_video_task(dialogue_data: list, options: dict):
    # ... (try/finally block starts here)
    try:
        update_job_progress("Initializing...")
        subtitle_style_key = options.get("subtitleStyle", "standard")
        
        # --- MODIFIED: Get style properties from the central dictionary ---
        selected_style = SUBTITLE_STYLES.get(subtitle_style_key, SUBTITLE_STYLES["standard"])

        background_key = options.get("backgroundVideo", "minecraft_parkour1")
        # ... (rest of the initial setup)

        for i, line_data in enumerate(dialogue_data):
            # ... (audio generation loop)
        
        # --- MODIFIED: Compositing uses the fetched style properties ---
        update_job_progress("Compositing video...")
        video_clips_to_compose = [background_clip]
        current_time = 0
        for clip_data in dialogue_clips:
            img_clip = (ImageClip(...)
            
            # The 'selected_style' dictionary is now unpacked directly into the TextClip
            txt_clip = (TextClip(clip_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption')
                        .set_duration(clip_data["audio"].duration)
                        .set_start(current_time)
                        .set_position(("center", 0.8), relative=True))
            
            video_clips_to_compose.extend([img_clip, txt_clip])
            current_time += clip_data["audio"].duration
        
        # ... (The rest of the function remains the same)
    finally:
        # ... (cleanup)
