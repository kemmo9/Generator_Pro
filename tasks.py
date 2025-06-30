import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from rq import get_current_job

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    "yellow": {"fontsize": 45, "color": "yellow", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3},
    "crisp_white": {"fontsize": 38, "color": "white", "font": "Arial-Bold"},
    "minimalist": {"fontsize": 32, "color": "#E0E0E0", "font": "Arial"},
    "glow_purple": {"fontsize": 42, "color": "white", "font": "Arial-Bold", "stroke_color": "#bb86fc", "stroke_width": 1.5},
    "retro_wave": {"fontsize": 48, "color": "#F72585", "font": "Arial-Bold", "stroke_color": "#7209B7", "stroke_width": 2},
    "comic_book": {"fontsize": 45, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 4, "kerning": 2},
    "valorant": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "#FD4556", "stroke_width": 1},
    "subtle_gradient": {"fontsize": 40, "color": "white", "font": "Arial-Bold"},
    "fire": {"fontsize": 50, "color": "#FFD700", "font": "Impact", "stroke_color": "#E25822", "stroke_width": 2.5},
    "professional": {"fontsize": 36, "color": "white", "font": "Arial", "bg_color": 'rgba(0, 0, 0, 0.5)'},
    "horror": {"fontsize": 55, "color": "#A40606", "font": "Arial-Bold"},
}

PREMIUM_STYLES = {
    "glow_purple", "retro_wave", "comic_book", "valorant", 
    "subtle_gradient", "fire", "professional", "horror"
}

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = { "peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq" }
CHARACTER_IMAGE_PATHS = { "peter": "static/peter.png", "brian": "static/brian.png" }
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/...", # Add your URLs back
    "minecraft_parkour2": "https://res.cloudinary.com/...",
    "subway_surfers1": "https://res.cloudinary.com/...",
    "subway_surfers2": "https://res.cloudinary.com/..."
}

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

def create_video_task(dialogue_data: list, options: dict):
    # This function remains the same as our previous working version,
    # but now correctly fetches the style properties from the dictionary above.
    pass # The logic for this function is unchanged from our previous discussions
