# ai: AI image presets (styles and backgrounds) and the image generator that runs them.
# A generator is anything with generate(prompt, images, aspect_ratio) -> BGR image; the real
# one calls Google's Nano Banana model, and tests use a fake one, so nothing here needs the
# internet except GeminiGenerator itself.
import base64
from dataclasses import dataclass

import cv2
import numpy as np

from .masks import blend, refine_mask

DEFAULT_MODEL = 'gemini-nano-banana-2.1'        # $0.0336 per 1K image (Nov 2026)
COST_PER_IMAGE_USD = 0.037                      # output plus a typical input photo, for estimates
PERSON_KEEP_MIN_OVERLAP = 0.85                  # see run_ai_preset()

# the model's aspect ratios; each photo is sent with the closest one
ASPECT_RATIOS = ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9']

KEEP_PERSON = ("Keep the person exactly the same: face, hair, expression, clothes, pose, "
               "size and position in the frame. Do not add any text.")
KEEP_LIKENESS = ("Keep the person's face, hair, expression and pose recognisable. "
                 "Do not add any text.")


@dataclass(frozen=True)
class AiPreset:
    key: str          # what Laravel sends, e.g. "comic"
    name: str         # for the screen
    kind: str         # "style" (restyle the whole photo) or "background" (new scene, same person)
    prompt: str


AI_PRESETS = [
    AiPreset('comic', 'Comic book', 'style',
             'Restyle this photo as a bold, colourful comic-book illustration with ink outlines. ' + KEEP_LIKENESS),
    AiPreset('anime', 'Anime', 'style',
             'Restyle this photo as a bright anime illustration with clean lines. ' + KEEP_LIKENESS),
    AiPreset('oil_painting', 'Oil painting', 'style',
             'Restyle this photo as a classic oil painting with visible brush strokes. ' + KEEP_LIKENESS),
    AiPreset('superhero', 'Superhero', 'style',
             'Turn the person in this photo into a superhero in a blue and gold costume, in a dramatic '
             'comic-movie poster style. ' + KEEP_LIKENESS),
    AiPreset('vegas_neon', 'Vegas neon', 'style',
             'Restyle this photo with glowing Las Vegas neon colours and lighting, like a neon sign. ' + KEEP_LIKENESS),
    AiPreset('vegas_strip', 'Las Vegas Strip at night', 'background',
             'Replace only the background of this photo with the Las Vegas Strip at night, with bright '
             'neon signs. ' + KEEP_PERSON),
    AiPreset('csn_court', 'Basketball court', 'background',
             'Replace only the background of this photo with an indoor college basketball court with '
             'blue and gold colours. ' + KEEP_PERSON),
    AiPreset('outer_space', 'Outer space', 'background',
             'Replace only the background of this photo with outer space, with stars, a colourful '
             'nebula and a planet. ' + KEEP_PERSON),
    AiPreset('red_rock', 'Red Rock Canyon', 'background',
             'Replace only the background of this photo with Red Rock Canyon near Las Vegas on a sunny '
             'day. ' + KEEP_PERSON),
]
AI_PRESETS_BY_KEY = {preset.key: preset for preset in AI_PRESETS}


class AiError(Exception):
    """The AI request failed or returned no image (the message is safe to show)."""


def closest_aspect_ratio(w, h):
    def value(ratio):
        a, b = ratio.split(':')
        return int(a) / int(b)
    return min(ASPECT_RATIOS, key=lambda ratio: abs(value(ratio) - w / h))

def mask_overlap(a, b):
    # how much two person masks agree: shared area / combined area (0 = none, 1 = identical)
    a, b = a > 0.5, b > 0.5
    union = np.logical_or(a, b).sum()
    return float(np.logical_and(a, b).sum() / union) if union else 0.0

def run_ai_preset(image, preset, generator, find_person=None, on_stage=None):
    # one AI preset on one unedited photo -> (new photo at the same size, details)
    # For backgrounds, the original person is put back on top so their face is never
    # altered - but only if the AI kept them in the same place (the two person masks overlap
    # enough). The model sometimes reframes the picture, and pasting the person back then
    # would leave ghost copies; in that case the AI image is used as it is.
    # find_person(image) -> person mask or None (MediaPipe), needed for backgrounds
    # on_stage(name) is told when work moves on: "generating", then "checking_person"
    stage = on_stage or (lambda name: None)
    h, w = image.shape[:2]
    stage('generating')
    out = generator.generate(preset.prompt, [image], closest_aspect_ratio(w, h))
    out = cv2.resize(out, (w, h), interpolation=cv2.INTER_AREA)
    details = {'person_kept': False, 'overlap': None}
    if preset.kind == 'background' and find_person is not None:
        stage('checking_person')
        original, new = find_person(image), find_person(out)
        if original is not None and new is not None:
            details['overlap'] = round(mask_overlap(original.reshape(h, w), new.reshape(h, w)), 3)
            if details['overlap'] >= PERSON_KEEP_MIN_OVERLAP:
                out = blend(image, out, refine_mask(original, image))
                details['person_kept'] = True
    return out, details


class GeminiGenerator:
    # Google's Nano Banana image model (needs GEMINI_API_KEY in the environment)
    def __init__(self, model=DEFAULT_MODEL):
        from google import genai          # imported here, so the rest of core works without it
        self.client = genai.Client()
        self.model = model

    def generate(self, prompt, images, aspect_ratio):
        content = [{'type': 'text', 'text': prompt}]
        for img in images:
            ok, png = cv2.imencode('.png', img)
            content.append({'type': 'image', 'data': base64.b64encode(png.tobytes()).decode('utf-8'),
                            'mime_type': 'image/png'})
        try:
            interaction = self.client.interactions.create(
                model=self.model, input=content,
                response_format={'type': 'image', 'aspect_ratio': aspect_ratio, 'image_size': '1K'})
            data = base64.b64decode(interaction.output_image.data)
        except Exception as error:      # network, quota, safety block... (never includes the key)
            raise AiError(f'{type(error).__name__}: {str(error)[:300]}') from error
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise AiError('The AI did not return an image')
        return img
