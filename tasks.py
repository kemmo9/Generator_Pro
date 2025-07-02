import os
import requests
import textwrap
import time
import cloudinary
import cloudinary.uploader
import PIL.Image
from PIL import Image as PILImage, ImageDraw, ImageFont
from moviepy.editor import *
from rq import get_current_job

# --- Configuration & Initial Setup ---

# This ensures compatibility with newer versions of the Pillow library for image processing.
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# Define base directories to locate static assets like fonts and templates.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# The "source of truth" for all available subtitle styles and their properties.
SUBTITLE_STYLES = {
    # Free Styles
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    "yellow": {"fontsize": 45, "color": "#FFD700", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3, "kerning": 1},
    "minimalist": {"fontsize": 36, "color": "#E0E0E0", "font": "Arial"},
    
    # Premium Styles (Requires a paid subscription)
    "glow_purple": {"fontsize": 42, "color": "white", "font": "Arial-Bold", "stroke_color": "#bb86fc", "stroke_width": 1.5},
    "valorant": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "#FD4556", "stroke_width": 2},
    "comic_book": {"fontsize": 45, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 5, "kerning": 2},
    "professional": {"fontsize": 36, "color": "#FFFFFF", "font": "Arial", "bg_color": 'rgba(0, 0, 0, 0.6)'},
    "horror": {"fontsize": 55, "color": "#A40606", "font": "Verdana-Bold", "kerning": -2},
    "retro_wave": {"fontsize": 48, "color": "#F72585", "font": "Arial-Bold", "stroke_color": "#7209B7", "stroke_width": 2},
    "fire": {"fontsize": 50, "color": "#FFD700", "font": "Impact", "stroke_color": "#E25822", "stroke_width": 2.5},
    "ice": {"fontsize": 48, "color": "white", "font": "Arial-Bold", "stroke_color": "#00B4D8", "stroke_width": 2.5}
}

# A simple set for the backend to quickly check if a style is premium.
PREMIUM_STYLES = {
    "glow_purple", "valorant", "comic_book", "professional",
    "horror", "retro_wave", "fire", "ice"
}

# Load API keys and other configurations from environment variables.
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key=os.getenv("CLOUDINARY_API_KEY"), 
    api_secret=os.getenv("CLOUDINARY_API_SECRET"), 
    secure=True
)

# Static asset definitions.
VOICE_IDS = {
    "peter": "BrXwCQ7xdzi6T5h2idQP", 
    "brian": "jpuuy9amUxVn651Jjmtq",
    "reddit": "jpuuy9amUxVn651Jjmtq" # Using a consistent voice for Reddit stories
}
CHARACTER_IMAGE_PATHS = {
    "peter": os.path.join(STATIC_DIR, "peter.png"), 
    "brian": os.path.join(STATIC_DIR, "brian.png")
}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}

# --- Helper Functions ---
def update_job_progress(message: str):
    """Updates the 'progress' metadata of the current RQ job."""
    job = get_current_job()
    if job:
        job.meta['progress'] = message
        job.save_meta()
        print(f"Job {job.id}: {message}")

def download_file(url, local_filename):
    """Downloads a file from a URL, saving it locally."""
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def generate_audio_elevenlabs(text, filename, voice_id):
    """Generates speech from text using the ElevenLabs API."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200:
        raise Exception(f"ElevenLabs API Error: {response.status_code} - {response.text}")
    with open(filename, "wb") as f:
        f.write(response.content)

def create_reddit_post_image(data):
    """Generates the static image of the Reddit post header."""
    job_id = get_current_job().id
    template = PILImage.open(os.path.join(STATIC_DIR, "reddit_template_final.png")).convert("RGBA")
    draw = ImageDraw.Draw(template)
    
    # Define fonts
    try:
        font_bold = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-SemiBold.ttf"), 28)
        font_heavy = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-Bold.ttf"), 44)
    except IOError:
        font_bold = ImageFont.load_default()
        font_heavy = ImageFont.load_default()

    # Draw text onto the template
    draw.text((120, 48), data.get('subreddit', 'r/stories'), font=font_bold, fill="#000000")
    
    y_pos = 155
    for line in textwrap.wrap(data.get('title', ''), width=40):
        draw.text((60, y_pos), line, font=font_heavy, fill="#1a1b1e")
        y_pos += 55 # Move down for the next line
        
    draw.text((150, 485), data.get('upvotes', '99+'), font=font_bold, fill="#636466", anchor="ls")
    draw.text((310, 485), data.get('comments', '99+'), font=font_bold, fill="#636466", anchor="ls")
    
    # Save the generated image
    filename = f"temp_reddit_{job_id}.png"
    template.save(filename)
    return filename

# --- Main Task Functions ---

def create_reddit_video_task(reddit_data: dict, options: dict):
    """Generates a video from a Reddit story post."""
    job_id = get_current_job().id
    temp_files = []
    
    try:
        update_job_progress("Generating assets...")
        full_text = f"{reddit_data.get('title', '')}. {reddit_data.get('body', '')}"
        
        # 1. Generate Audio
        vo_filename = f"temp_vo_{job_id}.mp3"
        temp_files.append(vo_filename)
        generate_audio_elevenlabs(full_text, vo_filename, VOICE_IDS['reddit'])
        audio_clip = AudioFileClip(vo_filename)

        # 2. Generate Reddit Post Image
        img_path = create_reddit_post_image(reddit_data)
        temp_files.append(img_path)
        post_image_clip = ImageClip(img_path).set_duration(audio_clip.duration).resize(width=1000).set_position(reddit_data.get('position', 'center'))

        # 3. Download Background Video
        background_key = options.get("backgroundVideo", "minecraft_parkour1")
        bg_url = BACKGROUND_VIDEO_URLS.get(background_key)
        bg_path = download_file(bg_url, f"temp_bg_{job_id}.mp4")
        temp_files.append(bg_path)
        background_clip = VideoFileClip(bg_path).subclip(0, audio_clip.duration).set_audio(audio_clip)

        update_job_progress("Compositing video...")
        final_video = CompositeVideoClip([background_clip, post_image_clip], size=background_clip.size)
        
        # 4. Render and Upload
        output_path = f"final_reddit_{job_id}.mp4"
        temp_files.append(output_path)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading to cloud...")
        upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        
        update_job_progress("Finished!")
        return {"video_url": upload_result['secure_url']}
    finally:
        # Cleanup
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)

def create_video_task(dialogue_data: list, options: dict):
    """Generates a video from character dialogue lines."""
    job_id = get_current_job().id
    temp_files = []
    video_clips = []
    audio_clips = []
    try:
        update_job_progress("Initializing...")
        subtitle_style_key = options.get("subtitleStyle", "standard")
        selected_style = SUBTITLE_STYLES.get(subtitle_style_key, SUBTITLE_STYLES["standard"])
        background_key = options.get("backgroundVideo", "minecraft_parkour1")
        background_video_url = BACKGROUND_VIDEO_URLS.get(background_key)

        update_job_progress("Generating audio clips...")
        for i, line in enumerate(dialogue_data):
            filename = f"temp_audio_{job_id}_{i}.mp3"
            temp_files.append(filename)
            generate_audio_elevenlabs(line['text'], filename, VOICE_IDS[line['character']])
            audio_clips.append(AudioFileClip(filename))

        update_job_progress("Stitching audio...")
        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        
        update_job_progress("Downloading background...")
        bg_path = download_file(background_video_url, f"temp_bg_{job_id}.mp4")
        temp_files.append(bg_path)
        background_clip = VideoFileClip(bg_path).subclip(0, final_audio.duration).set_audio(final_audio)

        update_job_progress("Compositing video...")
        composited_clips = [background_clip]
        current_time = 0
        for i, line_data in enumerate(dialogue_data):
            img_clip = ImageClip(CHARACTER_IMAGE_PATHS[line_data["character"]]).set_duration(audio_clips[i].duration).set_start(current_time).resize(height=300).set_position(line_data.get("imagePlacement", "center"))
            txt_clip = TextClip(line_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            composited_clips.extend([img_clip, txt_clip])
            current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip(composited_clips, size=background_clip.size)
        
        output_path = f"final_char_{job_id}.mp4"
        temp_files.append(output_path)
        
        update_job_progress("Rendering final video...")
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading to cloud...")
        upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        
        update_job_progress("Finished!")
        return {"video_url": upload_result['secure_url']}
    finally:
        # Cleanup
        for clip in audio_clips + composited_clips[1:]: # Don't close background_clip twice
             if clip: clip.close()
        if 'final_audio' in locals() and final_audio: final_audio.close()
        if 'background_clip' in locals() and background_clip: background_clip.close()
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
