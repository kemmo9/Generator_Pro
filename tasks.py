import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
from rq import get_current_job
import textwrap
import time
from jinja2 import Environment, FileSystemLoader

# This hotfix is still necessary
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# --- CONFIGURATION (No changes needed here) ---
HCTI_API_USER_ID = os.getenv("HCTI_USER_ID")
HCTI_API_KEY = os.getenv("HCTI_API_KEY")
SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    # ... all other subtitle styles
}
PREMIUM_STYLES = {"glow_purple", "valorant", "comic_book", "professional", "horror", "retro_wave", "fire", "ice"}
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    # ... all other background videos
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)
template_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

# --- HELPER FUNCTIONS (No changes needed here) ---
def update_job_progress(message: str):
    job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None; print(f"Job Progress: {message}")
def download_file(url, local_filename):
    with requests.get(url, stream=True) as r: r.raise_for_status(); open(local_filename, 'wb').write(r.content)
    return local_filename
def generate_audio_elevenlabs(text, filename, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_multilingual_v2"}; r=requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)
def format_count(num_str):
    try:
        if isinstance(num_str, (int, float)): num = num_str
        elif 'k' in num_str.lower() or 'm' in num_str.lower(): return num_str
        else: num = float(num_str)
        if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
        if num >= 1_000: return f"{num/1_000:.1f}K"
        return str(int(num))
    except (ValueError, TypeError): return num_str

# --- THE DEFINITIVE FIX for Reddit Image Generation ---
def create_reddit_post_image_via_api(data):
    job_id = get_current_job().id
    template = template_env.get_template('reddit_template.html')
    
    # Using publicly hosted, reliable icon URLs
    icon_url = "https://i.imgur.com/Kq4g5tW.png"
    tick_url = "https://i.imgur.com/3ZJ7kMh.png"
    likes_icon_url = "https://i.imgur.com/eYn0m6a.png"
    comments_icon_url = "https://i.imgur.com/s273I29.png"

    html = template.render(
        subreddit=data['subreddit'], username=data['username'], title=data['title'],
        body="", # Body is rendered as subtitles, not in the image
        upvotes=format_count(data['upvotes']), comments=format_count(data['comments']),
        icon_url=icon_url, tick_url=tick_url, likes_icon_url=likes_icon_url, comments_icon_url=comments_icon_url
    )

    # This new CSS creates the smaller, top-left aligned post
    css = """
    body { margin: 0; font-family: 'Inter', sans-serif; }
    .post-container {
        background-color: #FFFFFF;
        border: 1px solid #dee0e1;
        border-radius: 12px;
        padding: 16px;
        width: 800px; /* Smaller width */
        box-sizing: border-box;
    }
    .header { display: flex; align-items: center; margin-bottom: 12px; }
    .icon { width: 28px; height: 28px; margin-right: 8px; }
    .meta { display: flex; align-items: center; }
    .subreddit { color: #1c1c1c; font-weight: 500; font-size: 14px; }
    .username { color: #787c7e; font-size: 14px; margin-left: 8px; }
    .tick { display: none; } /* Hide the tick for a cleaner look */
    .title { font-size: 24px; font-weight: 600; color: #1a1b1e; line-height: 1.3; margin: 0; }
    .footer { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; color: #787c7e; font-weight: 500; font-size: 14px;}
    .footer-icon { height: 20px; margin-right: 6px; }
    .likes, .comments { display: flex; align-items: center; }
    """

    api_data = {'html': html, 'css': css, 'google_fonts': 'Inter'}
    response = requests.post('https://hcti.io/v1/image', data=api_data, auth=(HCTI_API_USER_ID, HCTI_API_KEY))
    response.raise_for_status()
    image_url = response.json()['url']
    
    image_filename = f"temp_reddit_frame_{job_id}.png"
    download_file(image_url, image_filename)
    return image_filename

# --- Main RQ Task Functions ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing multi-scene Reddit video..."); temp_files = []
    try:
        title_text = reddit_data.get('title', ''); body_text = reddit_data.get('body', '')
        update_job_progress("Generating voiceover for title..."); 
        title_vo_filename = f"temp_vo_title_{get_current_job().id}.mp3"; temp_files.append(title_vo_filename)
        generate_audio_elevenlabs(title_text, title_vo_filename, VOICE_IDS.get("reddit"))
        title_audio_clip = AudioFileClip(title_vo_filename)

        body_audio_clip = None
        if body_text:
            update_job_progress("Generating voiceover for body..."); 
            body_vo_filename = f"temp_vo_body_{get_current_job().id}.mp3"; temp_files.append(body_vo_filename)
            generate_audio_elevenlabs(body_text, body_vo_filename, VOICE_IDS.get("reddit"))
            body_audio_clip = AudioFileClip(body_vo_filename)

        total_duration = title_audio_clip.duration + (body_audio_clip.duration if body_audio_clip else 0)
        update_job_progress("Downloading background video...")
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        temp_bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(temp_bg_path)
        background_clip = VideoFileClip(temp_bg_path).set_duration(total_duration)

        update_job_progress("Generating post image...")
        image_path = create_reddit_post_image_via_api(reddit_data)
        temp_files.append(image_path)
        
        # --- THE FIX: Position the post image at the top-left ---
        scene1_clip = ImageClip(image_path).set_duration(title_audio_clip.duration).set_position(("left", "top")).margin(top=30, left=30, opacity=0)
        
        scene2_clips = []
        if body_audio_clip:
            subtitle_style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"), SUBTITLE_STYLES["standard"])
            subtitles_clip = TextClip(body_text, **subtitle_style, size=(background_clip.w * 0.9, None), method='caption').set_position('center').set_duration(body_audio_clip.duration).set_start(title_audio_clip.duration)
            scene2_clips.append(subtitles_clip)

        update_job_progress("Compositing all scenes...")
        final_audio = concatenate_audioclips([clip for clip in [title_audio_clip, body_audio_clip] if clip])
        final_video = CompositeVideoClip([background_clip, scene1_clip] + scene2_clips).set_audio(final_audio)
        
        output_filename = f"final_reddit_{get_current_job().id}.mp4"; temp_files.append(output_filename)
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger='bar')
        
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None

def create_video_task(dialogue_data: list, options: dict):
    # This is the original, working code for character dialogues.
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

        video_clips = []; current_time = 0; update_job_progress("Compositing video...")
        selected_style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
        for i, clip_data in enumerate(dialogue_data):
            char_path = os.path.join(os.path.dirname(__file__), "static", f"{clip_data['character']}.png")
            img = ImageClip(char_path).set_duration(audio_clips[i].duration).set_start(current_time).set_position(clip_data.get("imagePlacement", "center")).resize(height=300)
            txt = TextClip(clip_data["text"], **selected_style, size=(background_clip.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
            video_clips.extend([img, txt]); current_time += audio_clips[i].duration
        
        final_video = CompositeVideoClip([background_clip] + video_clips, size=background_clip.size)
        output_filename = f"final_char_{get_current_job().id}.mp4"; temp_files.append(output_filename)
        update_job_progress("Rendering final video...")
        final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", fps=24, logger='bar')
        
        update_job_progress("Uploading..."); upload_result = cloudinary.uploader.upload(output_filename, resource_type="video")
        return {"video_url": upload_result['secure_url']}
    finally:
        for f in temp_files: os.remove(f) if os.path.exists(f) else None
