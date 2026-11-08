#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Draws every lettering treatment clean on a dark background, then aged with the "print"
# and "vhs" finishes on a fiery one, so they can be compared by eye. Free to run: no AI.
# From the cover_studio folder:
#   .\.venv\Scripts\python.exe experiments\lettering_sheet.py ["YOUR NAME"]
# The sheet is saved to experiments/output/lettering_sheet.png.
import sys
import time
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.finish import age                           # noqa: E402
from core.lettering import TREATMENTS, draw_words     # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
SIZE = 150          # font size in pixels


def backgrounds(w, h):
    # plain near-black, and a fire-like gradient (dark red at the top to orange below)
    dark = np.full((h, w, 3), 18, np.uint8)
    t = np.linspace(0, 1, h)[:, None, None]
    fire = (np.array([10, 20, 90]) * (1 - t) + np.array([20, 120, 255]) * t).astype(np.uint8)
    return dark, np.repeat(fire, w, axis=1)

def lay_over(background, words):
    # a BGRA image laid over the centre of a BGR background
    out = background.copy()
    h, w = words.shape[:2]
    y, x = (out.shape[0] - h) // 2, (out.shape[1] - w) // 2
    a = words[..., 3:] / 255.0
    out[y:y + h, x:x + w] = (words[..., :3] * a + out[y:y + h, x:x + w] * (1 - a)).astype(np.uint8)
    return out


def main():
    text = sys.argv[1] if len(sys.argv) > 1 else 'BIG MIKE'
    rows = []
    for name in TREATMENTS:
        start = time.perf_counter()
        words = draw_words(text, name, SIZE, seed=1)
        print(f'{name:9} {words.shape[1]}x{words.shape[0]}  {(time.perf_counter() - start) * 1000:.0f} ms')
        w, h = words.shape[1] + 40, words.shape[0] + 20
        dark, fire = backgrounds(w, h)
        row = np.hstack([lay_over(dark, words), lay_over(fire, age(words, 'print', seed=1)),
                         lay_over(fire, age(words, 'vhs', seed=1))])
        cv2.putText(row, name, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)
        rows.append(row)
    width = max(r.shape[1] for r in rows)
    sheet = np.vstack([cv2.copyMakeBorder(r, 0, 0, 0, width - r.shape[1], cv2.BORDER_CONSTANT, value=(40, 40, 40))
                       for r in rows])
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / 'lettering_sheet.png'
    cv2.imwrite(str(path), sheet)
    print('saved', path)


if __name__ == '__main__':
    main()
