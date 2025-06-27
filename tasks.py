import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image

# Compatibility fix
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- Configuration ---
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = { "peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq" }
CHARACTER_IMAGE_PATHS = { "peter": "static/peter.png", "brian": "static/brian.png" }

# NEW: Using your provided Cloudinary URLs
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

# Helper function to download a file from a URL
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def generate_audio_elevenlabs(text, voice_id, filename):
    # This function is unchanged
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_monolingual_v1", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        with open(filename, "wb") as f: f.write(response.content)
        return True, None
    else:
        error_details = f"ElevenLabs API Error - Status: {response.status_code}, Response: {response.text}"
        print(error_details)
        return False, error_details

def create_video_task(dialogue_data: list, options: dict):
    # This function now uses the new URLs but the logic is the same
    dialogue_clips = []
    temp_files = []

    background_key = options.get("backgroundVideo", "minecraft_parkour1")
    background_video_url = BACKGROUND_VIDEO_URLS.get(background_key, BACKGROUND_VIDEO_URLS["minecraft_parkour1"])
    temp_background_path = "temp_background.mp4"
    temp_files.append(temp_background_path)
    
    subtitle_style = options.get("subtitleStyle", "standard")
    subtitle_styles = {
        "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
        "yellow": {"fontsize": 45, "color": "yellow", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
        "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3}
    }
    selected_style = subtitle_styles.get(subtitle_style, subtitle_styles["standard"])

    try:
        print(f"Downloading background video from {background_video_url}...")
        download_file(background_video_url, temp_background_path)
        print("Download complete.")
        
        for i, line_data in enumerate(dialogue_data):
            character = line_data.get("character")
            text = line_data.get("text")
            image_placement = line_data.get("imagePlacement", "center") 
            if not all([character, text, character in VOICE_IDS]): continue
            audio_filename = f"temp_audio_{i}.mp3"
            temp_files.append(audio_filename)
            success, error_message = generate_audio_elevenlabs(text, VOICE_IDS[character], audio_filename)
            if not success: raise Exception(error_message)
            audio_clip = AudioFileClip(audio_filename).audio_normalize()
            dialogue_clips.append({"character": character, "text": text, "audio": audio_clip, "imagePlacement": image_placement})

        if not dialogue_clips: raise Exception("No valid dialogue to process.")

        final_audio = concatenate_audioclips([d["audio"] for d in dialogue_clips])
        background_clip = VideoFileClip(temp_background_path).subclip(0, final_audio.duration).set_audio(final_audio)
        
        video_clips_to_compose = [background_clip]
        current_time = 0
        for clip_data in dialogue_clips:
            img_clip = (ImageClip(CHARACTER_IMAGE_PATHS[clip_data["character"]])
                        .set_duration(clip_data["audio"].duration)
                        .set_start(current_time)
                        .set_position(clip_data["imagePlacement"])
                        .resize(height=300))
            txt_clip = (TextClip(clip_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption')
                        .set_duration(clip_data["audio"].duration)
                        .set_start(current_time)
                        .set_position(("center", 0.8), relative=True))
            video_clips_to_compose.extend([img_clip, txt_clip])
            current_time += clip_data["audio"].duration

        final_video = CompositeVideoClip(video_clips_to_compose)
        output_filename = "final_video_temp.mp4"
        temp_files.append(output_filename)
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger=None)
        
        upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for clip_data in dialogue_clips:
            if 'audio' in clip_data and clip_data['audio']: clip_data['audio'].close()
        for f in temp_files:
            if os.path.exists(f): os.remove(f)
