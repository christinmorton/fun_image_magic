# settings: where the service's files are, and its secrets (read from image_service/.env).
import os
from pathlib import Path

from core.env_file import load_env

SERVICE_DIR = Path(__file__).resolve().parent.parent
load_env(SERVICE_DIR / '.env')      # keys already set in the real environment win

SERVICE_VERSION = '0.1.0'


def service_token():
    # the shared secret Laravel sends with every /v1 request (IMAGE_SERVICE_TOKEN in .env);
    # read on each call, so a changed environment (or a test) takes effect straight away
    return os.environ.get('IMAGE_SERVICE_TOKEN', '')
