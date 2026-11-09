# artwork: a cover's picture, made by the image AI from the photos of one person or a
# crew, and a style - the only step that costs money. Previews are a few 1K versions to
# pick from (made at the same time); a final is the picked preview made again at 2K or 4K.
# Every set is saved with the subject (or, for a crew, in subjects/_crews/), in
# artwork/<date-time>/, with the request that made it. Spending is checked against the
# daily limit first and logged after (core/spending.py).
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime

import cv2

from .ai import DEFAULT_MODEL, AiError
from .spending import PRICES
from .styles import CUSTOM, build_prompt, check_user_text

PREVIEW_COUNT = 4
ANGLE_ORDER = ('front', 'left', 'right')
# the model takes up to 14 images; a final also sends the preview, so 12 photos leaves room.
# A crew of up to 4 sends everyone's three angles; a bigger one sends front photos only
MAX_PHOTOS = 12

FINAL_PROMPT = ('Recreate the first image exactly as it is - the same composition, pose, clothing, jewellery, '
                'colours, lighting and background - as a sharper, more detailed, higher-resolution version. The '
                'other photos show the people in it: keep their faces exactly like them. No text, no letters, no '
                'logos.')


@dataclass(frozen=True)
class ArtworkRequest:
    style: str = 'new_orleans'
    scene: str = 'inferno'
    clothing: str = 'gold_silk'         # a key of styles.CLOTHING
    jewellery: tuple = ()               # keys of styles.JEWELLERY (empty = no jewellery)
    accessories: tuple = ()             # keys of styles.ACCESSORIES
    details: str = ''                   # the user's own words, added to the scene
    custom_scene: str = ''              # the user's own scene (used when scene is styles.CUSTOM)

    def prompt(self, references, people=1):
        # the prompt for `references` photos of each of `people` people
        return build_prompt(self.style, self.scene, references, clothing=self.clothing,
                            jewellery=self.jewellery, accessories=self.accessories,
                            details=self.details, custom_scene=self.custom_scene, people=people)

    def problems(self):
        # what's wrong with the user's own words, if anything (see styles.check_user_text)
        words = self.details + ' ' + (self.custom_scene if self.scene == CUSTOM else '')
        found = check_user_text(words)
        if self.scene == CUSTOM and not self.custom_scene.strip():
            found.append('the custom scene has no description')
        return found


def as_people(people):
    # one subject's pictures ({angle: picture}) or a list of them -> a list of them
    return [people] if isinstance(people, dict) else list(people)

def reference_photos(people):
    # the photos to send and how many there are per person, in order: each person's
    # photos together, front first. All the angles when they fit (the likeness test
    # showed they keep faces closer than a front photo alone); otherwise everyone's front
    # photo. Every person sends the same angles, so the prompt can say whose photos are whose
    people = as_people(people)
    if len(people) == 1:
        keys = [k for k in ANGLE_ORDER if k in people[0]]
    elif all(k in p for p in people for k in ANGLE_ORDER) and len(people) * len(ANGLE_ORDER) <= MAX_PHOTOS:
        keys = list(ANGLE_ORDER)
    else:
        keys = ['front']
    return [p[k] for p in people for k in keys if k in p], len(keys)

def preview_cost(count=PREVIEW_COUNT):
    return round(count * PRICES['1K'], 4)

def final_cost(size='2K'):
    return PRICES[size]

def _make(generator, prompt, images, size):
    try:
        return generator.generate(prompt, images, '1:1', size), None
    except AiError as error:
        return None, str(error)

def make_previews(people, request, generator, spending, count=PREVIEW_COUNT):
    # `count` 1K versions of the artwork for one person's pictures or a crew's (a list),
    # made at the same time: a list of (image or None, error or None). Raises
    # spending.OverLimit before sending anything if it would go over today's limit
    people = as_people(people)
    refs, per_person = reference_photos(people)
    if not refs or len(refs) != per_person * len(people):
        raise ValueError('everyone needs at least a front photo')
    if request.problems():
        raise ValueError('; '.join(request.problems()))
    spending.check(preview_cost(count))
    prompt = request.prompt(per_person, len(people))
    with ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda _: _make(generator, prompt, refs, '1K'), range(count)))
    spending.record(sum(1 for image, _ in results if image is not None), '1K', f'{count} previews')
    return results

def make_final(people, preview, generator, spending, size='2K'):
    # the chosen preview made again at `size`, sent with the people's photos so the faces
    # stay theirs: (image or None, error or None)
    spending.check(final_cost(size))
    image, error = _make(generator, FINAL_PROMPT, [preview] + reference_photos(people)[0], size)
    spending.record(1 if image is not None else 0, size, f'final at {size}')
    return image, error


def new_artwork_folder(subject_folder):
    base = subject_folder / 'artwork' / f'{datetime.now():%Y%m%d-%H%M%S}'
    folder, n = base, 2
    while folder.exists():
        folder, n = base.with_name(f'{base.name}-{n}'), n + 1
    folder.mkdir(parents=True)
    return folder

def save_previews(subject_folder, request, results, references, people=1, members=()):
    # saves preview_1.png... and request.json (with the prompt sent for `references` photos
    # of each of `people` people, and the members' names) in a new artwork folder; returns it
    folder = new_artwork_folder(subject_folder)
    for i, (image, _) in enumerate(results, start=1):
        if image is not None:
            cv2.imwrite(str(folder / f'preview_{i}.png'), image)
    info = {'request': asdict(request), 'prompt': request.prompt(references, people), 'model': DEFAULT_MODEL,
            'members': list(members),
            'previews': [{'file': f'preview_{i}.png' if image is not None else None, 'error': error}
                         for i, (image, error) in enumerate(results, start=1)],
            'created': datetime.now().isoformat(timespec='seconds')}
    (folder / 'request.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return folder

def save_final(folder, preview_number, size, image):
    path = folder / f'final_{preview_number}_{size}.png'
    cv2.imwrite(str(path), image)
    return path
