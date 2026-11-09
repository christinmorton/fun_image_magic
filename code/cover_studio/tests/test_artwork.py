# Checks for making artwork and logging what it costs. A fake generator stands in for the
# image AI, so nothing here calls Google or costs money. Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.ai import AiError                                                       # noqa: E402
from core.artwork import (FINAL_PROMPT, ArtworkRequest, make_final, make_previews,   # noqa: E402
                          preview_cost, save_final, save_previews)
from core.spending import PRICES, OverLimit, Spending                             # noqa: E402

PICTURES = {key: np.full((60, 80, 3), value, np.uint8) for key, value in [('right', 200), ('front', 40), ('left', 120)]}


class FakeGenerator:
    # remembers every request; returns a grey square, or fails every `fail_every`-th call
    def __init__(self, fail_every=0):
        self.calls, self.fail_every = [], fail_every
        self.lock = threading.Lock()

    def generate(self, prompt, images, aspect_ratio, image_size='1K'):
        with self.lock:
            self.calls.append((prompt, [int(i[0, 0, 0]) for i in images], aspect_ratio, image_size))
            n = len(self.calls)
        if self.fail_every and n % self.fail_every == 0:
            raise AiError('SafetyBlock: try another scene')
        return np.full((64, 64, 3), 99, np.uint8)


class TestArtwork(unittest.TestCase):
    def spending(self, tmp, limit=2.0):
        return Spending(Path(tmp) / 'spending.json', limit=limit)

    def test_previews_send_every_angle_front_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator, spending = FakeGenerator(), self.spending(tmp)
            request = ArtworkRequest(scene='boss_office', jewellery=('rope_chain',))
            results = make_previews(PICTURES, request, generator, spending)
            self.assertEqual(len(results), 4)
            self.assertTrue(all(image is not None and error is None for image, error in results))
            prompt, sent, ratio, size = generator.calls[0]
            self.assertEqual((sent, ratio, size), ([40, 120, 200], '1:1', '1K'))     # front, left, right
            self.assertIn('gold rope chain', prompt)
            self.assertIn('3 reference photos', prompt)
            self.assertAlmostEqual(spending.spent_today(), preview_cost(4))

    def test_failures_are_reported_and_not_charged(self):
        with tempfile.TemporaryDirectory() as tmp:
            spending = self.spending(tmp)
            results = make_previews(PICTURES, ArtworkRequest(), FakeGenerator(fail_every=2), spending)
            errors = [error for _, error in results if error]
            self.assertEqual(len(errors), 2)
            self.assertIn('SafetyBlock', errors[0])
            self.assertAlmostEqual(spending.spent_today(), 2 * PRICES['1K'])

    def test_over_the_limit_nothing_is_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator()
            with self.assertRaises(OverLimit):
                make_previews(PICTURES, ArtworkRequest(), generator, self.spending(tmp, limit=0.10))
            self.assertEqual(generator.calls, [])

    def test_banned_words_send_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator = FakeGenerator()
            request = ArtworkRequest(details='A Rolex on each wrist.')
            with self.assertRaises(ValueError):
                make_previews(PICTURES, request, generator, self.spending(tmp))
            self.assertEqual(generator.calls, [])
            custom = ArtworkRequest(scene='custom', custom_scene='On a speedboat at sunset.', details='Purple lights.')
            make_previews(PICTURES, custom, generator, self.spending(tmp))
            self.assertIn('speedboat', generator.calls[0][0])
            self.assertIn('Purple lights', generator.calls[0][0])

    def test_final_is_the_preview_made_bigger(self):
        with tempfile.TemporaryDirectory() as tmp:
            generator, spending = FakeGenerator(), self.spending(tmp)
            preview = np.full((64, 64, 3), 7, np.uint8)
            image, error = make_final(PICTURES, preview, generator, spending, size='2K')
            self.assertIsNone(error)
            prompt, sent, _, size = generator.calls[0]
            self.assertEqual((prompt, sent, size), (FINAL_PROMPT, [7, 40, 120, 200], '2K'))   # the preview first
            self.assertAlmostEqual(spending.spent_today(), PRICES['2K'])

    def test_saving_a_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = Path(tmp) / 'big-mike'
            subject.mkdir()
            request = ArtworkRequest(scene='inferno', clothing='camo')
            results = [(np.zeros((8, 8, 3), np.uint8), None), (None, 'SafetyBlock')]
            folder = save_previews(subject, request, results, references=3)
            self.assertTrue((folder / 'preview_1.png').exists())
            self.assertFalse((folder / 'preview_2.png').exists())
            info = json.loads((folder / 'request.json').read_text(encoding='utf-8'))
            self.assertEqual((info['request']['clothing'], info['previews'][1]['error']), ('camo', 'SafetyBlock'))
            self.assertIn('camouflage', info['prompt'])
            self.assertTrue(save_final(folder, 1, '2K', np.zeros((8, 8, 3), np.uint8)).exists())
            self.assertNotEqual(save_previews(subject, request, results, 3), folder)    # never overwrites


if __name__ == '__main__':
    unittest.main()
