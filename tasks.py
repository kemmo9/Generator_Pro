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
import shutil
import whisper

# --- Configuration & Asset URLs ---
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

ASSET_URLS = {
    "reddit_template": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751499682/blank_reddit_template_ohysli.png",
    "verified_checkmark": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751499826/verified_checkmark_n2lrib.png",
    "default_pfp": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488423/default_pfp_v08wql.png",
    "error_preview": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488741/error_preview_zlo1k8.png",
    "peter_char": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488831/peter_ogyitq.png",
    "brian_char": "https://res.cloudinary.com/dh2bzsmyd/image/upload/v1751488826/brian_xqi9u3.png",
    "font_semibold": "https://res.cloudinary.com/dh2bzsmyd/raw/upload/v1751488908/Inter-SemiBold_vjehlv.ttf",
    "font_bold": "https://res.cloudinary.com/dh2bzsmyd/raw/upload/v1751489151/Inter-Bold_wbssww.ttf",
}

SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "font": "Arial-Bold", "color": "white", "stroke_color": "black", "stroke_width": 2.5},
}
PREMIUM_STYLES = {} # Can be expanded later

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit_default": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}

# --- Helper Functions ---
def update_job_progress(message: str): job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None
def download_file_to_temp(url, temp_dir):
    filename = os.path.join(temp_dir, os.path.basename(url.split("?")[0]))
    with requests.get(url, stream=True) as r: r.raise_for_status(); open(filename, 'wb').write(r.content)
    return filename
def generate_audio_elevenlabs(text, filename, voice_id):
    url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers={"xi-api-key": ELEVENLABS_API_KEY}; data={"text": text}; r=requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)
def get_word_timestamps(audio_path):
    update_job_progress("Transcribing for timestamps..."); model = whisper.load_model("tiny.en"); result = model.transcribe(audio_path, word_timestamps=True); return result.get("segments", [])

def create_reddit_post_image(data: dict, temp_dir: str):
    template_path = download_file_to_temp(ASSET_URLS["reddit_template"], temp_dir)
    font_user_path = download_file_to_temp(ASSET_URLS["font_semibold"], temp_dir)
    font_title_path = download_file_to_temp(ASSET_URLS["font_bold"], temp_dir)
    font_stats_path = download_file_to_temp(ASSET_URLS["font_semibold"], temp_dir)
    pfp_path = download_file_to_temp(ASSET_URLS["default_pfp"], temp_dir)
    if data.get("pfp_url") and "http" in data["pfp_url"]:
        try: pfp_path = download_file_to_temp(data["pfp_url"], temp_dir)
        except Exception as e: print(f"Could not download user PFP: {e}")
    template = PILImage.open(template_path).convert("RGBA"); pfp = PILImage.open(pfp_path).convert("RGBA").resize((68, 68)); mask = PILImage.new('L', pfp.size, 0); draw_mask = ImageDraw.Draw(mask); draw_mask.ellipse((0, 0) + pfp.size, fill=255); template.paste(pfp, (45, 42), mask)
    draw = ImageDraw.Draw(template); font_user = ImageFont.truetype(font_user_path, 26); font_title = ImageFont.truetype(font_title_path, 44); font_stats = ImageFont.truetype(font_stats_path, 28)
    draw.text((125, 48), data.get('username', 'u/Anonymous'), font=font_user, fill="#c7c9ca"); draw.text((125, 78), data.get('subreddit', 'r/stories'), font=font_user, fill="#7f8284")
    if data.get("is_verified"):
        checkmark_path = download_file_to_temp(ASSET_URLS["verified_checkmark"], temp_dir)
        checkmark = PILImage.open(checkmark_path).convert("RGBA").resize((32, 32)); username_bbox = draw.textbbox((125, 48), data.get('username', 'u/Anonymous'), font=font_user); template.paste(checkmark, (username_bbox[2] + 8, 46), checkmark)
    y_pos = 145
    for line in textwrap.wrap(data.get('title', 'Your Awesome Title Goes Here'), width=40): draw.text((60, y_pos), line, font=font_title, fill="#000000"); y_pos += 55
    draw.text((160, 485), data.get('upvotes', '99') + "k", font=font_stats, fill="#c7c9ca", anchor="ls"); draw.text((320, 485), data.get('comments', '99') + "+", font=font_stats, fill="#c7c9ca", anchor="ls")
    output_filename = os.path.join(temp_dir, f"reddit_post_{int(time.time())}.png"); template.save(output_filename, "PNG"); return output_filename

def create_reddit_preview_image(data: dict):
    temp_dir = tempfile.mkdtemp()
    try: return create_reddit_post_image(data, temp_dir)
    except Exception as e:
        print(f"Error in preview generation: {e}"); return download_file_to_temp(ASSET_URLS["error_preview"], temp_dir)
    finally: shutil.rmtree(temp_dir)

# --- MAIN TASK FUNCTIONS ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    job_id, temp_dir = get_current_job().id, tempfile.mkdtemp()
    try:
        update_job_progress("Generating assets..."); narrator_voice = options.get("narrator_voice", "reddit_default"); title_text, body_text = reddit_data.get('title', ''), reddit_data.get('body', ''); full_text = f"{title_text}. {body_text}" if body_text.strip() else title_text
        audio_path = os.path.join(temp_dir, f"full_audio_{job_id}.mp3"); generate_audio_elevenlabs(full_text, audio_path, VOICE_IDS[narrator_voice])
        segments = get_word_timestamps(audio_path)
        title_word_count = len(title_text.split()); title_duration = 0
        if segments and segments[0]['words'] and title_word_count > 0: title_duration = segments[0]['words'][min(title_word_count - 1, len(segments[0]['words']) - 1)]['end']
        audio_clip = AudioFileClip(audio_path); bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1")); bg_path = download_file_to_temp(bg_url, temp_dir)
        background_video = VideoFileClip(bg_path).subclip(0, audio_clip.duration).set_audio(audio_clip); update_job_progress("Generating dynamic subtitles...")
        post_image_path = create_reddit_post_image(reddit_data, temp_dir); post_clip = ImageClip(post_image_path).set_duration(title_duration).resize(width=1000).set_position('center')
        
        subtitle_clips = []
        word_group_size = options.get("word_group_size", 3); size_multiplier = options.get("subtitle_size_multiplier", 1.0)
        # --- THE FIX: Create a safe copy of the style dictionary for this job ---
        style = SUBTITLE_STYLES.get("standard", {}).copy()
        style['fontsize'] = int(style.get('fontsize', 40) * size_multiplier)
        
        all_words = [word for seg in segments for word in seg['words']]; body_words = all_words[title_word_count:]
        for i in range(0, len(body_words), word_group_size):
            chunk = body_words[i:i+word_group_size]; text = " ".join([word_info['word'] for word_info in chunk])
            start_time = chunk[0]['start'] - title_duration; end_time = chunk[-1]['end'] - title_duration
            txt_clip = TextClip(text, **style, size=(background_video.w * 0.85, None), method='caption').set_position(('center', 'center')).set_start(start_time).set_duration(end_time - start_time)
            subtitle_clips.append(txt_clip)

        update_job_progress("Compositing final video..."); body_start_time = title_duration if title_duration > 0 else 0
        final_video = CompositeVideoClip([background_video.set_start(0), post_clip.set_start(0)] + [sc.set_start(body_start_time) for sc in subtitle_clips])
        output_path = os.path.join(temp_dir, f"final_reddit_{job_id}.mp4")
        update_job_progress("Rendering video..."); final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24, threads=2)
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally: shutil.rmtree(temp_dir)

def create_video_task(dialogue_data: list, options: dict):
    job_id, temp_dir = get_current_job().id, tempfile.mkdtemp()
    audio_clips, video_clips = [], []
    try:
        update_job_progress("Downloading assets..."); char_paths = {"peter": download_file_to_temp(ASSET_URLS["peter_char"], temp_dir), "brian": download_file_to_temp(ASSET_URLS["brian_char"], temp_dir)}
        # --- THE FIX: Create a safe copy of the style dictionary for this job ---
        style = SUBTITLE_STYLES.get("standard", {}).copy()
        size_multiplier = options.get("subtitle_size_multiplier", 1.0)
        style['fontsize'] = int(style.get('fontsize', 40) * size_multiplier)
        
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        
        update_job_progress("Generating audio...")
        for i, line in enumerate(dialogue_data):
            filename = os.path.join(temp_dir, f"audio_{job_id}_{i}.mp3")
            generate_audio_elevenlabs(line['text'], filename, VOICE_IDS[line['character']]); audio_clips.append(AudioFileClip(filename))
        final_audio = concatenate_audioclips(audio_clips).audio_normalize()
        
        bg_path = download_file_to_temp(bg_url, temp_dir); background_clip = VideoFileClip(bg_path).subclip(0, final_audio.duration).set_audio(final_audio)
        
        update_job_progress("Compositing video...")
        composited_clips = [background_clip]; current_time = 0
        for i, line_data in enumerate(dialogue_data):
            img_clip = ImageClip(char_paths[line_data["character"]]).set_duration(audio_clips[i].duration).set_start(current_time).resize(height=600).set_position(line_data.get("imagePlacement", "center"))
            txt_clip = TextClip(line_data["text"], **style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            video_clips.extend([img_clip, txt_clip]); composited_clips.extend([img_clip, txt_clip])
            current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip(composited_clips, size=background_clip.size)
        output_path = os.path.join(temp_dir, f"final_char_{job_id}.mp4")
        
        update_job_progress("Rendering video..."); final_video.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_path, resource_type="video")
        
        return {"video_url": upload_result['secure_url']}
    finally: shutil.rmtree(temp_dir)
