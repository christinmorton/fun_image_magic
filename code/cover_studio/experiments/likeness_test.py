#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Likeness test (plan step 18): does the image AI keep a scanned person recognisable in
# the New Orleans style, and do three angles help compared with one photo? It makes four
# images: two scenes (Inferno, Boss office) x (the front photo only, all the angles).
#
# COSTS MONEY with --run (about $0.045 per image, so about $0.18). Without --run it only
# checks and prints what it would send. From the cover_studio folder:
#   .\.venv\Scripts\python.exe experiments\likeness_test.py helena          (free: a dry run)
#   .\.venv\Scripts\python.exe experiments\likeness_test.py helena --run    (sends, about $0.18)
# Results go to subjects/<name>/likeness_test/<date-time>/ (gitignored, deleted with the
# subject), with the prompts and a side-by-side comparison sheet.
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.ai import DEFAULT_MODEL, AiError, GeminiGenerator                     # noqa: E402
from core.env_file import load_env                                             # noqa: E402
from core.styles import NEW_ORLEANS, build_prompt                              # noqa: E402
from core.subjects import SUBJECTS_DIR, has_current_consent, load_subject      # noqa: E402

SCENES = ['inferno', 'boss_office']
COST_PER_IMAGE = 0.045      # what Google billed per image in practice (core/ai.py's estimate is lower)
TILE = 360                  # comparison sheet tiles, in pixels


def plan(pictures):
    # the jobs: (scene, which photos, the photos, the prompt)
    angles = [k for k in ('front', 'left', 'right') if k in pictures]
    jobs = []
    for scene in SCENES:
        for refs in (['front'], angles):
            label = 'front only' if refs == ['front'] else f'{len(refs)} angles'
            jobs.append((scene, label, [pictures[k] for k in refs], build_prompt(NEW_ORLEANS, scene, len(refs))))
    return jobs

def tile(img, label):
    scale = TILE / max(img.shape[:2])
    small = cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    out = np.full((TILE + 30, TILE, 3), 30, np.uint8)
    y, x = (TILE - small.shape[0]) // 2, (TILE - small.shape[1]) // 2
    out[y:y + small.shape[0], x:x + small.shape[1]] = small
    cv2.putText(out, label, (8, TILE + 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return out

def main():
    run = '--run' in sys.argv[1:]
    names = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(names) != 1:
        sys.exit('Usage: likeness_test.py <subject folder name> [--run]')
    folder = SUBJECTS_DIR / names[0]
    if not (folder / 'subject.json').is_file():
        sys.exit(f'No saved subject called "{names[0]}" in subjects/.')
    info, pictures = load_subject(folder)
    if not has_current_consent(info):
        warning = (f'{info["name"]} hasn\'t agreed to the current permission wording, which covers sending their '
                   f'photos to the image AI.\nShow it to them first:  .\\.venv\\Scripts\\python.exe desktop\\scan.py '
                   f'--reconfirm {names[0]}')
        if run:
            sys.exit(warning)                   # nothing is ever sent without it
        print(warning + '\n')
    jobs = plan(pictures)
    print(f'Subject: {info["name"]} ({", ".join(info["angles"])})   model: {DEFAULT_MODEL}')
    for scene, label, images, prompt in jobs:
        print(f'  {NEW_ORLEANS.scenes[scene][0]:12} {label:11} sends {len(images)} photo(s), {len(prompt.split())} words')
    print(f'\nFirst prompt in full:\n{jobs[0][3]}\n')
    cost = len(jobs) * COST_PER_IMAGE
    if not run:
        print(f'Dry run: nothing was sent. Add --run to make the {len(jobs)} images (about ${cost:.2f}).')
        return
    load_env(SERVICE_DIR / '.env')
    if not os.environ.get('GEMINI_API_KEY'):
        sys.exit('GEMINI_API_KEY is not set in .env')
    out = folder / 'likeness_test' / f'{datetime.now():%Y%m%d-%H%M%S}'
    out.mkdir(parents=True)
    generator = GeminiGenerator()
    results, made = [], 0
    for scene, label, images, prompt in jobs:
        name = f'{scene}_{label.replace(" ", "_")}'
        start = time.perf_counter()
        try:
            image = generator.generate(prompt, images, '1:1')
            cv2.imwrite(str(out / f'{name}.png'), image)
            error, made = None, made + 1
        except AiError as problem:
            image, error = None, str(problem)
        seconds = round(time.perf_counter() - start, 1)
        print(f'  {name:28} {"ok" if error is None else "FAILED: " + error}  ({seconds} s)')
        results.append({'scene': scene, 'photos': label, 'file': f'{name}.png' if error is None else None,
                        'error': error, 'seconds': seconds, 'prompt': prompt})
    (out / 'results.json').write_text(json.dumps({'subject': info['name'], 'model': DEFAULT_MODEL,
                                                  'results': results}, indent=2), encoding='utf-8')
    # the comparison sheet: per scene, the front photo, then the two results
    rows = []
    for scene in SCENES:
        row = [tile(pictures['front'], 'scan: front')]
        for r in [r for r in results if r['scene'] == scene]:
            pic = cv2.imread(str(out / r['file'])) if r['file'] else np.zeros((TILE, TILE, 3), np.uint8)
            row.append(tile(pic, f'{NEW_ORLEANS.scenes[scene][0]}: {r["photos"]}'))
        rows.append(np.hstack(row))
    cv2.imwrite(str(out / 'comparison.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(f'\nMade {made} of {len(jobs)} images (about ${made * COST_PER_IMAGE:.2f}). Saved to {out}')


if __name__ == '__main__':
    main()
