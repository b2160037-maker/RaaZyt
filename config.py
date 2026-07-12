"""
config.py -- single source of truth for RAAZ FILES automation.

Every secret/key is read from environment variables (GitHub Secrets in the
cloud, or a local .env for testing). NOTHING sensitive is hard-coded here.
"""
import os
import warnings
from pathlib import Path

# Silence harmless third-party deprecation/future warnings (e.g. the
# google.generativeai FutureWarning) so the console/log stays clean.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

try:
    from dotenv import load_dotenv  # python-dotenv is optional
    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default) or default


# ---------------------------------------------------------------------------
# BRAND IDENTITY  (change the channel in ONE place)
# ---------------------------------------------------------------------------
CHANNEL_NAME = env("CHANNEL_NAME", "RAAZ FILES")

SIGNATURE_LINE = (
    "Andar aao... par dhyaan se. Kyunki yahan har raaz, ek sach hai."
)

IMAGE_STYLE_SUFFIX = (
    "cinematic, dark moody, volumetric light, photorealistic, 8k, dramatic fog"
)

# ---------------------------------------------------------------------------
# VOICE  (keep consistent = the channel "voice")
# ---------------------------------------------------------------------------
TTS_VOICE = env("TTS_VOICE", "hi-IN-SwaraNeural")    # female, confident + melodious
TTS_RATE = env("TTS_RATE", "+20%")                   # fast, energetic delivery
TTS_RATE_REVEAL = env("TTS_RATE_REVEAL", "+12%")     # a touch slower on reveals
TTS_PITCH = env("TTS_PITCH", "+0Hz")                 # neutral (female already bright; avoids shrill)
TTS_VOLUME = env("TTS_VOLUME", "+0%")
GTTS_LANG = "hi"                                     # gTTS backup language

# Loudness targets (LUFS)
TARGET_LUFS_VOICE = -14.0
TARGET_LUFS_MUSIC = -22.0

# ---------------------------------------------------------------------------
# VIDEO / RENDER
# ---------------------------------------------------------------------------
LONG_W, LONG_H = 1920, 1080
SHORT_W, SHORT_H = 1080, 1920
FPS = 30
VIDEO_CRF = 20
KEN_BURNS_ZOOM = 1.15
CROSSFADE_SEC = 0.3
THUMB_W, THUMB_H = 1280, 720

# Target-minute ranges by topic depth (the model chooses within these).
MIN_MINUTES = 4
MAX_MINUTES = 12
DEFAULT_MINUTES = 8

# ---------------------------------------------------------------------------
# VISUALS SPEED / RELIABILITY TUNING
# ---------------------------------------------------------------------------
IMAGE_RETRIES = int(env("IMAGE_RETRIES", "1"))     # tries per image provider
IMAGE_TIMEOUT = int(env("IMAGE_TIMEOUT", "35"))    # seconds per image request
VISUAL_WORKERS = int(env("VISUAL_WORKERS", "4"))   # concurrent scene fetches

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.resolve()
ASSETS = ROOT / "assets"
BRAND = ASSETS / "brand"
MUSIC_DIR = ASSETS / "music"
SFX_DIR = ASSETS / "sfx"
FONTS_DIR = BRAND / "fonts"
THUMBS_DIR = ROOT / "thumbnails"
OUTPUT_DIR = ROOT / "output"

LOGO_STING = BRAND / "logo_sting.mp4"
AVATAR = BRAND / "avatar.png"
BANNER = BRAND / "banner.png"
SIGNATURE_STING = BRAND / "signature_sting.wav"

TOPICS_FILE = ROOT / "topics.json"
USED_TOPICS_FILE = ROOT / "used_topics.json"
STATE_FILE = ROOT / "state.json"

for _d in (ASSETS, BRAND, MUSIC_DIR, SFX_DIR, FONTS_DIR, THUMBS_DIR, OUTPUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# API KEYS / SECRETS  (all read from env; empty = provider skipped gracefully)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = env("GEMINI_API_KEY")
GROQ_API_KEY = env("GROQ_API_KEY")
OPENROUTER_API_KEY = env("OPENROUTER_API_KEY")
HF_TOKEN = env("HF_TOKEN")

PEXELS_API_KEY = env("PEXELS_API_KEY")
PIXABAY_API_KEY = env("PIXABAY_API_KEY")
STABLEHORDE_KEY = env("STABLEHORDE_KEY", "0000000000")  # anon key (rate-limited)

YT_CLIENT_SECRET_JSON = env("YT_CLIENT_SECRET_JSON")
YT_TOKEN_JSON = env("YT_TOKEN_JSON")
# Local (Windows/PowerShell) convenience: if the env/secret is not set, read the
# JSON straight from files in the project root (client_secret.json / token.json).
if not YT_CLIENT_SECRET_JSON and (ROOT / "client_secret.json").exists():
    YT_CLIENT_SECRET_JSON = (ROOT / "client_secret.json").read_text(encoding="utf-8")
if not YT_TOKEN_JSON and (ROOT / "token.json").exists():
    YT_TOKEN_JSON = (ROOT / "token.json").read_text(encoding="utf-8")

RCLONE_CONF = env("RCLONE_CONF")
GDRIVE_SA_JSON = env("GDRIVE_SA_JSON")
RCLONE_REMOTE = env("RCLONE_REMOTE", "gdrive:raaz-thumbnails")

GMAIL_USER = env("GMAIL_USER")
GMAIL_APP_PASSWORD = env("GMAIL_APP_PASSWORD")
OWNER_EMAIL = env("OWNER_EMAIL")

# ---------------------------------------------------------------------------
# MODEL NAMES
# ---------------------------------------------------------------------------
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-flash-latest")
GROQ_MODEL = env("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_MODEL = env("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
HF_TEXT_MODEL = env("HF_TEXT_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
HF_IMAGE_MODEL = env("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")

# ---------------------------------------------------------------------------
# UPLOAD BEHAVIOUR
# ---------------------------------------------------------------------------
YT_PRIVACY = env("YT_PRIVACY", "public")      # public | private | unlisted
YT_CATEGORY_ID = env("YT_CATEGORY_ID", "22")  # 22 = People & Blogs, 27 = Education

# ---------------------------------------------------------------------------
# STAGGERED SHORTS RELEASE (via YouTube scheduled publish)
# short 1 -> live immediately with the long video
# short 2 -> +SHORT2_DELAY_HOURS later
# short 3 -> next morning at SHORT3_HOUR_IST (24h clock, IST)
# ---------------------------------------------------------------------------
SHORT2_DELAY_HOURS = int(env("SHORT2_DELAY_HOURS", "2"))
SHORT3_HOUR_IST = int(env("SHORT3_HOUR_IST", "8"))

# ---------------------------------------------------------------------------
# FIXED BRANDED OUTRO  (unmodified 10s clip appended to EVERY long video + Short)
# ---------------------------------------------------------------------------
OUTRO_CLIP = BRAND / env("OUTRO_FILENAME", "Animate_a_logo_reveal_a_black.mp4")
OUTRO_DUCK_FACTOR = float(env("OUTRO_DUCK_FACTOR", "0.5"))  # ~ -6 dB while narration speaks
OUTRO_MAX_SEC = float(env("OUTRO_MAX_SEC", "10.0"))         # CTA must fit inside the clip
OUTRO_CTA_TEXT = env(
    "OUTRO_CTA_TEXT",
    "Agar tumhe sach jaanna pasand hai, toh is parivaar ka hissa ban jao -- "
    "Subscribe karo aur Like button zaroor dabao. Kyunki yaad rakhna... RAAZ KHULEGA.")
OUTRO_CTA_SHORT = env(
    "OUTRO_CTA_SHORT",
    "Is parivaar ka hissa bano -- Subscribe aur Like dabao. Kyunki... RAAZ KHULEGA.")

# ---------------------------------------------------------------------------
# ON-CAMERA HOST clip (shown when a scene needs the host "to camera").
# Auto looped/trimmed to that scene's narration length by edit.py. Its own
# audio is dropped -- the TTS narration plays over it.
# ---------------------------------------------------------------------------
HOST_CLIP = BRAND / env("HOST_FILENAME", "Animate_this_hooded_host_natu.mp4")

# ---------------------------------------------------------------------------
# OWNER TOPIC REQUESTS  (owner can pre-book a topic for a specific date)
# Edit owner_requests.json:  {"requests": [{"date":"YYYY-MM-DD","topic":"...","type":"..."}]}
# If a request exists for today's date it is used; else the SEO/seed bank is used.
# ---------------------------------------------------------------------------
OWNER_REQUESTS_FILE = ROOT / "owner_requests.json"
