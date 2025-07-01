import os
import requests
from PIL import Image, ImageDraw, ImageFont

# --- SETUP ---
# Defines the directory where all assets will be saved.
STATIC_DIR = "static"
print(f"Ensuring '{STATIC_DIR}' directory exists...")
os.makedirs(STATIC_DIR, exist_ok=True)

# --- 1. FONT DOWNLOADER ---
def download_fonts():
    """Downloads the required Inter font files from Google Fonts CDN."""
    print("\n--- Downloading Fonts ---")
    fonts_to_download = {
        "Inter-Regular.ttf": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuOKfAZ9hjg.ttf",
        "Inter-SemiBold.ttf": "https://fonts.gstatic.com/s/inter/v13/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuOKfAZ9hGg.ttf"
    }
    for filename, url in fonts_to_download.items():
        file_path = os.path.join(STATIC_DIR, filename)
        if os.path.exists(file_path):
            print(f"'{filename}' already exists. Skipping.")
            continue
        try:
            print(f"Downloading '{filename}'...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"SUCCESS: Saved '{filename}' to '{STATIC_DIR}'.")
        except requests.RequestException as e:
            print(f"ERROR: Could not download {filename}. Please check your internet connection. Error: {e}")

# --- 2. ICON CREATION ---
def create_icons():
    """Programmatically creates all the necessary icon files using Pillow."""
    print("\n--- Creating Icons ---")

    # Reddit Icon
    try:
        path = os.path.join(STATIC_DIR, "reddit_icon.png")
        img = Image.new('RGBA', (64, 64), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0,0), (63,63)], fill='#FF4500') # Orange circle
        draw.ellipse([(22, 10), (42, 30)], fill='white') # Head
        draw.ellipse([(12, 28), (22, 38)], fill='white') # Left Ear
        draw.ellipse([(42, 28), (52, 38)], fill='white') # Right Ear
        draw.line([(40,10),(48,2)], fill='white', width=4)
        draw.ellipse([(46,0),(52,6)], fill='white')
        draw.ellipse([(26, 18), (30, 24)], fill='black') # Left Eye
        draw.ellipse([(34, 18), (38, 24)], fill='black') # Right Eye
        img.save(path)
        print(f"SUCCESS: Created '{os.path.basename(path)}'.")
    except Exception as e:
        print(f"ERROR creating Reddit icon: {e}")

    # Upvote Icon
    try:
        path = os.path.join(STATIC_DIR, "upvote_icon.png")
        img = Image.new('RGBA', (32, 32), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(16, 4), (4, 18), (12, 18), (12, 28), (20, 28), (20, 18), (28, 18)], fill='#818384') # Grey color
        img.save(path)
        print(f"SUCCESS: Created '{os.path.basename(path)}'.")
    except Exception as e:
        print(f"ERROR creating Upvote icon: {e}")

    # Comment Icon
    try:
        path = os.path.join(STATIC_DIR, "comment_icon.png")
        img = Image.new('RGBA', (32, 32), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((2, 4, 30, 24), radius=6, fill='#818384')
        draw.polygon([(8, 24), (16, 30), (16, 24)], fill='#818384')
        img.save(path)
        print(f"SUCCESS: Created '{os.path.basename(path)}'.")
    except Exception as e:
        print(f"ERROR creating Comment icon: {e}")
        
    # Favicon
    try:
        path = os.path.join(STATIC_DIR, "favicon.ico")
        img = Image.new('RGBA', (32, 32), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0,0),(31,31)], fill='#bb86fc') # Purple circle
        draw.polygon([(18,4), (10,18), (16,16), (14,28), (22,14), (16,16)], fill='white') # Bolt
        img.save(path, sizes=[(16,16), (32,32)])
        print(f"SUCCESS: Created '{os.path.basename(path)}'.")
    except Exception as e:
        print(f"ERROR creating Favicon: {e}")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    download_fonts()
    create_icons()
    print("\nAsset creation complete. Please run 'git add .' and commit the new files.")
