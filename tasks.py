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

# NEW: Expanded dictionary for background videos
BACKGROUND_VIDEOS = {
    "minecraft_parkour1": "static/background_minecraft.mp4",
    "minecraft_parkour2": "static/background_minecraft2.mp4",
    "subway_surfers1": "static/background_subway1.mp4",
    "subway_surfers2": "static/background_subway2.mp4"
}

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
  api_key = os.getenv("CLOUDINARY_API_KEY"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET"),
  secure = True
)

# ... (the rest of your tasks.py file remains exactly the same) ...

# The generate_audio_elevenlabs function is unchanged

# The create_video_task function is mostly unchanged, but will now use the new keys
def create_video_task(dialogue_data: list, options: dict):
    dialogue_clips = []
    temp_files = []

    # Get options from the payload
    subtitle_style = options.get("subtitleStyle", "standard")
    background_key = options.get("backgroundVideo", "minecraft_parkour1") # Default to the first one
    
    # Use the selected background video key to get the file path
    background_video_path = BACKGROUND_VIDEOS.get(background_key, BACKGROUND_VIDEOS["minecraft_parkour1"])

    subtitle_styles = {
        "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
        "yellow": {"fontsize": 45, "color": "yellow", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5},
        "meme": {"fontsize": 50, "color": "white", "font": "Impact", "stroke_color": "black", "stroke_width": 3}
    }
    selected_style = subtitle_styles.get(subtitle_style, subtitle_styles["standard"])

    try:
        # ... the rest of the function (audio generation, video composition) is identical to your last version ...
        # This part does not need to change at all.

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
        background_clip = VideoFileClip(background_video_path).subclip(0, final_audio.duration).set_audio(final_audio)
        
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
