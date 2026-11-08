# Checks for the cover layouts (no AI, windows or webcam needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import (LAYOUTS, PIECES, STICKERS, CoverWords, apply_lettering, arch,   # noqa: E402
                               draw_cover_lettering, recede)
from core.lettering import TREATMENTS                                                 # noqa: E402

SIZE = 400         # small covers, so the tests stay quick
WORDS = CoverWords(name='BIG MIKE', title='BOSS LIFE', presents='Big Tee presents',
                   featuring=('Lil Ray', 'Dre', 'Mama Jo', 'Smoke'))


def ink(layer, top, bottom):
    # how much of a band of the cover (fractions of its height) has lettering in it
    h = layer.shape[0]
    return (layer[int(top * h):int(bottom * h), :, 3] > 128).mean()


class TestLayouts(unittest.TestCase):
    def test_every_layout_is_complete(self):
        for key, layout in LAYOUTS.items():
            with self.subTest(layout=key):
                self.assertIn('name', layout.spots)
                self.assertIn('title', layout.spots)
                self.assertTrue(set(layout.spots) <= set(PIECES))
                self.assertTrue(set(layout.styles.values()) <= set(TREATMENTS))
                for spot in layout.spots.values():
                    self.assertTrue(0 <= spot.x and spot.x + spot.w <= 1 and 0 <= spot.y and spot.y + spot.h <= 1)

    def test_name_on_top_title_at_the_bottom_middle_left_for_the_picture(self):
        for key in LAYOUTS:
            with self.subTest(layout=key):
                layer = draw_cover_lettering(WORDS, key, SIZE)
                self.assertEqual(layer.shape, (SIZE, SIZE, 4))
                self.assertGreater(ink(layer, 0, 0.22), 0.1)       # the name
                self.assertGreater(ink(layer, 0.8, 1), 0.1)        # the title
                centre = layer[int(SIZE * 0.4):int(SIZE * 0.6), int(SIZE * 0.35):int(SIZE * 0.65), 3]
                self.assertLess((centre > 128).mean(), 0.05)       # the person's face stays clear

    def test_empty_pieces_are_left_out(self):
        bare = draw_cover_lettering(CoverWords(name='BIG MIKE', sticker=()), 'hero', SIZE)
        full = draw_cover_lettering(WORDS, 'hero', SIZE)
        self.assertEqual(ink(bare, 0.8, 1), 0)                     # no title
        self.assertLess((bare[..., 3] > 128).mean(), (full[..., 3] > 128).mean())

    def test_a_long_name_shrinks_to_fit(self):
        layer = draw_cover_lettering(CoverWords(name='THE INCREDIBLE MIKE JOHNSON JR', sticker=()), 'hero', SIZE)
        self.assertGreater(ink(layer, 0, 0.22), 0.05)
        self.assertEqual(ink(layer, 0.3, 1), 0)                    # nothing spilled below its box

    def test_a_short_title_sits_centred_in_its_box(self):
        # the plain serif style has no sparkles, so its solid ink is just the letters
        for key, layout in LAYOUTS.items():
            with self.subTest(layout=key):
                layer = draw_cover_lettering(CoverWords(name='', title='RICH', sticker=()), key, SIZE,
                                             styles={'title': 'serif'})
                ys, xs = np.where(layer[..., 3] > 128)
                s = layout.spots['title']
                left, top, right, bottom = s.x * SIZE, s.y * SIZE, (s.x + s.w) * SIZE, (s.y + s.h) * SIZE
                self.assertGreaterEqual(ys.min(), top - 2)
                self.assertLessEqual(ys.max(), bottom + 2)
                self.assertLess(abs((ys.min() + ys.max()) / 2 - (top + bottom) / 2), 3)     # centred up and down
                self.assertLess(abs((xs.min() + xs.max()) / 2 - (left + right) / 2), 3)     # and across

    def test_every_layout_labels_its_featuring_list(self):
        for key, layout in LAYOUTS.items():
            with self.subTest(layout=key):
                self.assertTrue(layout.heading)
                layer = draw_cover_lettering(CoverWords(name='', featuring=('Dre', 'Mama Jo'), sticker=()), key, SIZE)
                b, g, r = (layer[..., i].astype(int) for i in range(3))
                yellow = (layer[..., 3] > 200) & (r > 200) & (g > 170) & (b < 140)   # the brush-lettered label
                self.assertGreater(yellow.sum(), 5)

    def test_a_finish_on_one_part_leaves_the_others_alone(self):
        clean = draw_cover_lettering(WORDS, 'hero', SIZE, seed=1)
        title_aged = draw_cover_lettering(WORDS, 'hero', SIZE, seed=1, finishes={'title': 'vhs'})
        top, bottom = slice(0, int(SIZE * 0.22)), slice(int(SIZE * 0.8), SIZE)
        self.assertTrue(np.array_equal(clean[top], title_aged[top]))          # the name is untouched
        self.assertFalse(np.array_equal(clean[bottom], title_aged[bottom]))   # the title is aged

    def test_every_sticker_fits_its_box(self):
        spot = LAYOUTS['hero'].spots['sticker']
        for _, lines, look in STICKERS[1:]:
            with self.subTest(sticker=look):
                layer = draw_cover_lettering(CoverWords(name='', sticker=lines), 'hero', SIZE, styles={'sticker': look})
                ys, xs = np.where(layer[..., 3] > 40)
                self.assertGreater(len(xs), 0)
                self.assertGreaterEqual(xs.min(), spot.x * SIZE - 2)
                self.assertLessEqual(xs.max(), (spot.x + spot.w) * SIZE + 2)
                self.assertGreaterEqual(ys.min(), spot.y * SIZE - 2)
                self.assertLessEqual(ys.max(), (spot.y + spot.h) * SIZE + 2)

    def test_styles_can_be_swapped(self):
        gold = draw_cover_lettering(WORDS, 'hero', SIZE)
        chrome = draw_cover_lettering(WORDS, 'hero', SIZE, styles={'name': 'chrome'})
        self.assertFalse(np.array_equal(gold, chrome))

    def test_apply_lettering_over_a_picture(self):
        layer = draw_cover_lettering(WORDS, 'crew_row', SIZE)
        picture = np.full((SIZE * 2, SIZE * 2, 3), 90, np.uint8)      # resized to fit
        cover = apply_lettering(picture, layer)
        self.assertEqual(cover.shape, (SIZE, SIZE, 3))
        self.assertTrue((cover[SIZE // 2, SIZE // 2] == 90).all())    # the middle is still the picture


class TestWarps(unittest.TestCase):
    def test_arch_and_recede(self):
        img = np.zeros((50, 200, 4), np.uint8)
        img[20:30, :, :] = 255                                      # a flat bar
        up, down = arch(img, 0.5), arch(img, -0.5)
        self.assertEqual(up.shape[0], 75)
        middle, edge = up[:, 100, 3], up[:, 2, 3]
        self.assertLess(np.argmax(middle), np.argmax(edge))         # bowed up: the middle is higher
        self.assertGreater(np.argmax(down[:, 100, 3]), np.argmax(down[:, 2, 3]))
        block = np.full((50, 200, 4), 255, np.uint8)
        tilted = recede(block, 0.4)
        self.assertEqual(tilted.shape, block.shape)
        self.assertGreater(tilted[47, 3, 3], 200)                   # the bottom keeps its full width
        self.assertEqual(tilted[0, 2, 3], 0)                        # the top corners are pulled in
        self.assertEqual(tilted[0, 100, 3], 255)


if __name__ == '__main__':
    unittest.main()
