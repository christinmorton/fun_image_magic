# artwork: a cover's picture, made by the image AI from a subject's photos and a style -
# the only step that costs money. Previews are a few 1K versions to pick from (made at
# the same time); a final is the picked preview made again at 2K or 4K. Every set is saved
# with the subject, in subjects/<name>/artwork/<date-time>/, with the request that made
# it. Spending is checked against the daily limit first and logged after (core/spending.py).
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime

import cv2

from .ai import DEFAULT_MODEL, AiError
from .spending import PRICES
from .styles import build_prompt

PREVIEW_COUNT = 4
ANGLE_ORDER = ('front', 'left', 'right')

FINAL_PROMPT = ('Recreate the first image exactly as it is - the same composition, pose, clothing, jewellery, '
                'colours, lighting and background - as a sharper, more detailed, higher-resolution version. The '
                'other photos show the same person: keep their face exactly like them. No text, no letters, no '
                'logos.')


@dataclass(frozen=True)
class ArtworkRequest:
    style: str = 'new_orleans'
    scene: str = 'inferno'
    clothing: str = 'gold_silk'         # a key of styles.CLOTHING
    jewellery: tuple = ()               # keys of styles.JEWELLERY (empty = no jewellery)
    accessories: tuple = ()             # keys of styles.ACCESSORIES

    def prompt(self, references):
        return build_prompt(self.style, self.scene, references, clothing=self.clothing,
                            jewellery=self.jewellery, accessories=self.accessories)


def reference_photos(pictures):
    # a subject's photos to send, front first (all the angles: the likeness test showed
    # they keep the face closer than the front photo alone)
    return [pictures[k] for k in ANGLE_ORDER if k in pictures]

def preview_cost(count=PREVIEW_COUNT):
    return round(count * PRICES['1K'], 4)

def final_cost(size='2K'):
    return PRICES[size]

def _make(generator, prompt, images, size):
    try:
        return generator.generate(prompt, images, '1:1', size), None
    except AiError as error:
        return None, str(error)

def make_previews(pictures, request, generator, spending, count=PREVIEW_COUNT):
    # `count` 1K versions of the artwork, made at the same time: a list of (image or
    # None, error or None). Raises spending.OverLimit before sending anything if it would
    # go over today's limit
    refs = reference_photos(pictures)
    if not refs:
        raise ValueError('the subject has no photos')
    spending.check(preview_cost(count))
    prompt = request.prompt(len(refs))
    with ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda _: _make(generator, prompt, refs, '1K'), range(count)))
    spending.record(sum(1 for image, _ in results if image is not None), '1K', f'{count} previews')
    return results

def make_final(pictures, preview, generator, spending, size='2K'):
    # the chosen preview made again at `size`, sent with the subject's photos so the face
    # stays theirs: (image or None, error or None)
    spending.check(final_cost(size))
    image, error = _make(generator, FINAL_PROMPT, [preview] + reference_photos(pictures), size)
    spending.record(1 if image is not None else 0, size, f'final at {size}')
    return image, error


def new_artwork_folder(subject_folder):
    base = subject_folder / 'artwork' / f'{datetime.now():%Y%m%d-%H%M%S}'
    folder, n = base, 2
    while folder.exists():
        folder, n = base.with_name(f'{base.name}-{n}'), n + 1
    folder.mkdir(parents=True)
    return folder

def save_previews(subject_folder, request, results, references):
    # saves preview_1.png... and request.json (with the prompt sent for `references`
    # photos) in a new artwork folder; returns the folder
    folder = new_artwork_folder(subject_folder)
    for i, (image, _) in enumerate(results, start=1):
        if image is not None:
            cv2.imwrite(str(folder / f'preview_{i}.png'), image)
    info = {'request': asdict(request), 'prompt': request.prompt(references), 'model': DEFAULT_MODEL,
            'previews': [{'file': f'preview_{i}.png' if image is not None else None, 'error': error}
                         for i, (image, error) in enumerate(results, start=1)],
            'created': datetime.now().isoformat(timespec='seconds')}
    (folder / 'request.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return folder

def save_final(folder, preview_number, size, image):
    path = folder / f'final_{preview_number}_{size}.png'
    cv2.imwrite(str(path), image)
    return path
