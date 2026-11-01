# settings: where the service's files are, and its secrets (read from image_service/.env).
import os
from pathlib import Path

from core.env_file import load_env

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_env(SERVICE_DIR / '.env')      # keys already set in the real environment win

SERVICE_VERSION = '0.1.0'


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

def ai_configured():
    return bool(os.environ.get('GEMINI_API_KEY'))

def service_token():
    # the shared secret Laravel sends with every /v1 request (IMAGE_SERVICE_TOKEN in .env);
    # read on each call, so a changed environment (or a test) takes effect straight away
    return os.environ.get('IMAGE_SERVICE_TOKEN', '')
