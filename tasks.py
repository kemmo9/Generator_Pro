import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
from rq import get_current_job
import textwrap
import time
from jinja2 import Environment, FileSystemLoader

# --- CONFIGURATION ---
HCTI_API_USER_ID = os.getenv("HCTI_USER_ID")
HCTI_API_KEY = os.getenv("HCTI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

# Set up Jinja2 to find the new HTML template
template_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

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
        if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
        if num >= 1_000: return f"{num/1_000:.1f}K"
        return str(int(num))
    except (ValueError, TypeError): return num_str

# --- NEW, ROBUST Reddit Image Generation via API ---
def create_reddit_post_image_via_api(data, text_chunk, part_num):
    job_id = get_current_job().id
    template = template_env.get_template('reddit_template.html')

    # Data URLs for the icons to embed them directly in the HTML
    # This prevents any file loading issues. You MUST add these icons to your static folder.
    icon_url = "https://i.imgur.com/Kq4g5tW.png" # Generic Reddit-like icon
    tick_url = "https://i.imgur.com/3ZJ7kMh.png" # Blue verified tick
    likes_icon_url = "https://i.imgur.com/eYn0m6a.png" # Heart icon
    comments_icon_url = "https://i.imgur.com/s273I29.png" # Comment bubble icon

    html = template.render(
        subreddit=data['subreddit'],
        username=data['username'],
        title=data['title'],
        body=text_chunk,
        upvotes=format_count(data['upvotes']),
        comments=format_count(data['comments']),
        icon_url=icon_url,
        tick_url=tick_url,
        likes_icon_url=likes_icon_url,
        comments_icon_url=comments_icon_url
    )

    api_data = {'html': html, 'google_fonts': 'Inter'}
    response = requests.post('https://hcti.io/v1/image', data=api_data, auth=(HCTI_API_USER_ID, HCTI_API_KEY))
    response.raise_for_status()
    image_url = response.json()['url']
    
    image_filename = f"temp_reddit_frame_{job_id}_{part_num}.png"
    download_file(image_url, image_filename)
    return image_filename

# --- Main RQ Task Functions ---
def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video..."); temp_files = []
    video_clips = []
    try:
        story_text = reddit_data.get('body', ''); full_text_for_vo = f"{reddit_data['title']}. {story_text}"
        update_job_progress("Generating voiceover..."); vo_filename = f"temp_vo_{get_current_job().id}.mp3"
        temp_files.append(vo_filename); generate_audio_elevenlabs(full_text_for_vo, vo_filename, VOICE_IDS.get("reddit"))
        full_audio_clip = AudioFileClip(vo_filename)
        
        chunks = textwrap.wrap(story_text, width=400, replace_whitespace=False)
        if not chunks: chunks = [" "]
        total_chars = sum(len(c) for c in chunks) or 1
        
        update_job_progress(f"Generating {len(chunks)} post images via API...")
        for i, chunk in enumerate(chunks):
            chunk_duration = (len(chunk) / total_chars) * full_audio_clip.duration
            image_path = create_reddit_post_image_via_api(reddit_data, chunk, i + 1)
            temp_files.append(image_path)
            img_clip = ImageClip(image_path).set_duration(chunk_duration)
            video_clips.append(img_clip)

        reddit_story_clip = concatenate_videoclips(video_clips, method="compose").set_position(('center', 'center'))
        
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
    # This function is for character dialogues and does not need to be changed.
    pass
