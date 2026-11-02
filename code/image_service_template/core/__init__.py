# core: the image engine - presets, masks, overlays, props, looks and rendering, slot
# layouts, MediaPipe analysis and the art library. No windows and no web code, so the
# desktop app (desktop/) and the web API (api/) can both use it.
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = CORE_DIR / 'assets'      # frames, stickers, backgrounds, mascot poses, props
MODELS_DIR = CORE_DIR / 'models'      # MediaPipe face landmarker and person segmenter
