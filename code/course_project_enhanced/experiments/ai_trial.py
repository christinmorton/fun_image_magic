#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# AI trial (not part of the app): sends a few test requests to Google's Nano Banana image
# model and saves the results, so we can judge quality, speed and cost before building it
# into the editor. Each run costs roughly $0.10-0.15 (three 1K images, Oct 2026 prices).
#
#   .\.venv\Scripts\python.exe experiments\ai_trial.py path\to\photo.jpg
#
# Needs GEMINI_API_KEY in .env (copy .env.example). Results go to experiments/output/.
import base64
import sys
import time
from pathlib import Path

import cv2
import numpy as np

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from env_file import load_env           # noqa: E402
from masks import blend, refine_mask    # noqa: E402
from sources import load_image          # noqa: E402
from tracking import Tracker            # noqa: E402

MODEL = 'gemini-nano-banana-2.1'        # Nano Banana 2.1, $0.0336 per 1K image output
OUTPUT_DIR = APP_DIR / 'experiments' / 'output'


def to_png_b64(img):
    # an OpenCV image -> base64 PNG text, the way the API wants images
    ok, png = cv2.imencode('.png', img)
    return base64.b64encode(png.tobytes()).decode('utf-8')

def generate(client, prompt, images, aspect_ratio):
    # one request: text + images in, one image out. Returns (image, seconds, interaction)
    content = [{'type': 'text', 'text': prompt}]
    content += [{'type': 'image', 'data': to_png_b64(img), 'mime_type': 'image/png'} for img in images]
    start = time.perf_counter()
    interaction = client.interactions.create(
        model=MODEL, input=content,
        response_format={'type': 'image', 'aspect_ratio': aspect_ratio, 'image_size': '1K'})
    seconds = time.perf_counter() - start
    data = base64.b64decode(interaction.output_image.data)
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR), seconds, interaction

def on_white(bgra):
    # a transparent cut-out flattened onto white (simplest for the model to read)
    alpha = bgra[..., 3:] / 255.0
    return (bgra[..., :3] * alpha + 255 * (1 - alpha)).astype(np.uint8)

def key_out_green(img):
    # the model can't make transparent images, so cartoon Cody is drawn on bright green;
    # turn the green into transparency (a chroma key, like a green screen)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (40, 120, 120), (85, 255, 255))
    alpha = cv2.GaussianBlur(255 - green, (3, 3), 0)
    out = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    out[..., 3] = alpha
    return out


def main():
    loaded = load_env(APP_DIR / '.env')
    if 'GEMINI_API_KEY' not in loaded and not __import__('os').environ.get('GEMINI_API_KEY'):
        raise SystemExit('No GEMINI_API_KEY: copy .env.example to .env and add your key.')
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python experiments/ai_trial.py path/to/photo.jpg')
    photo = load_image(sys.argv[1])
    if photo is None:
        raise SystemExit(f'Could not load {sys.argv[1]}')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUTPUT_DIR / '0_input.png'), photo)

    from google import genai              # imported here so the checks above run first
    client = genai.Client()               # reads GEMINI_API_KEY from the environment
    aspect = '4:3' if photo.shape[1] >= photo.shape[0] else '3:4'
    results = []

    # 1. AI style: restyle the whole photo, keeping the person recognisable
    prompt = ("Restyle this photo as a bold, colourful comic-book illustration with ink outlines. "
              "Keep the person's face, hair, expression and pose recognisable.")
    results.append(('1_style_comic', prompt, [photo]))

    # 2. AI background: the model has no mask input, so ask for the background only, then
    #    put the original person back on top with our own person mask (step 5)
    prompt = ("Replace only the background of this photo with the Las Vegas Strip at night, with "
              "bright neon signs. Keep the person exactly the same: face, hair, clothes, pose and size.")
    results.append(('2_background_vegas', prompt, [photo]))

    # 3. cartoon Cody: the three Cody cut-outs as reference images
    codys = [on_white(cv2.imread(str(p), cv2.IMREAD_UNCHANGED))
             for p in sorted((APP_DIR / 'assets' / 'mascot').glob('*.png'))]
    prompt = ("These photos show Cody, a coyote mascot in a costume. Draw Cody as a friendly flat "
              "vector cartoon character: the same grey and cream coyote face, big eyes, and a blue "
              "CSN jersey. Full body, standing, waving with one paw. Plain solid bright green "
              "(#00FF00) background, no other objects, no text, no shadow.")
    results.append(('3_cartoon_cody', prompt, codys))

    tracker = Tracker(APP_DIR / 'models')
    total = 0.0
    for name, prompt, images in results:
        try:
            out, seconds, interaction = generate(client, prompt, images,
                                                 '3:4' if name.startswith('3') else aspect)
        except Exception as error:          # a blocked or failed request shouldn't stop the others
            print(f'{name}: FAILED - {type(error).__name__}: {error}')
            continue
        total += seconds
        cv2.imwrite(str(OUTPUT_DIR / f'{name}.png'), out)
        usage = getattr(interaction, 'usage', None)
        print(f'{name}: {seconds:.1f} s, {out.shape[1]}x{out.shape[0]}, usage: {usage}')

        if name.startswith('2'):
            # put the original person back over the AI background, at the photo's size
            ai_bg = cv2.resize(out, (photo.shape[1], photo.shape[0]), interpolation=cv2.INTER_AREA)
            _, person_mask = tracker.analyse_still(photo)
            mask = refine_mask(person_mask, photo)
            cv2.imwrite(str(OUTPUT_DIR / f'{name}_person_kept.png'), blend(photo, ai_bg, mask))
        if name.startswith('3'):
            cv2.imwrite(str(OUTPUT_DIR / f'{name}_transparent.png'), key_out_green(out))
    tracker.close()
    print(f'Done in {total:.1f} s of generation. Results: {OUTPUT_DIR}')


if __name__ == '__main__':
    main()
