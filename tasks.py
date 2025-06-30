import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from rq import get_current_job
import time

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

PREMIUM_STYLES = {"glow_purple", "retro_wave", "comic_book", "valorant", "subtle_gradient", "fire", "professional", "horror"}

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

def update_job_progress(message: str):
    job = get_current_job()
    if job:
        job.meta['progress'] = message
        job.save_meta()
        print(f"Job {job.id}: {message}")

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
    return local_filename

def generate_audio_elevenlabs(text, voice_id, filename):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 200: raise Exception(f"ElevenLabs API Error: {response.text}")
    with open(filename, "wb") as f: f.write(response.content)

def create_video_task(dialogue_data: list, options: dict):
    # This is the complete, working logic for character videos
    temp_files = []
    video_clips, audio_clips = [], []
    try:
        update_job_progress("Initializing...")
        subtitle_style_key = options.get("subtitleStyle", "standard")
        selected_style = SUBTITLE_STYLES.get(subtitle_style_key, SUBTITLE_STYLES["standard"])
        background_key = options.get("backgroundVideo", "minecraft_parkour1")
        background_video_url = BACKGROUND_VIDEO_URLS[background_key]
        update_job_progress("Downloading background video...")
        temp_background_path = download_file(background_video_url, "temp_background.mp4")
        temp_files.append(temp_background_path)
        for i, line in enumerate(dialogue_data):
            update_job_progress(f"Generating audio {i+1}/{len(dialogue_data)}...")
            audio_filename = f"temp_audio_{i}.mp3"
            generate_audio_elevenlabs(line['text'], VOICE_IDS[line['character']], audio_filename)
            temp_files.append(audio_filename)
            audio_clips.append(AudioFileClip(audio_filename))
        update_job_progress("Stitching audio...")
        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        background_clip = VideoFileClip(temp_background_path).subclip(0, final_audio.duration).set_audio(final_audio)
        update_job_progress("Compositing video...")
        current_time = 0
        for i, clip_data in enumerate(dialogue_data):
            img = ImageClip(CHARACTER_IMAGE_PATHS[clip_data["character"]]).set_duration(audio_clips[i].duration).set_start(current_time).set_position(clip_data.get("imagePlacement", "center")).resize(height=300)
            txt = TextClip(clip_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            video_clips.extend([img, txt])
            current_time += audio_clips[i].duration
        final_video = CompositeVideoClip([background_clip] + video_clips, size=background_clip.size)
        output_filename = "final_video_temp.mp4"
        temp_files.append(output_filename)
        update_job_progress("Rendering final video...")
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24)
        update_job_progress("Uploading to cloud...")
        upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        update_job_progress("Finished!")
        return {"video_url": upload_result['secure_url']}
    finally:
        for clip in audio_clips + video_clips:
            if clip: clip.close()
        if 'background_clip' in locals() and background_clip: background_clip.close()
        for f in temp_files:
            if os.path.exists(f): os.remove(f)

def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video...")
    print(f"Received Reddit Job: {reddit_data.get('title')}")
    time.sleep(5) # Simulate work
    update_job_progress("Finished Reddit task (placeholder).")
    return {"video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
