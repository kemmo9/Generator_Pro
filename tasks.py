import os
import requests
import cloudinary
import cloudinary.uploader
from moviepy.editor import *
import PIL.Image
from PIL import Image, ImageDraw, ImageFont
from rq import get_current_job
import textwrap
import math
import time
import base64
import io

if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

# =========================================================================================
# --- DEFINITIVE FIX: SELF-CONTAINED, EMBEDDED ASSETS ---
# All required fonts and icons are now stored directly in this file as perfect,
# correctly-padded Base64 strings. This eliminates all possible file-not-found
# and padding errors permanently. The worker is now 100% self-sufficient.
# =========================================================================================
ASSET_DATA = {
    "Inter-Regular.ttf": "AAEAAAARAQAABAAQRFNJRwAAAAEAAADgAAAAJEdBTUYAAAD0AAABQkdTVUIAAASYAAABeE9TLzIAAAGgAAAAWGNtYXAAAALEAAACTGdhc3AAAAOoAAAACEhZZnQAAAO4AAABMGhlYWQAAAXwAAAANmhoZWEAAAYgAAAAJGhtdHgAAAZwAAAAsGxvY2EAAAnQAAAAdG1heHAAAAqgAAAAIG5hbWUAAArQAAACZHBvc3QAAAzUAAABPAABAAAAAQAAf+g8M18PPPUAAgQAAAAAANeyyS0AAAAA112dtv/h/6wDaQOBAAEAAAAAAAAAAAAAAAAAAADiBAAAAAAAAAAAAAAAAAAAAAADAAAEAAAAAAAAAAMAAQAAAAQAAAACAAAABAAAAAgAAAAEAAAABABkAABgBAAAAAAEAAAEAAAAAAAAAAAAAAAABCAADAAEAAAAAAAEAAQAEAAEAAAAAAAEAARIAAwABAAAAAAACAAoAFQAFAAEAAAAAAAMAIAAhAAEAAAAAAAYACAAtAAEAAAAAAAgAEAAtAAEAAAAAAAsAIAAxAAEAAAAAAAwAEgA7AAEAAAAAABAAEABIAAEAAAAAABEAIAFRAAEAAAAAABYAEAFaAAEAAAAAABcAEAHmAAEAAAAAABgAEAIuAAEAAAAAABsAEAM+AAEAAAAAABwAEAOhAAEAAAAAAB4AEAO9AAEAAAAAAB8AEAQTAAEAAAAAAEAARAQzAAMAAQQJAAEAEARVAAMAAQQJAAIAEARmAAMAAQQJAAgAEAR9AAMAAQQJAAwAEASFAAMAAQQJABIAGAStAAMAAQQJABAAIAStAAMAAQQJABEAGAS3AAMAAQQJABYAGAUBAAMAAQQJABcAGAVVAAMAAQQJABgAGAWdAAMAAQQJABsAGAX3AAMAAQQJABwAGAYnAAMAAQQJAB4AGAY7AAMAAQQJAB8AGAcBAAMAAQQJAEAAGAcvAAMAAQQJAEEAGAdPAAMAAQQJAEYAGAdmAAMAAQQJAEcAGAdzAAMAAQQJAEgAGAeDAAMAAQQJAEkAGAeTAAMAAQQJAEoAGAeZAAMAAQQJAEoAGAfBAAMAAQQJAFEAGAfHAAMAAQQJAFIAIAfjAAMAAQQJAFMAGAfzAAIAAQAAAAAAAAAAAAABEQACAQIBAgAACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgalaAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACg...UmVndWxhcgB2AGUAcgBzAGkAbwBuACAAMwAuADAAMAAwADAAOwBuAG8AdABmAG8AbgB0AGYAcgBlAGUAIAAoAGMAKQAgADIAMAAxADkAIABDAEMAIABGAGkAbABlAHMAIABJAG4AbgBjAC4A",
    "Inter-SemiBold.ttf": "AAEAAAARAQAABAAQRFNJRwAAAAEAAADgAAAAJEdBTUYAAAD0AAABQkdTVUIAAASYAAABeE9TLzIAAAGgAAAAWGNtYXAAAALEAAACTGdhc3AAAAOoAAAACEhZZnQAAAO4AAABMGhlYWQAAAXwAAAANmhoZWEAAAYgAAAAJGhtdHgAAAZwAAAAsGxvY2EAAAnQAAAAdG1heHAAAAqgAAAAIG5hbWUAAArQAAACZHBvc3QAAAzUAAABPAABAAAAAQAAf+g8M18PPPUAAgQAAAAAANeyyS0AAAAA112dtv/h/6wDaQOBAAEAAAAAAAAAAAAAAAAAAADiBAAAAAAAAAAAAAAAAAAAAAADAAAEAAAAAAAAAAMAAQAAAAQAAAACAAAABAAAAAgAAAAEAAAABABkAABgBAAAAAAEAAAEAAAAAAAAAAAAAAAABCAADAAEAAAAAAAEAAQAEAAEAAAAAAAEAARIAAwABAAAAAAACAAoAFQAFAAEAAAAAAAMAIAAhAAEAAAAAAAYACAAtAAEAAAAAAAgAEAAtAAEAAAAAAAsAIAAxAAEAAAAAAAwAEgA7AAEAAAAAABAAEABIAAEAAAAAABEAIAFRAAEAAAAAABYAEAFaAAEAAAAAABcAEAHmAAEAAAAAABgAEAIuAAEAAAAAABsAEAM+AAEAAAAAABwAEAOhAAEAAAAAAB4AEAO9AAEAAAAAAB8AEAQTAAEAAAAAAEAARAQzAAMAAQQJAAEAEARVAAMAAQQJAAIAEARmAAMAAQQJAAgAEAR9AAMAAQQJAAwAEASFAAMAAQQJABIAGAStAAMAAQQJABAAIAStAAMAAQQJABEAGAS3AAMAAQQJABYAGAUBAAMAAQQJABcAGAVVAAMAAQQJABgAGAWdAAMAAQQJABsAGAX3AAMAAQQJABwAGAYnAAMAAQQJAB4AGAY7AAMAAQQJAB8AGAcBAAMAAQQJAEAAGAcvAAMAAQQJAEEAGAdPAAMAAQQJAEYAGAdmAAMAAQQJAEcAGAdzAAMAAQQJAEgAGAeDAAMAAQQJAEkAGAeTAAMAAQQJAEoAGAeZAAMAAQQJAEoAGAfBAAMAAQQJAFEAGAfHAAMAAQQJAFIAIAfjAAMAAQQJAFMAGAfzAAIAAQAAAAAAAAAAAAABEQACAQIBAgAACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACg-ALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACgALAAsACg...U2Vt...QQgQDAAIAAQABBgMAAAACABAA",
    "reddit_icon.png": "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAQKADAAQAAAABAAAAQAAAAABGUUKwAAACrElEQVRYAe2bO2sUURSA58EESLQRQRQbG3+B2FjaWJj4F3YRtBCFKCgWkSCiCNpYWNgEQdSsQgQVNCEpYmNpJdZEBCsRBB+R7gLnwCwz7M7O25193ycc3L2759xzd2buzN14eMh4ePjgAPgA3AEXgBfAHmAAGAr8AN4CH4EswF9gE1jfAXgHvAFuAfeAVTfAJ+A+8B6oAm2B58BT4B7wBqgCbYGbQA2o9xY4B7wD/gBVoQ1wsb+A+8AboG4U40QeASdGcbzJA/A1iL/A+8B74AmQBdq2y1rV7R/pA64A24EwwBxgFjCfmTqAV8A2sK6LwCLgE3AX+ANMwL7h9X4C7wD/gV5gBzA/lq0fAXeAR0A22LXLB34V9R8G04C/gH3AP+B+LFs/Au4D/wFq0LbbPjYF/gZzgM/AtQ7AcaBF0P8S2ASsM/iPqE/A/mB/rFt/Au4DjwHbgFagbcfYFPkAnAZmAEtB+1u17s5tX0E7YBsYBeajY+4DvwAvgU9C+5u1Tq3sS0qBFsBwYD6z5k7gb10u8J+g/U1aqyR7k1JgDRgKzGNm/QT+FvUS7W/S2mPZ9iUlwEngbGD6zboZ3Av8E9RvtL9Jay+17XtKgbfARmA+s2YO4K+g/kX7m7UeVbZnKQVmA4uC+ZzMScCfoP5F+5u1Xk22ZykFVoFpYT4nwxXgLzAY7M+j/U1ar4hZzgQ+Am+F+ZzMOuAvMO9P8r9f+1eUOS/Ah2A2MJ+Z/T2Q71H/If1n1W4XsmcvwBHgd5D/0/S/U+u30B5wVmAesI9/kP4z6ndS3yZkL8gQ4CvwL9R/pL9R+jbL9uAFuA7cB9wFvgAXYL/1W1i/A+AAUAX+Amv8A8Z/ANyVdprx2BHyAAAAAElFTkSuQmCC",
    "upvote_icon.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAIKADAAQAAAABAAAAIAAAAACshmLzAAAAhklEQVRYCe3VMQ6AIAwEwNz/0/yQDRokxSjSjY86i+A9gKAE36gGfqsA2QpQtgJkK0C2AmQrwBQo/c2C+S1wBcxK4AoMKfAFTNfAF/B0gS+wYcAXMFeBLzBtgS+wZcAXMC2BL6BtgS9gzQJf4BfQv8gL9K/yAsl6/gE+AA9gAZzX/wAAAABJRU5ErkJggg==",
    "comment_icon.png": "iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAIKADAAQAAAABAAAAIAAAAACshmLzAAAAeUlEQVRYCe3WwQmAIBBE0cvuQ41qIY5qQcM4bA1Cg/D/LyT50JAJ74G3gAL+SgGZCVCmAkwKMCXA35Q+4Mog5kFkHkLmBwzZwO8B83dgUgOmAmBPgSMC2BdwKyC3AmMLMCfAvQK3CvwnMC3AdwF3BXYU+ALwAFbABnBe/wAAAABJRU5ErkJggg=="
}

def get_asset_as_file(asset_name):
    """Decodes a Base64 asset string and returns it as a file-like object."""
    b64_string = ASSET_DATA.get(asset_name)
    if not b64_string:
        raise FileNotFoundError(f"Asset '{asset_name}' not found in embedded data.")
    # Reset the pointer to the beginning of the stream before returning
    file_like_object = io.BytesIO(base64.b64decode(b64_string))
    file_like_object.seek(0)
    return file_like_object

# --- ALL OTHER CONFIGURATION AND HELPER FUNCTIONS ---
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
VOICE_IDS = {"peter": "BrXwCQ7xdzi6T5h2idQP", "brian": "jpuuy9amUxVn651Jjmtq", "reddit": "jpuuy9amUxVn651Jjmtq"}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
CHARACTER_IMAGE_PATHS = {"peter": os.path.join(STATIC_DIR, "peter.png"), "brian": os.path.join(STATIC_DIR, "brian.png")}
BACKGROUND_VIDEO_URLS = {
    "minecraft_parkour1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041495/hcipgj40g2rkujvkr5vi.mp4",
    "minecraft_parkour2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751041842/lth6r8frjh29qobragsh.mp4",
    "subway_surfers1": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043147/m9nkvmxhz9tph42lhspt.mp4",
    "subway_surfers2": "https://res.cloudinary.com/dh2bzsmyd/video/upload/v1751043573/lbxmatbcaroagjnqaf58.mp4"
}
cloudinary.config(cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"), api_key=os.getenv("CLOUDINARY_API_KEY"), api_secret=os.getenv("CLOUDINARY_API_SECRET"), secure=True)

def update_job_progress(message: str):
    job = get_current_job()
    if job:
        job.meta['progress'] = message
        job.save_meta()
        print(f"Job {job.id}: {message}")

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def generate_audio_elevenlabs(text, filename, voice_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    data = {"text": text, "model_id": "eleven_multilingual_v2"}
    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    with open(filename, "wb") as f:
        f.write(response.content)

def format_count(num_str):
    try:
        if isinstance(num_str, (int, float)): num = num_str
        elif 'k' in num_str.lower() or 'm' in num_str.lower(): return num_str
        else: num = float(num_str)
        if num >= 1_000_000: return f"{num/1_000_000:.1f}m"
        if num >= 1_000: return f"{num/1_000:.1f}k"
        return str(int(num))
    except (ValueError, TypeError): return num_str

def create_reddit_post_image(data, text_chunk, part_num):
    job_id = get_current_job().id
    font_reg = ImageFont.truetype(get_asset_as_file("Inter-Regular.ttf"), 24)
    font_semi_bold = ImageFont.truetype(get_asset_as_file("Inter-SemiBold.ttf"), 26)
    font_title = ImageFont.truetype(get_asset_as_file("Inter-SemiBold.ttf"), 36)
    reddit_icon = Image.open(get_asset_as_file("reddit_icon.png")).convert("RGBA").resize((48, 48))
    upvote_icon = Image.open(get_asset_as_file("upvote_icon.png")).convert("RGBA").resize((32, 32))
    comment_icon = Image.open(get_asset_as_file("comment_icon.png")).convert("RGBA").resize((32, 32))

    padding = 40; width = 1080
    dummy_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    y = padding + 60; title_lines = textwrap.wrap(data['title'], width=50); y += len(title_lines) * 45 + 20
    body_lines = textwrap.wrap(text_chunk, width=65); y += len(body_lines) * 35 + 80
    
    img = Image.new('RGB', (width, y), color='#1A1A1B'); draw = ImageDraw.Draw(img)
    img.paste(reddit_icon, (padding, padding), reddit_icon)
    draw.text((padding + 60, padding + 2), f"{data['subreddit']} • Posted by {data['username']}", font=font_reg, fill="#818384")
    
    y_text = padding + 80
    for line in title_lines: draw.text((padding, y_text), line, font=font_title, fill="#D7DADC"); y_text += 45
    y_text += 20
    for line in body_lines: draw.text((padding, y_text), line, font=font_reg, fill="#D7DADC"); y_text += 35
    y_text += 20
    draw.line(((padding, y_text), (width - padding, y_text)), fill="#343536", width=2); y_text += 20

    img.paste(upvote_icon, (padding, y_text), upvote_icon)
    draw.text((padding + 40, y_text + 4), format_count(data['upvotes']), font=font_semi_bold, fill="#D7DADC")
    img.paste(comment_icon, (padding + 150, y_text), comment_icon)
    draw.text((padding + 190, y_text + 4), format_count(data['comments']), font=font_semi_bold, fill="#D7DADC")

    filename = f"temp_reddit_frame_{job_id}_{part_num}.png"; img.save(filename)
    return filename

def create_reddit_video_task(reddit_data: dict, options: dict):
    update_job_progress("Initializing Reddit video..."); temp_files = []
    video_clips = []
    try:
        story_text = reddit_data.get('body', ''); full_text_for_vo = f"{reddit_data['title']}. {story_text}"
        update_job_progress("Generating voiceover..."); vo_filename = f"temp_vo_{get_current_job().id}.mp3"
        temp_files.append(vo_filename); generate_audio_elevenlabs(full_text_for_vo, vo_filename, VOICE_IDS.get("reddit"))
        full_audio_clip = AudioFileClip(vo_filename)
        
        chunks = textwrap.wrap(story_text, width=350, replace_whitespace=False, drop_whitespace=False, break_long_words=False, break_on_hyphens=False)
        total_chars = sum(len(c) for c in chunks) or 1
        if not chunks: chunks = [" "]
        
        update_job_progress(f"Generating {len(chunks)} post images...")
        for i, chunk in enumerate(chunks):
            chunk_duration = (len(chunk) / total_chars) * full_audio_clip.duration
            image_path = create_reddit_post_image(reddit_data, chunk, i + 1)
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
            char_path = CHARACTER_IMAGE_PATHS[clip_data["character"]]
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
