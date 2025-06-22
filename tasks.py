import os
import requests
import re
import cloudinary
import cloudinary.uploader
from moviepy.editor import *

# --- Configuration ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {
    "peter": "N2lVSenPjV6F_h5T2u2K", # Pre-made "Adam" voice
    "brian": "yoZ06aMzmToWyo4y4TfN", # Pre-made "Dorothy" voice
}
BACKGROUND_VIDEO_PATH = "static/background_minecraft.mp4"
CHARACTER_IMAGE_PATHS = {
    "peter": "static/peter.png",
    "brian": "static/brian.png",
}

# Configure Cloudinary using environment variables
cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

def generate_audio_elevenlabs(text: str, voice_id: str, filename: str):
    # (This helper function is the same as before)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(filename, "wb") as f:
            f.write(response.content)
        return True
    return False

def create_video_task(script: str):
    """The main task function that the worker will execute."""
    # (The video generation logic is the same as before, with a few key changes at the end)
    lines = [line.strip() for line in script.split('\n') if line.strip()]
    dialogue_clips = []
    temp_files = []

    try:
        # 1. Generate audio
        for i, line in enumerate(lines):
            match = re.match(r'\[(\w+)\]:\s*(.*)', line, re.IGNORECASE)
            if not match: continue
            character, text = match.groups()
            character = character.lower()
            if character not in VOICE_IDS: continue

            audio_filename = f"temp_audio_{i}.mp3"
            temp_files.append(audio_filename)
            if not generate_audio_elevenlabs(text, VOICE_IDS[character], audio_filename):
                raise Exception(f"Failed to generate audio for line: {line}")
            
            audio_clip = AudioFileClip(audio_filename)
            dialogue_clips.append({"character": character, "text": text, "audio": audio_clip})
        
        if not dialogue_clips:
            raise Exception("No valid dialogue lines found.")

        # 2. Stitch and compose video
        final_audio = concatenate_audioclips([d["audio"] for d in dialogue_clips])
        background_clip = VideoFileClip(BACKGROUND_VIDEO_PATH).subclip(0, final_audio.duration).set_audio(final_audio)
        
        video_clips_to_compose = [background_clip]
        current_time = 0
        for clip_data in dialogue_clips:
            img_clip = ImageClip(CHARACTER_IMAGE_PATHS[clip_data["character"]]).set_duration(clip_data["audio"].duration).set_start(current_time).set_position(("center", "center")).resize(height=300)
            txt_clip = TextClip(clip_data["text"], fontsize=40, color='white', font='Arial-Bold', stroke_color='black', stroke_width=2, size=(background_clip.w * 0.8, None), method='caption').set_duration(clip_data["audio"].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            video_clips_to_compose.extend([img_clip, txt_clip])
            current_time += clip_data["audio"].duration

        final_video = CompositeVideoClip(video_clips_to_compose)
        output_filename = "final_video_temp.mp4"
        temp_files.append(output_filename)
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger=None)

        # 3. Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        
        # 4. Return the secure URL of the uploaded video
        return {"video_url": upload_result['secure_url']}

    finally:
        # 5. Clean up all temporary files
        for clip_data in dialogue_clips:
            clip_data["audio"].close()
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)