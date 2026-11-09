#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Downloads the two MediaPipe models the photo mockups use (core/photo_mockups.py) into
# core/models/mockups/: the pose landmarker (finds the shoulders and hips) and the
# multiclass selfie segmenter (marks which pixels are clothes). They're too big to keep in
# git (about 26 MB together), so each copy of the app fetches them once. Both are Apache 2.0
# (see their model cards on ai.google.dev/edge/mediapipe).
# From the cover_studio folder:  .\.venv\Scripts\python.exe tools\get_mockup_models.py
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.photo_mockups import MOCKUP_MODELS_DIR     # noqa: E402
from get_upscale_models import fetch                 # noqa: E402

MODELS = {
    'pose_landmarker_full.task': 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/'
                                 'pose_landmarker_full/float16/latest/pose_landmarker_full.task',
    'selfie_multiclass_256x256.tflite': 'https://storage.googleapis.com/mediapipe-models/image_segmenter/'
                                        'selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite',
}


def main():
    MOCKUP_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for name, url in MODELS.items():
        fetch(url, MOCKUP_MODELS_DIR / name)
    print(f'Models are in {MOCKUP_MODELS_DIR}')


if __name__ == '__main__':
    main()
