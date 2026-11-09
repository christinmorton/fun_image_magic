# settings: where the service's files are, and its secrets (read from image_service/.env).
import os
import tempfile
from pathlib import Path

from core.env_file import load_env

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_env(SERVICE_DIR / '.env')      # keys already set in the real environment win

SERVICE_VERSION = '0.2.0'           # keep in step with CHANGELOG.md


def photo_ttl_seconds():
    # how long uploaded photos are kept (PHOTO_TTL_SECONDS in .env; default 2 hours)
    try:
        return max(60, int(os.environ.get('PHOTO_TTL_SECONDS', 7200)))
    except ValueError:
        return 7200

def ai_daily_limit():
    # how many AI images may be made per UTC day (AI_DAILY_LIMIT in .env; default 100)
    try:
        return max(0, int(os.environ.get('AI_DAILY_LIMIT', 100)))
    except ValueError:
        return 100

def rate_limit_per_minute():
    # uploads + renders + layouts + AI jobs allowed per minute per client
    # (RATE_LIMIT_PER_MINUTE in .env; default 120; 0 = no limit)
    try:
        return max(0, int(os.environ.get('RATE_LIMIT_PER_MINUTE', 120)))
    except ValueError:
        return 120

def _megabytes(name, default):
    # a size in MB from .env, as bytes (at least 1 MB)
    try:
        return max(1, int(os.environ.get(name, default))) * 1024 * 1024
    except ValueError:
        return default * 1024 * 1024

def video_max_bytes():
    # the largest video upload (VIDEO_MAX_MB in .env; default 300 MB, over 5 minutes of webcam video)
    return _megabytes('VIDEO_MAX_MB', 300)

def video_storage_bytes():
    # how much video may be kept at once; uploads past it are refused (VIDEO_STORAGE_MB; default 3000 MB)
    return _megabytes('VIDEO_STORAGE_MB', 3000)

def video_ttl_seconds():
    # how long uploaded videos are kept for the app to fetch (VIDEO_TTL_SECONDS; default 2 hours)
    try:
        return max(60, int(os.environ.get('VIDEO_TTL_SECONDS', 7200)))
    except ValueError:
        return 7200

def video_dir():
    # where uploaded videos are kept until they expire (VIDEO_DIR; default a folder in the system's
    # temp folder). The folder is emptied each time the service starts.
    return Path(os.environ.get('VIDEO_DIR') or Path(tempfile.gettempdir()) / 'image-service-videos')

def ai_configured():
    return bool(os.environ.get('GEMINI_API_KEY'))

def service_token():
    # the shared secret the calling app sends with every /v1 request (IMAGE_SERVICE_TOKEN in .env);
    # read on each call, so a changed environment (or a test) takes effect straight away
    return os.environ.get('IMAGE_SERVICE_TOKEN', '')
