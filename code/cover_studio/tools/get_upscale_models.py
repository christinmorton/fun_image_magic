#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Downloads the super-resolution models the upscaler uses (core/upscale.py) into
# core/models/upscale/, with their licence. They're too big to keep in git (EDSR is about
# 38 MB per scale), so each copy of the app fetches them once. All are Apache 2.0.
# From the cover_studio folder:  .\.venv\Scripts\python.exe tools\get_upscale_models.py
import sys
import urllib.request
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.upscale import MODELS, UPSCALE_DIR     # noqa: E402

LICENCES = {
    'EDSR-LICENSE.txt': 'https://raw.githubusercontent.com/Saafke/EDSR_Tensorflow/master/LICENSE',
    'FSRCNN-LICENSE.txt': 'https://raw.githubusercontent.com/Saafke/FSRCNN_Tensorflow/master/LICENSE',
}


def fetch(url, path):
    if path.exists() and path.stat().st_size > 0:
        print(f'  have  {path.name}')
        return
    print(f'  fetch {path.name} ...', end=' ', flush=True)
    request = urllib.request.Request(url, headers={'User-Agent': 'cover-studio'})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    path.write_bytes(data)
    print(f'{len(data) / 1e6:.1f} MB')


def main():
    UPSCALE_DIR.mkdir(parents=True, exist_ok=True)
    for model in MODELS.values():
        fetch(model.url, UPSCALE_DIR / model.file)
    for name, url in LICENCES.items():
        fetch(url, UPSCALE_DIR / name)
    print(f'Models are in {UPSCALE_DIR}')


if __name__ == '__main__':
    main()
