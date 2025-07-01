import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from PIL import Image, ImageDraw, ImageFont
from rq import get_current_job
import textwrap
import math

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- COMPLETE SUBTITLE STYLE & PREMIUM DEFINITIONS ---
SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    "yellow": {"fontsize": 45, "color": "#FFD700", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3, "kerning": 1},
    "minimalist": {"fontsize": 36, "color": "#E0E0E0", "font": "Arial"},
    "glow_purple": {"fontsize": 42, "color": "white", "font": "Arial-Bold", "stroke_color": "#bb86fc", "stroke_width": 1.5},
    "valorant": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "#FD4556", "stroke_width": 2},
    "comic_book": {"fontsize": 45, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 5, "kerning": 2},
    "professional": {"fontsize": 36, "color": "#FFFFFF", "font": "Arial", "bg_color": 'rgba(0, 0, 0, 0.6)'},
    "horror": {"fontsize": 55, "color": "#A40606", "font": "Verdana-Bold", "kerning": -2},
    "retro_wave": {"fontsize": 48, "color": "#F72585", "font": "Arial-Bold", "stroke_color": "#7209B7", "stroke_width": 2},
    "fire": {"fontsize": 50, "color": "#FFD700", "font": "Impact", "stroke_color": "#E25822", "stroke_width": 2.5},
    "ice": {"fontsize": 48, "color": "white", "font": "Arial-Bold", "stroke_color": "#00B4D8", "stroke_width": 2.5}
}
PREMIUM_STYLES = {"glow_purple", "valorant", "comic_book", "professional", "horror", "retro_wave", "fire", "ice"}

# --- CONFIGURATION ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq"}
CHARACTER_IMAGE_PATHS = {"peter": "static/peter.png", "brian": "static/brian.png"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

# --- HELPER FUNCTIONS ---
def update_job_progress(message: str):
    job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None; print(f"Job Progress: {message}")

def download_file(url, filename):
    with requests.get(url, stream=True) as r: r.raise_for_status(); open(filename, 'wb').write(r.content)
    return filename

def generate_audio_elevenlabs(text, filename, voice_id="jpuuy9amUxVn651Jjmtq"): # Default Reddit voice
    url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers={"xi-api-key": ELEVENLABS_API_KEY}; data={"text": text}; r=requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)

def format_count(num_str):
    try:
        if isinstance(num_str, (int, float)): num = num_str
        elif 'k' in num_str.lower() or 'm' in num_str.lower(): return num_str
        else: num = float(num_str)
        if num >= 1_000_000: return f"{num/1_000_000:.1f}m"
        if num >= 1_000: return f"{num/1_000:.1f}k"
        return str(int(num))
    except (ValueError, TypeError): return num_str

# --- NEW: Reddit Image Generation Function ---
def create_reddit_post_image(data, text_chunk, part_num, total_parts):
    job_id = get_current_job().id
    # Load fonts and icons (ensure these are in your static folder)
    font_reg = ImageFont.truetype("static/Inter-Regular.ttf", 24)
    font_semi_bold = ImageFont.truetype("static/Inter-SemiBold.ttf", 26)
    font_title = ImageFont.truetype("static/Inter-SemiBold.ttf", 36)
    reddit_icon = Image.open("static/reddit_icon.png").convert("RGBA").resize((48, 48))
    upvote_icon = Image.open("static/upvote_icon.png").convert("RGBA").resize((32, 32))
    comment_icon = Image.open("static/comment_icon.png").convert("RGBA").resize((32, 32))

    # Create canvas
    padding = 40
    width = 1080
    
    # Dynamic height calculation
    y = padding
    draw = ImageDraw.Draw(Image.new('RGB', (1,1))) # Dummy draw to measure text
    y += 60 # Header space
    title_lines = textwrap.wrap(data['title'], width=50)
    y += len(title_lines) * 45 + 20
    body_lines = textwrap.wrap(text_chunk, width=65)
    y += len(body_lines) * 35 + 60 # Footer space
    
    img = Image.new('RGB', (width, y), color='#1A1A1B') # Reddit dark mode
    draw = ImageDraw.Draw(img)
    
    # Header
    img.paste(reddit_icon, (padding, padding), reddit_icon)
    draw.text((padding + 60, padding + 2), f"{data['subreddit']} • Posted by {data['username']}", font=font_reg, fill="#818384")
    
    # Title
    y_text = padding + 80
    for line in title_lines:
        draw.text((padding, y_text), line, font=font_title, fill="#D7DADC")
        y_text += 45
    
    # Body
    y_text += 20
    for line in body_lines:
        draw.text((padding, y_text), line, font=font_reg, fill="#D7DADC")
        y_text += 35
    
    # Footer separator
    y_text += 20
    draw.line(((padding, y_text), (width - padding, y_text)), fill="#343536", width=2)
    y_text += 20

    # Upvotes
    img.paste(upvote_icon, (padding, y_text), upvote_icon)
    draw.text((padding + 40, y_text + 4), format_count(data['upvotes']), font=font_semi_bold, fill="#D7DADC")
    
    # Comments
    img.paste(comment_icon, (padding + 150, y_text), comment_icon)
    draw.text((padding + 190, y_text + 4), format_count(data['comments']), font=font_semi_bold, fill="#D7DADC")

    filename = f"temp_reddit_frame_{job_id}_{part_num}.png"
    img.save(filename)
    return filename

# --- NEW: Reddit Video Task ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video...")
    temp_files = []
    try:
        story_text = reddit_data.get('body', '')
        full_text_for_vo = f"{reddit_data['title']}. {story_text}"
        
        update_job_progress("Generating voiceover...")
        vo_filename = f"temp_vo_{get_current_job().id}.mp3"
        temp_files.append(vo_filename)
        generate_audio_elevenlabs(full_text_for_vo, vo_filename)
        full_audio_clip = AudioFileClip(vo_filename)
        
        # Split text and calculate duration for each chunk
        chunks = textwrap.wrap(story_text, width=350, replace_whitespace=False)
        if not chunks: chunks = [" "] # Handle empty body
        total_chars = sum(len(c) for c in chunks)
        image_clips = []

        update_job_progress(f"Generating {len(chunks)} post images...")
        for i, chunk in enumerate(chunks):
            chunk_duration = (len(chunk) / total_chars) * full_audio_clip.duration
            image_path = create_reddit_post_image(reddit_data, chunk, i + 1, len(chunks))
            temp_files.append(image_path)
            img_clip = ImageClip(image_path).set_duration(chunk_duration)
            image_clips.append(img_clip)

        reddit_story_clip = concatenate_videoclips(image_clips).set_position('center')
        
        update_job_progress("Downloading background...")
        background_key = options.get("backgroundVideo", "minecraft_parkour1")
        bg_url = BACKGROUND_VIDEO_URLS.get(background_key)
        temp_bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4")
        temp_files.append(temp_bg_path)
        background_clip = VideoFileClip(temp_bg_path).subclip(0, full_audio_clip.duration)
        
        update_job_progress("Compositing final video...")
        final_video = CompositeVideoClip([background_clip, reddit_story_clip])
        final_video = final_video.set_audio(full_audio_clip)

        output_filename = f"final_reddit_{get_current_job().id}.mp4"
        temp_files.append(output_filename)
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger='bar')

        update_job_progress("Uploading...")
        upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None

# --- Original Character Dialogue Task ---
def create_video_task(dialogue_data: list, options: dict):
    # This function is correct and does not need to be changed.
    pass
