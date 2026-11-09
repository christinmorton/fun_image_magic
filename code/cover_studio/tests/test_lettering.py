# Checks for the lettering engine (no AI, windows or webcam needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.lettering import (FONTS, FONTS_DIR, TREATMENTS, draw_words, even_lines,   # noqa: E402
                            featuring_list, load_font, plain, sticker, text_mask)

SIZE = 60          # small, so the tests stay quick
CREW = ['Lil Ray', 'Big Tee', 'Dre', 'Mama Jo', 'Cousin Pookie', 'Lady K', 'Smoke', 'Uncle Ray', 'Nita']


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


class TestSupportingText(unittest.TestCase):
    def test_featuring_list_fills_its_box(self):
        for w, h in [(300, 260), (700, 50)]:            # a column, and a single strip
            with self.subTest(box=(w, h)):
                img = featuring_list(CREW, w, h)
                self.assertEqual(img.shape, (h, w, 4))
                self.assertGreater(img[..., 3].max(), 200)
        with self.assertRaises(ValueError):
            featuring_list(['  ', ''], 300, 200)

    def test_featuring_label_beside_the_names(self):
        img = featuring_list(CREW, 700, 50, 'Feat.', inline=True)
        b, g, r = (img[..., i].astype(int) for i in range(3))
        solid = img[..., 3] > 200
        label = np.where(solid & (r > 200) & (g > 170) & (b < 140))[1]           # yellow
        names = np.where(solid & (r > 230) & (g > 230) & (b > 230))[1]           # white
        self.assertGreater(len(label), 0)
        self.assertLess(label.max(), names.min())                                # the label comes first

    def test_even_lines_keep_every_name_and_avoid_a_lone_one(self):
        font = load_font('narrow', 30)
        lines = even_lines([n.upper() for n in CREW], font, 3, 10000)
        self.assertEqual(len(lines), 3)
        self.assertEqual(' '.join(lines).replace(',', '').split(), ' '.join(CREW).upper().split())
        widths = [font.getlength(line) for line in lines]
        self.assertLess(max(widths) / min(widths), 1.6)      # no line far shorter than the rest
        self.assertIsNone(even_lines(['A VERY LONG NAME INDEED'], font, 1, 50))   # can't fit

    def test_sticker_uses_its_own_wording(self):
        two, three = sticker(('CERTIFIED', 'HOOD CLASSIC'), 120), sticker(('ONE', 'TWO', 'THREE'), 120)
        self.assertEqual((two.shape[0], three.shape[0]), (120, 120))
        self.assertEqual(two[60, two.shape[1] // 2, 3], 255)     # a solid box, not see-through
        with self.assertRaises(ValueError):
            sticker((' ',), 120)
        with self.assertRaises(ValueError):
            sticker(('PARENTAL', 'ADVISORY'), 120, style='riaa')

    def test_a_tiny_sticker_still_works(self):
        for style in ('badge', 'stamp', 'hazard'):
            with self.subTest(style=style):
                tiny = sticker(('CERTIFIED', 'HOOD CLASSIC'), 12, style)
                self.assertLessEqual(tiny.shape[0], 18)                  # about the size asked for (the stamp tilts)
                self.assertGreater(tiny[..., 3].max(), 0)

    def test_sticker_styles(self):
        badge = sticker(('CERTIFIED', 'HOOD CLASSIC'), 120, 'badge')
        # the gold border runs along the straight edges too, not only round the corners
        b, g, r = badge[3, badge.shape[1] // 2, :3].astype(int)
        self.assertTrue(r > 180 and g > 140 and b < 90, (b, g, r))
        hazard = sticker(('WARNING', 'TOO HOT'), 120, 'hazard')
        edge = hazard[6, 20:-20, :3].astype(int).sum(axis=1)
        self.assertTrue(edge.min() < 120 and edge.max() > 400)   # black and yellow stripes along the top
        stamp = sticker(('STREET', 'CERTIFIED'), 120, 'stamp', seed=1)
        self.assertGreater(stamp.shape[0], 120)                  # tilted, so taller than its box
        self.assertLess(stamp[..., 3].mean(), badge[..., 3].mean())   # ink only, no filled box

    def test_plain_text(self):
        img = plain('BIG TEE PRESENTS', 'serif', 40)
        self.assertEqual(img.shape[2], 4)
        self.assertEqual(img[..., 3].max(), 255)


class TestFonts(unittest.TestCase):
    def test_every_font_is_there_with_its_licence(self):
        for name, file in FONTS.items():
            with self.subTest(font=name):
                self.assertTrue((FONTS_DIR / file).is_file())
                family = file.split('-')[0]
                self.assertTrue(list(FONTS_DIR.glob(f'{family}-*.txt')), f'no licence for {file}')


if __name__ == '__main__':
    unittest.main()
