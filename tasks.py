import os, requests, cloudinary, cloudinary.uploader, textwrap, time
from moviepy.editor import *
import PIL.Image
from PIL import Image, ImageDraw, ImageFont
from rq import get_current_job

if not hasattr(PIL.Image, 'ANTIALIAS'): PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
BASE_DIR = os.path.dirname(os.path.abspath(__file__)); STATIC_DIR = os.path.join(BASE_DIR, "static")

SUBTITLE_STYLES = {"standard": {"fontsize": 40, "color": "white", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2}, "yellow": {"fontsize": 45, "color": "#FFD700", "font": "Arial-Bold", "stroke_color": "black", "stroke_width": 2.5}, "meme": {"fontsize": 50, "color": "white", "font": "Impact", "kerning": 1, "stroke_color": "black", "stroke_width": 3}}
PREMIUM_STYLES = {}
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
CHARACTER_IMAGE_PATHS = {"peter": os.path.join(STATIC_DIR, "peter.png"), "brian": os.path.join(STATIC_DIR, "brian.png")}
BACKGROUND_VIDEO_URLS = {"minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4", "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4", "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4", "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

def update_job_progress(message): job = get_current_job(); job.meta['progress'] = message; job.save_meta() if job else None
def download_file(url, filename): with requests.get(url, stream=True) as r: r.raise_for_status(); open(filename, 'wb').write(r.content); return filename
def generate_audio_elevenlabs(text, filename, voice_id): url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"; headers={"xi-api-key": ELEVENLABS_API_KEY}; data={"text": text}; r=requests.post(url, json=data, headers=headers); r.raise_for_status(); open(filename, "wb").write(r.content)
def create_reddit_post_image(data):
    template = Image.open(os.path.join(STATIC_DIR, "reddit_template_final.png")).convert("RGBA"); draw = ImageDraw.Draw(template)
    font_bold = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-SemiBold.ttf"), 28); font_heavy = ImageFont.truetype(os.path.join(STATIC_DIR, "Inter-SemiBold.ttf"), 44)
    draw.text((120, 48), data.get('subreddit', 'r/stories'), font=font_bold, fill="#000000")
    y_pos = 155
    for line in textwrap.wrap(data.get('title', ''), width=40): draw.text((60, y_pos), line, font=font_heavy, fill="#1a1b1e"); y_pos += 55
    draw.text((150, 485), data.get('upvotes', '99+'), font=font_bold, fill="#636466", anchor="ls"); draw.text((310, 485), data.get('comments', '99+'), font=font_bold, fill="#636466", anchor="ls")
    filename = f"temp_reddit_{get_current_job().id}.png"; template.save(filename); return filename
    
def create_reddit_video_task(data, options):
    update_job_progress("Generating assets..."); text = f"{data.get('title','')}. {data.get('body','')}"
    vo_filename = f"temp_vo_{get_current_job().id}.mp3"; generate_audio_elevenlabs(text, vo_filename, VOICE_IDS['reddit'])
    audio = AudioFileClip(vo_filename)
    img_path = create_reddit_post_image(data)
    post_clip = ImageClip(img_path).set_duration(audio.duration).resize(width=1000).set_position(data.get('position', 'center'))
    bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1")); bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4")
    background = VideoFileClip(bg_path).set_duration(audio.duration).set_audio(audio)
    update_job_progress("Compositing..."); final = CompositeVideoClip([background, post_clip])
    output_path = f"final_reddit_{get_current_job().id}.mp4"; final.write_videofile(output_path)
    update_job_progress("Uploading..."); result = cloudinary.uploader.upload(output_path, resource_type="video")
    for f in [vo_filename, img_path, bg_path, output_path]: os.remove(f)
    return {"video_url": result['secure_url']}
    
def create_video_task(data, options):
    update_job_progress("Generating audio..."); audio_clips, temp_files = [], []
    for i, line in enumerate(data):
        filename = f"temp_audio_{i}.mp3"; temp_files.append(filename); generate_audio_elevenlabs(line['text'], filename, VOICE_IDS[line['character']]); audio_clips.append(AudioFileClip(filename))
    audio = concatenate_audioclips(audio_clips)
    bg_url = BACKGROUND_VIDEO_URLS.get(options.get("backgroundVideo", "minecraft_parkour1")); bg_path = download_file(bg_url, f"temp_bg_{get_current_job().id}.mp4"); temp_files.append(bg_path)
    background = VideoFileClip(bg_path).set_duration(audio.duration).set_audio(audio)
    clips = [background]; current_time = 0; style = SUBTITLE_STYLES.get(options.get("subtitleStyle", "standard"))
    for i, line in enumerate(data):
        img = ImageClip(CHARACTER_IMAGE_PATHS[line["character"]]).set_duration(audio_clips[i].duration).set_start(current_time).resize(height=300).set_position(("center", "center"))
        txt = TextClip(line["text"], **style, size=(background.w * 0.8, None), method='caption').set_duration(audio_clips[i].duration).set_start(current_time).set_position(("center", 0.8), relative=True)
        clips.extend([img, txt]); current_time += audio_clips[i].duration
    final = CompositeVideoClip(clips)
    output_path = f"final_char_{get_current_job().id}.mp4"; final.write_videofile(output_path, codec="libx264", audio_codec="aac")
    update_job_progress("Uploading..."); result = cloudinary.uploader.upload(output_path, resource_type="video")
    for f in temp_files + [output_path]: os.remove(f)
    return {"video_url": result['secure_url']}
