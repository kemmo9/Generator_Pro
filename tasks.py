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
import tempfile

# --- Configuration & Initial Setup ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

ASSET_URLS = {
    "reddit_template": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488346/reddit_post_template_nqq3u9.png",
    "default_pfp": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488423/default_pfp_v08wql.png",
    "error_preview": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488741/error_preview_zlo1k8.png",
    "peter_char": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488831/peter_ogyitq.png",
    "brian_char": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488826/brian_xqi9u3.png",
    "font_semibold": "https://res.cloudinary.com/dh2bzsmyd/raw/upload/v1751488908/Inter-SemiBold_vjehlv.ttf",
    "font_bold": "https://res.cloudinary.com/dh2bzsmyd/raw/upload/v1751489151/Inter-Bold_wbssww.ttf",
}

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

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}

# --- Helper Functions ---
def update_job_progress(message: str):
    job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None

def download_file_to_temp(url, temp_dir):
    filename = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))
    with requests.get(url, stream=True) as r:
        r.raise_for_status(); open(filename, 'wb').write(r.content)
    return filename

def generate_audio_elevenlabs(text, filename, voice_id):
    url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers={"xi-api-key": ELEVENLABS_API_KEY}; data={"text": text}; r=requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)

def create_reddit_post_image(data: dict, temp_dir: str):
    template_path = download_file_to_temp(ASSET_URLS["reddit_template"], temp_dir)
    font_semibold_path = download_file_to_temp(ASSET_URLS["font_semibold"], temp_dir)
    font_bold_path = download_file_to_temp(ASSET_URLS["font_bold"], temp_dir)
    pfp_path = download_file_to_temp(ASSET_URLS["default_pfp"], temp_dir)

    if data.get("pfp_url") and "http" in data["pfp_url"]:
        try: pfp_path = download_file_to_temp(data["pfp_url"], temp_dir)
        except Exception as e: print(f"Could not download user PFP: {e}")
    
    template = PILImage.open(template_path).convert("RGBA")
    pfp = PILImage.open(pfp_path).convert("RGBA").resize((68, 68))
    mask = PILImage.new('L', pfp.size, 0); draw_mask = ImageDraw.Draw(mask); draw_mask.ellipse((0, 0) + pfp.size, fill=255); template.paste(pfp, (45, 42), mask)
    
    draw = ImageDraw.Draw(template)
    font_user = ImageFont.truetype(font_semibold_path, 22)
    font_title = ImageFont.truetype(font_bold_path, 44)
    font_bold = ImageFont.truetype(font_bold_path, 28) # Font for stats

    draw.text((125, 48), data.get('username', 'u/Anonymous'), font=font_user, fill="#c7c9ca")
    draw.text((125, 78), data.get('subreddit', 'r/stories'), font=font_user, fill="#c7c9ca")
    y_pos = 145
    for line in textwrap.wrap(data.get('title', 'Your Awesome Title Goes Here'), width=40):
        draw.text((60, y_pos), line, font=font_title, fill="#000000"); y_pos += 55
            
    # --- THE FIX: Using the correct 'font_bold' variable instead of the non-existent 'user' variable ---
    draw.text((160, 485), data.get('upvotes', '99') + "k", font=font_bold, fill="#c7c9ca", anchor="ls")
    draw.text((320, 485), data.get('comments', '99') + "+", font=font_bold, fill="#c7c9ca", anchor="ls")

    output_filename = os.path.join(temp_dir, f"reddit_post_{int(time.time())}.png")
    template.save(output_filename, "PNG")
    return output_filename

def create_reddit_preview_image(data: dict):
    temp_dir = tempfile.mkdtemp()
    try:
        return create_reddit_post_image(data, temp_dir)
    except Exception as e:
        print(f"Error in preview generation: {e}")
        return download_file_to_temp(ASSET_URLS["error_preview"], temp_dir)

# --- MAIN TASK FUNCTIONS ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    job_id = get_current_job().id
    temp_dir = tempfile.mkdtemp()
    try:
        update_job_progress("Generating assets...")
        full_text = f"{reddit_data.get('title', '')}. {reddit_data.get('body', '')}"
        
        post_image_path = create_reddit_post_image(reddit_data, temp_dir)
        vo_filename = os.path.join(temp_dir, f"temp_vo_{job_id}.mp3")
        generate_audio_elevenlabs(full_text, vo_filename, VOICE_IDS['reddit'])
        
        audio_clip = AudioFileClip(vo_filename)
        post_clip = ImageClip(post_image_path).set_duration(audio_clip.duration).resize(width=1000).set_position('center')
        
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        bg_path = download_file_to_temp(bg_url, temp_dir)
        background_clip = VideoFileClip(bg_path).subclip(0, audio_clip.duration).set_audio(audio_clip)

        update_job_progress("Compositing..."); final_video = CompositeVideoClip([background_clip, post_clip], size=background_clip.size)
        output_path = os.path.join(temp_dir, f"final_reddit_{job_id}.mp4")
        
        update_job_progress("Rendering video..."); final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading to cloud..."); upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        
        update_job_progress("Finished!")
        return {"video_url": upload_result['secure_url']}
    finally:
        if 'final_video' in locals(): final_video.close()
        for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)

def create_video_task(dialogue_data: list, options: dict):
    job_id = get_current_job().id
    temp_dir = tempfile.mkdtemp()
    audio_clips, video_clips = [], []
    try:
        update_job_progress("Downloading assets...")
        char_image_paths = {
            "peter": download_file_to_temp(ASSET_URLS["peter_char"], temp_dir),
            "brian": download_file_to_temp(ASSET_URLS["brian_char"], temp_dir)
        }
        
        selected_style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        
        update_job_progress("Generating audio...")
        for i, line in enumerate(dialogue_data):
            filename = os.path.join(temp_dir, f"temp_audio_{job_id}_{i}.mp3")
            generate_audio_elevenlabs(line['text'], filename, VOICE_IDS[line['character']])
            audio_clips.append(AudioFileClip(filename))
        
        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        
        bg_path = download_file_to_temp(bg_url, temp_dir)
        background_clip = VideoFileClip(bg_path).subclip(0, final_audio.duration).set_audio(final_audio)

        update_job_progress("Compositing video...")
        composited_clips = [background_clip]
        current_time = 0
        for i, line_data in enumerate(dialogue_data):
            img_path = char_image_paths[line_data["character"]]
            img_clip = ImageClip(img_path).set_duration(audio_clips[i].duration).set_start(current_time).resize(height=300).set_position(line_data.get("imagePlacement", "center"))
            txt_clip = TextClip(line_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            video_clips.extend([img_clip, txt_clip])
            composited_clips.extend([img_clip, txt_clip])
            current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip(composited_clips, size=background_clip.size)
        output_path = os.path.join(temp_dir, f"final_char_{job_id}.mp4")
        
        update_job_progress("Rendering video..."); final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        
        update_job_progress("Finished!")
        return {"video_url": upload_result['secure_url']}
    finally:
        if 'final_video' in locals(): final_video.close()
        for clip in audio_clips + video_clips:
            if clip: clip.close()
        if 'final_audio' in locals(): final_audio.close()
        if 'background_clip' in locals(): background_clip.close()
        for f in os.listdir(temp_dir): os.remove(os.path.join(temp_dir, f))
        os.rmdir(temp_dir)
