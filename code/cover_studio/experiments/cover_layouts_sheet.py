#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Draws the lettering of every cover layout over a placeholder picture (a fiery background
# and a grey stand-in for the person), to check the spacing. Free to run: no AI.
# From the cover_studio folder:
#   .\.venv\Scripts\python.exe experiments\cover_layouts_sheet.py ["YOUR NAME"]
# The sheet is saved to experiments/output/cover_layouts_sheet.png.
import sys
import time
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import LAYOUTS, CoverWords, apply_lettering, draw_cover_lettering   # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
SIZE = 900          # each cover, in pixels

CREW = ('Lil Ray', 'Big Tee', 'Dre', 'Mama Jo', 'Cousin Pookie', 'Lady K', 'Smoke', 'Uncle Ray', 'Nita')


def placeholder(size, people=1):
    # a dark-red-to-orange background with grey silhouettes where the people would stand
    t = np.linspace(0, 1, size)[:, None, None]
    img = np.repeat((np.array([20, 30, 110]) * (1 - t) + np.array([30, 140, 255]) * t).astype(np.uint8), size, axis=1)
    for i in range(people):
        cx = int(size * (i + 1) / (people + 1))
        scale = 1.0 if people == 1 else 0.6
        cv2.ellipse(img, (cx, int(size * 0.62)), (int(size * 0.2 * scale), int(size * 0.28 * scale)), 0, 180, 360,
                    (70, 70, 70), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, int(size * (0.4 if people == 1 else 0.48))), int(size * 0.11 * scale), (90, 90, 90), -1, cv2.LINE_AA)
    return img


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else 'BIG MIKE'
    covers = []
    for key, layout in LAYOUTS.items():
        crew = key == 'crew_row'
        words = CoverWords(name='DA FAM' if crew else name, title='HOOD RICH' if crew else 'BOSS LIFE',
                           presents=f'{name} presents' if key == 'boss_desk' else 'Big Tee presents',
                           featuring=CREW)
        start = time.perf_counter()
        lettering = draw_cover_lettering(words, layout, SIZE, seed=1)
        print(f'{key:16} {(time.perf_counter() - start) * 1000:.0f} ms')
        cover = apply_lettering(placeholder(SIZE, 4 if crew else 1), lettering)
        cv2.putText(cover, layout.name, (10, SIZE - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        covers.append(cover)
    sheet = np.vstack([np.hstack(covers[:2]), np.hstack(covers[2:4])])
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / 'cover_layouts_sheet.png'
    cv2.imwrite(str(path), sheet)
    print('saved', path)


if __name__ == '__main__':
    main()
