# Checks for the lettering engine (no AI, windows or webcam needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.lettering import FONTS, FONTS_DIR, TREATMENTS, draw_words, text_mask   # noqa: E402

SIZE = 60          # small, so the tests stay quick


class TestTreatments(unittest.TestCase):
    def test_every_treatment_is_transparent_words(self):
        for name in TREATMENTS:
            with self.subTest(treatment=name):
                img = draw_words('BIG MIKE', name, SIZE)
                self.assertEqual((img.ndim, img.shape[2], img.dtype), (3, 4, np.uint8))
                alpha = img[..., 3]
                self.assertEqual(alpha.max(), 255)                      # solid ink somewhere
                self.assertLess(max(alpha[0, 0], alpha[0, -1], alpha[-1, 0], alpha[-1, -1]), 10)   # clear corners
                self.assertGreater((alpha > 128).mean(), 0.1)           # the words fill a fair part of it

    def test_same_seed_same_picture(self):
        for name in TREATMENTS:
            with self.subTest(treatment=name):
                self.assertTrue(np.array_equal(draw_words('ICE', name, SIZE, seed=3),
                                               draw_words('ICE', name, SIZE, seed=3)))
        # the random parts (here, the gems) change with the seed
        self.assertFalse(np.array_equal(draw_words('ICE', 'ice', SIZE, seed=1), draw_words('ICE', 'ice', SIZE, seed=2)))

    def test_size_and_length(self):
        small, big = draw_words('GOLD', 'gold', 40), draw_words('GOLD', 'gold', 80)
        self.assertAlmostEqual(big.shape[0] / small.shape[0], 2, delta=0.15)     # height follows the size
        self.assertGreater(draw_words('GOLD CHAINS', 'gold', 40).shape[1], small.shape[1])

    def test_spelling_is_kept_exactly(self):
        # the mask is the font's own letters, so different words give different shapes
        self.assertFalse(np.array_equal(text_mask('MIKE', 'slab', SIZE, 0), text_mask('MIKF', 'slab', SIZE, 0)))

    def test_bad_requests(self):
        with self.assertRaises(ValueError):
            draw_words('   ', 'gold', SIZE)
        with self.assertRaises(ValueError):
            draw_words('BIG MIKE', 'neon', SIZE)


class TestFonts(unittest.TestCase):
    def test_every_font_is_there_with_its_licence(self):
        for name, file in FONTS.items():
            with self.subTest(font=name):
                self.assertTrue((FONTS_DIR / file).is_file())
                family = file.split('-')[0]
                self.assertTrue(list(FONTS_DIR.glob(f'{family}-*.txt')), f'no licence for {file}')


if __name__ == '__main__':
    unittest.main()
