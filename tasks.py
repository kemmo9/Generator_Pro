import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
from rq import get_current_job
import base64
import uuid
import time
import textwrap

# This hotfix is still necessary for compatibility
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURATION (Complete and Final) ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
}
# THE FIX for ImageMagick Error: We will no longer use stroke_color, which requires ImageMagick.
# We will create a shadow effect manually instead.
SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold"},
    "yellow": {"fontsize": 45, "color": "#FFD700", "font": "Arial-Bold"},
    "meme": {"fontsize": 50, "color": "white", "font": "Impact", "kerning": 1},
}
PREMIUM_STYLES = {} # None for now
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)
CHARACTER_IMAGE_PATHS = {
    "peter": os.path.join(os.path.dirname(__file__), "static", "peter.png"),
    "brian": os.path.join(os.path.dirname(__file__), "static", "brian.png")
}

# --- HELPER FUNCTIONS ---
def update_job_progress(message: str):
    job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r: r.raise_for_status(); open(local_filename, 'wb').write(r.content)
def generate_audio_elevenlabs(text, filename, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}; data = {"text": text, "model_id": "eleven_multilingual_v2"}; r = requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)

# --- THE DEFINITIVE REDDIT VIDEO TASK (html2canvas method) ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video..."); temp_files = []
    try:
        image_data_url = reddit_data.get('image_data_url')
        if not image_data_url: raise ValueError("No image data received from frontend.")
        
        header, encoded = image_data_url.split(",", 1)
        image_data = base64.b64decode(encoded)
        image_path = f"temp_reddit_{get_current_job().id}.png"; temp_files.append(image_path)
        with open(image_path, "wb") as f: f.write(image_data)
        
        title_text = reddit_data.get('title', ''); body_text = reddit_data.get('body', '')
        update_job_progress("Generating voiceover..."); vo_filename = f"temp_vo_{get_current_job().id}.mp3"; temp_files.append(vo_filename)
        generate_audio_elevenlabs(f"{title_text}. {body_text}", vo_filename, VOICE_IDS.get("reddit"))
        audio_clip = AudioFileClip(vo_filename)
        
        title_duration = (len(title_text) / len(f"{title_text}. {body_text}" or 1)) * audio_clip.duration if body_text else audio_clip.duration

        update_job_progress("Compositing video...")
        post_clip = ImageClip(image_path).set_duration(title_duration).resize(width=1000).set_position(('center', 'top')).margin(top=50, opacity=0)
        
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(bg_path)
        background_clip = VideoFileClip(bg_path).set_duration(audio_clip.duration)
        
        subtitles_clip = None
        if body_text:
            style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
            shadow = TextClip(body_text, **style, color='black', size=(background_clip.w * 0.9, None), method='caption').set_position(('center', 'center')).set_start(title_duration).set_duration(audio_clip.duration - title_duration)
            main = TextClip(body_text, **style, size=(background_clip.w * 0.9, None), method='caption').set_position(('center', 'center')).set_start(title_duration).set_duration(audio_clip.duration - title_duration)
            subtitles_clip = CompositeVideoClip([shadow.set_position(lambda t: ('center', 3)), main])

        final_clips = [background_clip, post_clip]
        if subtitles_clip: final_clips.append(subtitles_clip)
        final_video = CompositeVideoClip(final_clips).set_audio(audio_clip)
        
        output_filename = f"final_reddit_{get_current_job().id}.mp4"; temp_files.append(output_filename)
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None

# --- THE DEFINITIVE CHARACTER DIALOGUE TASK ---
def create_video_task(dialogue_data: list, options: dict):
    update_job_progress("Initializing character dialogue video..."); temp_files = []
    try:
        audio_clips = []; update_job_progress("Generating audio clips...")
        for i, line in enumerate(dialogue_data):
            audio_filename = f"temp_audio_{get_current_job().id}_{i}.mp3"; temp_files.append(audio_filename)
            generate_audio_elevenlabs(line['text'], audio_filename, VOICE_IDS.get(line['character']))
            audio_clips.append(AudioFileClip(audio_filename))

        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        temp_bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(temp_bg_path)
        background_clip = VideoFileClip(temp_bg_path).set_duration(final_audio.duration).set_audio(final_audio)

        video_clips = [background_clip]; current_time = 0
        update_job_progress("Compositing video...")
        style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
        for i, clip_data in enumerate(dialogue_data):
            char_path = CHARACTER_IMAGE_PATHS[clip_data["character"]]
            img = ImageClip(char_path).set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", "center")).resize(height=300)
            
            # THE FIX: Create shadow and main text separately to avoid ImageMagick
            shadow_txt = TextClip(clip_data["text"], **style, color='black', size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(lambda t: ('center', 0.8*background_clip.h + 2))
            main_txt = TextClip(clip_data["text"], **style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(lambda t: ('center', 0.8*background_clip.h))
            
            video_clips.extend([img, shadow_txt, main_txt])
            current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip(video_clips)
        output_filename = f"final_char_{get_current_job().id}.mp4"; temp_files.append(output_filename)
        update_job_progress("Rendering final video...")
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None
