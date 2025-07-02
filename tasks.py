import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from PIL import Image, ImageDraw, ImageFont
from rq import get_current_job
import textwrap
import time

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# --- THE FIX: Removing stroke_color to eliminate the ImageMagick dependency ---
SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold"},
    "yellow": {"fontsize": 45, "color": "#FFD700", "font": "Arial-Bold"},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "kerning": 1},
}
PREMIUM_STYLES = {}
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
CHARACTER_IMAGE_PATHS = {"peter": os.path.join(STATIC_DIR, "peter.png"), "brian": os.path.join(STATIC_DIR, "brian.png")}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

# --- All helper functions are correct and do not need to be changed ---
def update_job_progress(message: str):
    job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r: r.raise_for_status(); open(local_filename, 'wb').write(r.content)
    return local_filename
def generate_audio_elevenlabs(text, filename, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}; data = {"text": text, "model_id": "eleven_multilingual_v2"}; r = requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)
def format_count(num_str):
    try:
        if isinstance(num_str, (int, float)): num = num_str
        elif 'k' in num_str.lower() or 'm' in num_str.lower(): return num_str
        else: num = float(num_str)
        if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
        if num >= 1_000: return f"{num/1_000:.1f}K"
        return str(int(num))
    except (ValueError, TypeError): return num_str
def create_reddit_post_image(data):
    job_id = get_current_job().id
    template_path = os.path.join(STATIC_DIR, "reddit_template_final.png")
    font_bold = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-SemiBold.ttf"), 28)
    font_heavy = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-SemiBold.ttf"), 44)
    img = Image.open(template_path).convert("RGBA"); draw = ImageDraw.Draw(img)
    draw.text((120, 48), data.get('subreddit', 'r/stories'), font=font_bold, fill="#000000")
    y_pos = 155
    for line in textwrap.wrap(data.get('title', ''), width=40): draw.text((60, y_pos), line, font=font_heavy, fill="#1a1b1e"); y_pos += 55
    draw.text((150, 485), format_count(data.get('upvotes', '99+')), font=font_bold, fill="#636466", anchor="ls")
    draw.text((310, 485), format_count(data.get('comments', '99+')), font=font_bold, fill="#636466", anchor="ls")
    filename = f"temp_reddit_frame_{job_id}.png"; img.save(filename)
    return filename

# --- Main RQ Task Functions ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    # This function is correct and does not need to be changed.
    pass

def create_video_task(dialogue_data: list, options: dict):
    update_job_progress("Initializing character dialogue video..."); temp_files = []
    try:
        audio_clips = []; update_job_progress("Generating audio clips...")
        for i, line in enumerate(dialogue_data):
            audio_filename = f"temp_audio_{get_current_job().id}_{i}.mp3"; temp_files.append(audio_filename)
            generate_audio_elevenlabs(line['text'], audio_filename, VOICE_IDS.get(line['character']))
            audio_clips.append(AudioFileClip(audio_filename))
        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        update_job_progress("Downloading background...")
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        temp_bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(temp_bg_path)
        background_clip = VideoFileClip(temp_bg_path).set_duration(final_audio.duration).set_audio(final_audio)
        video_clips = [background_clip]; current_time = 0; update_job_progress("Compositing video...")
        style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
        for i, clip_data in enumerate(dialogue_data):
            char_path = CHARACTER_IMAGE_PATHS[clip_data["character"]]
            img = ImageClip(char_path).set_duration(audio_clips[i].duration).set_start(current_time).set_position(clip_data.get("imagePlacement", "center")).resize(height=300)
            
            # --- THE DEFINITIVE FIX for the ImageMagick Error ---
            # Create a shadow by layering two text clips. This is robust and has no dependencies.
            shadow_style = style.copy()
            shadow_style['color'] = 'black'
            shadow_offset = 2 # The thickness of the shadow in pixels
            
            shadow_txt = TextClip(clip_data["text"], **shadow_style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(lambda t: ('center', 0.8*background_clip.h + shadow_offset))
            main_txt = TextClip(clip_data["text"], **style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(('center', 0.8*background_clip.h))
            
            video_clips.extend([shadow_txt, main_txt, img]); current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip(video_clips)
        output_filename = f"final_char_{get_current_job().id}.mp4"; temp_files.append(output_filename)
        update_job_progress("Rendering final video...")
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger='bar')
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None
