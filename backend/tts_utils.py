# import os
# from uuid import uuid4
# from gtts import gTTS
# def generate_tts_file(text: str, lang: str = "en"):
#     """
#     Generates MP3 with gTTS, returns (file_path, public_url).
#     """
#     BASE_URL = "https://ai-health-chatbot-6jaw.onrender.com"
#     filename = f"tts_{uuid4().hex}.mp3"
#     filepath = os.path.join(TTS_DIR, filename)

#     tts = gTTS(text=text, lang=lang, slow=False)
#     tts.save(filepath)

#     if not BASE_URL:
#         public_url = f"/static/tts/{filename}"
#     else:
#         public_url = f"{BASE_URL.rstrip('/')}/static/tts/{filename}"

#     return filepath, public_url

# backend/tts_utils.py
import os
from uuid import uuid4
from gtts import gTTS
from dotenv import load_dotenv

# Load environment variables from the root .env file
#load_dotenv()
#load_dotenv(dotenv_path='backend/.env.example')
load_dotenv(dotenv_path='backend/.env')
# [FIX 1] Define the paths for saving audio files
# This calculates the path relative to the project root
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "static")
TTS_DIR = os.path.join(STATIC_DIR, "tts")
os.makedirs(TTS_DIR, exist_ok=True)

# [FIX 2] Load the BASE_URL from environment variables, don't hardcode it
BASE_URL = os.getenv("BASE_URL")

def generate_tts_file(text: str, lang: str = "en"):
    """Generates an MP3 with gTTS and returns its public URL."""
    
    if not BASE_URL:
        # This will stop the function if the URL isn't configured
        raise ValueError("BASE_URL environment variable is not set.")
    
    FILENAME = f"tts_{uuid4().hex}.mp3"
    filepath = os.path.join(TTS_DIR, FILENAME)

    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(filepath)
    
    # [FIX 3] The typo is also fixed by this logic, but the main point
    # is to always construct the full URL.
    public_url = f"{BASE_URL.rstrip('/')}/static/tts/{FILENAME}"

    return filepath, public_url