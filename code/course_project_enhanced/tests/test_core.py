# Quick checks for the picture code (no webcam or windows needed).
# Run from the course_project_enhanced folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from asset_library import STICKERS, load_art          # noqa: E402
from booth import PhotoStrip                          # noqa: E402
from filters import KERNELS, PRESETS                  # noqa: E402
from look import Look, render                         # noqa: E402
from overlays import paste_centered                   # noqa: E402
from sources import MAX_IMAGE_H, MAX_IMAGE_W, load_image   # noqa: E402


def test_photo(w=640, h=480):
    # a colourful gradient, so effects have something to work on
    x = np.linspace(0, 255, w, dtype=np.uint8)[None, :]
    y = np.linspace(0, 255, h, dtype=np.uint8)[:, None]
    return cv2.merge([np.repeat(x, h, 0), np.repeat(y, w, 1), np.full((h, w), 128, np.uint8)])


class TestPresets(unittest.TestCase):
    def test_every_preset_keeps_size_and_type(self):
        for w, h in [(640, 480), (333, 251)]:      # also an odd size
            img = test_photo(w, h)
            for name, effect in PRESETS:
                with self.subTest(preset=name, size=(w, h)):
                    out = effect(img.copy())
                    self.assertEqual(out.shape, img.shape)
                    self.assertEqual(out.dtype, np.uint8)

    def test_every_kernel_keeps_size(self):
        img = test_photo()
        for i, kernel in enumerate(KERNELS):
            with self.subTest(kernel=i):
                self.assertEqual(cv2.filter2D(img, -1, kernel).shape, img.shape)


class TestRender(unittest.TestCase):
    def test_default_look_changes_nothing(self):
        img = test_photo()
        art = load_art(APP_DIR / 'assets')
        self.assertTrue(np.array_equal(render(img.copy(), Look(), art), img))

    def test_frame_and_mascot_keep_size(self):
        img = test_photo(960, 639)
        art = load_art(APP_DIR / 'assets')
        out = render(img, Look(frame=0, mascot=True), art)
        self.assertEqual(out.shape, img.shape)


class TestOverlays(unittest.TestCase):
    def test_paste_clips_at_the_edges(self):
        img = np.zeros((100, 100, 3), np.uint8)
        sticker = np.full((40, 40, 4), 255, np.uint8)
        for cx, cy in [(0, 0), (100, 100), (-30, 50), (500, 500)]:
            paste_centered(img, sticker, cx, cy)   # must not crash
        self.assertEqual(img[0, 0].tolist(), [255, 255, 255])
        self.assertEqual(img[50, 50].tolist(), [0, 0, 0])


class TestAssets(unittest.TestCase):
    def test_all_art_loads(self):
        art = load_art(APP_DIR / 'assets')
        self.assertIsNotNone(art.mascot)
        self.assertEqual(len(art.stickers), len(STICKERS))
        self.assertGreater(len(art.frames), 0)
        self.assertGreater(len(art.backgrounds), 0)


class TestSources(unittest.TestCase):
    def test_load_image_shrinks_big_photos_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            big, small = Path(tmp) / 'big.png', Path(tmp) / 'small.png'
            cv2.imwrite(str(big), test_photo(2000, 1000))
            cv2.imwrite(str(small), test_photo(300, 200))
            h, w = load_image(str(big)).shape[:2]
            self.assertTrue(w <= MAX_IMAGE_W and h <= MAX_IMAGE_H)
            self.assertEqual(load_image(str(small)).shape[:2], (200, 300))
            self.assertIsNone(load_image(str(Path(tmp) / 'missing.png')))


class TestPhotoStrip(unittest.TestCase):
    def test_four_shots_make_a_strip(self):
        strip, img = PhotoStrip(), test_photo(100, 80)
        strip.start(now=0)
        self.assertEqual(strip.update(img, now=0.5), (3, None))   # counting down
        finished = None
        for t in [3, 6, 9, 12]:
            _, finished = strip.update(img, now=t)
        self.assertEqual(finished.shape, (4 * (80 + 24), 100 + 24, 3))
        self.assertFalse(strip.shooting)


if __name__ == '__main__':
    unittest.main()
