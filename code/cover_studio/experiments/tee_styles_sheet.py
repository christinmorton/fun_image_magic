#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Puts saved covers on a light and a dark tee photo in each tee style (classic, faded,
# knockout, faded + knockout), to compare them. Free to run: no AI. Needs set-up tee photos
# in mockup_photos/ (see desktop/mockup_tool.py).
# From the cover_studio folder:
#   .\.venv\Scripts\python.exe experiments\tee_styles_sheet.py [design folder names...]
# With no names it uses every saved design with artwork, newest version of each name first.
# The sheet is saved to experiments/output/tee_styles_sheet.jpg, and each mockup to
# experiments/output/tee_styles/.
import sys
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.designs import list_designs                                         # noqa: E402
from core.photo_mockups import mockup, ready_photos, write_jpg                # noqa: E402
from core.products import PRODUCTS_BY_KEY, load_design, make_product          # noqa: E402
from core.tee_styles import STYLES, style_print_file                          # noqa: E402

OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
TILE = 420          # each mockup on the sheet, in pixels


def pick_designs(names):
    # the chosen design folders, or one per name (the newest) with artwork
    folders = [f for f in list_designs() if (f / 'artwork.png').is_file()]
    if names:
        return [f for f in folders if f.name in names]
    seen, picked = set(), []
    for folder in folders:                               # newest first
        person = folder.name.split('-', 2)[-1]
        if person not in seen:
            seen.add(person)
            picked.append(folder)
    return picked

def pick_photos():
    # the lightest and the darkest shirt among the closest front-view tee shots (the widest
    # print areas in pixels, ones set by hand first), so the print is easy to see
    def closeness(item):
        path, placement = item
        (x0, _), (x1, _) = placement.corners[:2]
        return (placement.status == 'set', abs(x1 - x0))
    def lightness(item):
        b, g, r = item[1].colour
        return 0.114 * b + 0.587 * g + 0.299 * r
    photos = sorted(ready_photos('tee'), key=closeness, reverse=True)[:25]
    if not photos:
        return []
    return [max(photos, key=lightness), min(photos, key=lightness)]

def label(img, text):
    cv2.rectangle(img, (0, img.shape[0] - 30), (img.shape[1], img.shape[0]), (0, 0, 0), -1)
    cv2.putText(img, text, (8, img.shape[0] - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return img

def main():
    designs, photos = pick_designs(sys.argv[1:]), pick_photos()
    if not designs or not photos:
        print('Needs a saved design with artwork and set-up tee photos (desktop\\mockup_tool.py).')
        return
    out_dir = OUTPUT_DIR / 'tee_styles'
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for folder in designs:
        print_file = make_product(PRODUCTS_BY_KEY['tee'], load_design(folder))
        for path, placement in photos:
            row = []
            for style in STYLES:
                styled = style_print_file(print_file, style, placement.colour)
                img = mockup(path, placement, styled)
                shade = 'dark' if placement.dark else 'light'
                write_jpg(out_dir / f'{folder.name}-{shade}-{style}.jpg', img)
                row.append(label(cv2.resize(img, (TILE, TILE), interpolation=cv2.INTER_AREA),
                                 f'{style.replace("_", " + ")}   {folder.name.split("-", 2)[-1]}'))
                print(f'{folder.name}  {shade}  {style}')
            rows.append(np.hstack(row))
    cv2.imwrite(str(OUTPUT_DIR / 'tee_styles_sheet.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(f'Saved {OUTPUT_DIR / "tee_styles_sheet.jpg"}')


if __name__ == '__main__':
    main()
