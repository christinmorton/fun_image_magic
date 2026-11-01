# Checks for the AI presets and the "keep the person" logic, using fake generators (no
# internet, no API key, no cost). Run:  .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ai import (AI_PRESETS, AI_PRESETS_BY_KEY, closest_aspect_ratio,   # noqa: E402
                     mask_overlap, run_ai_preset)


def photo(w=640, h=480):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (40, 160, 40)                       # green background
    img[100:400, 240:400] = (200, 150, 120)      # the "person"
    return img

def person_mask(img_shape, x0=240, x1=400):
    mask = np.zeros(img_shape[:2], np.float32)
    mask[100:400, x0:x1] = 1.0
    return mask


class FakeGenerator:
    # returns a solid image of a different size, like the model's 1K output
    def __init__(self, color=(10, 20, 200), size=(1200, 896)):
        self.color, self.size, self.calls = color, size, []

    def generate(self, prompt, images, aspect_ratio):
        self.calls.append((prompt, len(images), aspect_ratio))
        out = np.zeros((self.size[1], self.size[0], 3), np.uint8)
        out[:] = self.color
        return out


class TestAiPresets(unittest.TestCase):
    def test_presets_are_well_formed(self):
        self.assertEqual(len(AI_PRESETS_BY_KEY), len(AI_PRESETS))                  # unique keys
        for preset in AI_PRESETS:
            self.assertIn(preset.kind, ('style', 'background'))
            self.assertIn('Do not add any text', preset.prompt)
            if preset.kind == 'background':
                self.assertIn('position in the frame', preset.prompt)              # helps alignment

    def test_closest_aspect_ratio(self):
        self.assertEqual(closest_aspect_ratio(640, 480), '4:3')
        self.assertEqual(closest_aspect_ratio(480, 640), '3:4')
        self.assertEqual(closest_aspect_ratio(1920, 1080), '16:9')
        self.assertEqual(closest_aspect_ratio(500, 500), '1:1')

    def test_mask_overlap(self):
        a = person_mask((480, 640))
        self.assertEqual(mask_overlap(a, a), 1.0)
        self.assertEqual(mask_overlap(a, person_mask((480, 640), 0, 100)), 0.0)
        self.assertEqual(mask_overlap(np.zeros((4, 4)), np.zeros((4, 4))), 0.0)


class TestRunAiPreset(unittest.TestCase):
    def test_style_returns_the_photo_size(self):
        generator = FakeGenerator()
        out, details = run_ai_preset(photo(), AI_PRESETS_BY_KEY['comic'], generator)
        self.assertEqual(out.shape, (480, 640, 3))
        self.assertEqual(details, {'person_kept': False, 'overlap': None})
        self.assertEqual(generator.calls[0][1:], (1, '4:3'))                        # one photo, 4:3

    def test_background_keeps_the_person_when_aligned(self):
        img = photo()
        # the AI kept the person in place: the same mask is found in its output
        out, details = run_ai_preset(img, AI_PRESETS_BY_KEY['vegas_strip'], FakeGenerator(),
                                     find_person=lambda image: person_mask(image.shape))
        self.assertTrue(details['person_kept'])
        self.assertEqual(details['overlap'], 1.0)
        self.assertTrue(np.array_equal(out[250, 320], img[250, 320]))              # original person
        self.assertTrue(np.array_equal(out[20, 20], [10, 20, 200]))                # AI background

    def test_background_reframed_uses_the_ai_image(self):
        img = photo()
        # the AI moved the person: their mask in the output is somewhere else
        masks = iter([person_mask(img.shape), person_mask(img.shape, 0, 160)])
        out, details = run_ai_preset(img, AI_PRESETS_BY_KEY['vegas_strip'], FakeGenerator(),
                                     find_person=lambda image: next(masks))
        self.assertFalse(details['person_kept'])
        self.assertEqual(details['overlap'], 0.0)
        self.assertTrue(np.array_equal(out[250, 320], [10, 20, 200]))              # no ghost paste

    def test_stages_are_reported(self):
        stages = []
        run_ai_preset(photo(), AI_PRESETS_BY_KEY['comic'], FakeGenerator(), on_stage=stages.append)
        self.assertEqual(stages, ['generating'])
        stages.clear()
        run_ai_preset(photo(), AI_PRESETS_BY_KEY['red_rock'], FakeGenerator(),
                      find_person=lambda image: None, on_stage=stages.append)
        self.assertEqual(stages, ['generating', 'checking_person'])

    def test_background_without_a_person(self):
        out, details = run_ai_preset(photo(), AI_PRESETS_BY_KEY['outer_space'], FakeGenerator(),
                                     find_person=lambda image: None)
        self.assertEqual(details, {'person_kept': False, 'overlap': None})


if __name__ == '__main__':
    unittest.main()
