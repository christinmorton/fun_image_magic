# Checks for the aged finishes (no AI or windows needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.finish import FINISHES, age                  # noqa: E402
from core.lettering import draw_words                  # noqa: E402


def picture(w=320, h=240):
    x = np.linspace(0, 255, w, dtype=np.uint8)[None, :]
    return np.dstack([np.repeat(x, h, 0), np.full((h, w), 90, np.uint8), np.full((h, w), 200, np.uint8)])


class TestFinish(unittest.TestCase):
    def test_every_finish_keeps_size_and_type(self):
        layer = draw_words('GOLD', 'gold', 50)
        for finish in FINISHES:
            for img in (picture(), layer):
                with self.subTest(finish=finish, channels=img.shape[2]):
                    out = age(img, finish, seed=1)
                    self.assertEqual((out.shape, out.dtype), (img.shape, np.uint8))

    def test_clean_changes_nothing_and_the_others_do(self):
        img = picture()
        self.assertTrue(np.array_equal(age(img, 'clean'), img))
        self.assertTrue(np.array_equal(age(img, 'print', strength=0), img))
        for finish in ('print', 'vhs'):
            self.assertGreater(np.abs(age(img, finish, seed=1).astype(int) - img).mean(), 2)

    def test_same_seed_same_result(self):
        img = picture()
        for finish in ('print', 'vhs'):
            self.assertTrue(np.array_equal(age(img, finish, seed=5), age(img, finish, seed=5)))
            self.assertFalse(np.array_equal(age(img, finish, seed=5), age(img, finish, seed=6)))

    def test_print_fades_the_blacks(self):
        black = np.zeros((200, 200, 3), np.uint8)
        self.assertGreater(age(black, 'print', seed=1).mean(), 8)          # no true black left

    def test_vhs_has_scan_lines(self):
        grey = np.full((200, 200, 3), 160, np.uint8)
        rows = age(grey, 'vhs', seed=1)[:150].mean(axis=(1, 2))           # above the tracking noise
        self.assertGreater(np.abs(np.diff(rows)).mean(), 8)                # rows alternate light and dark

    def test_layers_stay_see_through_around_the_words(self):
        aged = age(draw_words('GOLD', 'gold', 50), 'print', seed=1)
        self.assertLess(aged[0, 0, 3], 10)
        self.assertGreater(aged[..., 3].max(), 200)

    def test_parts_age_at_the_covers_scale(self):
        # a small part of a big cover gets the big cover's grain, not grain for its own size
        part = picture(200, 100)
        self.assertFalse(np.array_equal(age(part, 'vhs', seed=1), age(part, 'vhs', seed=1, unit_size=3600)))

    def test_unknown_finish(self):
        with self.assertRaises(ValueError):
            age(picture(), 'sepia')


if __name__ == '__main__':
    unittest.main()
