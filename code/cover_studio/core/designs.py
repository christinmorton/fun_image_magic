# designs: saving a design to its own folder in designs/ (kept on this machine, never
# committed): the lettering at print size as a transparent PNG, a preview with the picture
# behind it, and a recipe (the words, layout, styles, seed and each part's finish) that
# remakes it exactly.
import json
import re
from dataclasses import asdict
from datetime import datetime

import cv2

from . import CORE_DIR
from .cover_layout import (LAYOUTS, PIECES, CoverWords, apply_lettering, draw_cover_lettering, placeholder,
                           square_crop)

DESIGNS_DIR = CORE_DIR.parent / 'designs'
PRINT_SIZE = 3600          # a square cover 12 inches across at 300 dpi
PREVIEW_SIZE = 1200


def slug(text):
    # a short, safe folder name from the words, e.g. "Big Mike!" -> "big-mike"
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:40] or 'design'

def new_folder(designs_dir, name):
    # designs/<date-time>-<name>/, never reusing a folder that already exists
    base = f'{datetime.now():%Y%m%d-%H%M%S}-{slug(name)}'
    folder, n = designs_dir / base, 2
    while folder.exists():
        folder, n = designs_dir / f'{base}-{n}', n + 1
    folder.mkdir(parents=True)
    return folder

def save_lettering(words, layout, styles=None, seed=0, picture=None, print_size=PRINT_SIZE,
                   designs_dir=DESIGNS_DIR, finishes=None, strength=1.0):
    # draws the lettering at print size, each part aged with its own finish (see
    # core/finish.py; e.g. {'name': 'vhs'}), and saves it with a preview and its recipe;
    # returns the new folder. picture is the BGR picture behind it (None = a placeholder)
    styles = {**LAYOUTS[layout].styles, **(styles or {})}
    finishes = {piece: (finishes or {}).get(piece, 'clean') for piece in PIECES}
    folder = new_folder(designs_dir, words.name)
    lettering = draw_cover_lettering(words, layout, print_size, styles, seed, finishes, strength)
    cv2.imwrite(str(folder / 'lettering.png'), lettering)
    if picture is None:
        picture = placeholder(PREVIEW_SIZE, 4 if layout == 'crew_row' else 1)
    picture = cv2.resize(square_crop(picture), (PREVIEW_SIZE, PREVIEW_SIZE), interpolation=cv2.INTER_AREA)
    small = cv2.resize(lettering, (PREVIEW_SIZE, PREVIEW_SIZE), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(folder / 'preview.jpg'), apply_lettering(picture, small), [cv2.IMWRITE_JPEG_QUALITY, 92])
    recipe = {'words': asdict(words), 'layout': layout, 'styles': styles, 'seed': seed,
              'finishes': finishes, 'strength': strength,
              'print_size': print_size, 'created': datetime.now().isoformat(timespec='seconds')}
    (folder / 'recipe.json').write_text(json.dumps(recipe, indent=2), encoding='utf-8')
    return folder

def load_recipe(folder):
    # a saved design's settings, ready to draw again: a dict with words (a CoverWords),
    # layout, styles, seed, finishes (part -> finish) and strength
    recipe = json.loads((folder / 'recipe.json').read_text(encoding='utf-8'))
    words = recipe['words']
    recipe['words'] = CoverWords(**{k: tuple(v) if isinstance(v, list) else v for k, v in words.items()})
    if 'finishes' not in recipe:                    # older recipes had one finish (or none) for everything
        one = recipe.pop('finish', 'clean')
        recipe['finishes'] = {piece: one for piece in PIECES}
    recipe.setdefault('strength', 1.0)
    return recipe
