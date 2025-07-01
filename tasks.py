import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
from rq import get_current_job
import textwrap
import time

# --- CONFIGURATION ---
HCTI_API_USER_ID = os.getenv("HCTI_USER_ID")
HCTI_API_KEY = os.getenv("HCTI_API_KEY")

SUBTITLE_STYLES = {
    "standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2},
    # ... all your other subtitle styles ...
}
PREMIUM_STYLES = {"glow_purple", "valorant", "comic_book", "professional", "horror", "retro_wave", "fire", "ice"}
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    # ... all your other background videos ...
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

# --- HELPER FUNCTIONS ---
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
        if num >= 1_000_000: return f"{num/1_000_000:.1f}m"
        if num >= 1_000: return f"{num/1_000:.1f}k"
        return str(int(num))
    except (ValueError, TypeError): return num_str

# --- NEW, UNBREAKABLE Reddit Image Generation ---
def create_reddit_post_image_via_api(data, text_chunk, part_num):
    job_id = get_current_job().id
    html_template = f"""
    <div class="post">
        <div class="header">
            <img src="https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-57x57.png" class="icon">
            <span class="subreddit">{data['subreddit']}</span>
            <span class="meta">• Posted by {data['username']}</span>
        </div>
        <h2 class="title">{data['title']}</h2>
        <div class="body">{text_chunk}</div>
        <div class="footer">
            <span class="votes">⬆️ {format_count(data['upvotes'])}</span>
            <span class="comments">💬 {format_count(data['comments'])}</span>
        </div>
    </div>"""

    css_template = """
    body { margin: 0; background-color: #030303; }
    .post { background-color: #1A1A1B; color: #D7DADC; font-family: 'Verdana', sans-serif; padding: 20px; border-radius: 8px; width: 1000px; box-sizing: border-box;}
    .header { display: flex; align-items: center; font-size: 14px; color: #818384; margin-bottom: 15px; }
    .icon { width: 32px; height: 32px; border-radius: 50%; margin-right: 10px; }
    .subreddit { color: #D7DADC; font-weight: bold; }
    .title { font-size: 24px; font-weight: 600; color: #D7DADC; margin-bottom: 15px; }
    .body { font-size: 16px; line-height: 1.6; white-space: pre-wrap; }
    .footer { margin-top: 20px; font-size: 14px; font-weight: bold; }
    .votes, .comments { margin-right: 20px; }"""

    api_data = {'html': html_template, 'css': css_template}
    response = requests.post('https://hcti.io/v1/image', data=api_data, auth=(HCTI_API_USER_ID, HCTI_API_KEY))
    response.raise_for_status()
    image_url = response.json()['url']
    
    # Download the generated image
    image_filename = f"temp_reddit_frame_{job_id}_{part_num}.png"
    download_file(image_url, image_filename)
    return image_filename

# --- Main RQ Task Functions ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video..."); temp_files = []
    video_clips = []
    try:
        story_text = reddit_data.get('body', '')
        full_text_for_vo = f"{reddit_data['title']}. {story_text}"
        
        update_job_progress("Generating voiceover..."); vo_filename = f"temp_vo_{get_current_job().id}.mp3"
        temp_files.append(vo_filename); generate_audio_elevenlabs(full_text_for_vo, vo_filename, VOICE_IDS.get("reddit"))
        full_audio_clip = AudioFileClip(vo_filename)
        
        chunks = textwrap.wrap(story_text, width=350, replace_whitespace=False)
        if not chunks: chunks = [" "]
        total_chars = sum(len(c) for c in chunks) or 1
        
        update_job_progress(f"Generating {len(chunks)} post images via API...")
        for i, chunk in enumerate(chunks):
            chunk_duration = (len(chunk) / total_chars) * full_audio_clip.duration
            image_path = create_reddit_post_image_via_api(reddit_data, chunk, i + 1)
            temp_files.append(image_path)
            img_clip = ImageClip(image_path).set_duration(chunk_duration)
            video_clips.append(img_clip)

        reddit_story_clip = concatenate_videoclips(video_clips, method="compose").set_position('center')
        
        update_job_progress("Downloading background...")
        bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1"))
        temp_bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(temp_bg_path)
        background_clip = VideoFileClip(temp_bg_path).set_duration(full_audio_clip.duration)
        
        update_job_progress("Compositing final video...")
        final_video = CompositeVideoClip([background_clip, reddit_story_clip]).set_audio(full_audio_clip)
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
            # This uses the absolute path method, which is robust
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
