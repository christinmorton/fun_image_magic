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

from asset_library import STICKERS, load_art, trim_transparent   # noqa: E402
from booth import PhotoStrip                          # noqa: E402
from filters import KERNELS, PRESETS                  # noqa: E402
from look import Look, render                         # noqa: E402
from overlays import fit_frame, paste_centered        # noqa: E402
from slots import BORDER, Slots                       # noqa: E402
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

    def test_gaussian_kernels_blur_sideways_too(self):
        # a 1-pixel vertical white line must spread left and right
        img = np.zeros((20, 20), np.uint8)
        img[:, 10] = 255
        for i in (2, 3):
            with self.subTest(kernel=i):
                self.assertEqual(KERNELS[i].shape[0], KERNELS[i].shape[1])      # square
                self.assertAlmostEqual(float(KERNELS[i].sum()), 1.0, places=5)  # keeps brightness
                self.assertGreater(cv2.filter2D(img, -1, KERNELS[i])[10, 9], 0)

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

    def test_course_sliders_match_the_original_method(self):
        # the course version processed both colour and grey, then picked one
        img = test_photo()
        art = load_art(APP_DIR / 'assets')
        for grayscale in (0, 1):
            look = Look(contrast=2, brightness=60, kernel=1, grayscale=grayscale)
            source = img if grayscale == 0 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            expected = cv2.filter2D(source, -1, KERNELS[1])
            expected = cv2.addWeighted(expected, 2, np.zeros_like(source), 0, 10)
            if grayscale:
                expected = cv2.cvtColor(expected, cv2.COLOR_GRAY2BGR)
            with self.subTest(grayscale=grayscale):
                self.assertTrue(np.array_equal(render(img.copy(), look, art), expected))

    def test_contrast_has_fine_steps(self):
        # 1.1 and 1.2 (slider 11 and 12) must give different, gradually stronger pictures
        img = test_photo()
        art = load_art(APP_DIR / 'assets')
        spread = [float(render(img.copy(), Look(contrast=c), art).std()) for c in (1.0, 1.1, 1.2)]
        self.assertLess(spread[0], spread[1])
        self.assertLess(spread[1], spread[2])

    def test_frame_and_mascot_keep_size(self):
        img = test_photo(960, 639)
        art = load_art(APP_DIR / 'assets')
        for pose in range(len(art.mascots)):
            with self.subTest(pose=pose):
                out = render(img.copy(), Look(frame=0, mascot=pose), art)
                self.assertEqual(out.shape, img.shape)


class TestOverlays(unittest.TestCase):
    def test_paste_clips_at_the_edges(self):
        img = np.zeros((100, 100, 3), np.uint8)
        sticker = np.full((40, 40, 4), 255, np.uint8)
        for cx, cy in [(0, 0), (100, 100), (-30, 50), (500, 500)]:
            paste_centered(img, sticker, cx, cy)   # must not crash
        self.assertEqual(img[0, 0].tolist(), [255, 255, 255])
        self.assertEqual(img[50, 50].tolist(), [0, 0, 0])


class TestFrameFitting(unittest.TestCase):
    def make_frame(self):
        # 200x150 frame: plain blue border with a round gold badge in the bottom-right corner
        frame = np.zeros((150, 200, 4), np.uint8)
        cv2.rectangle(frame, (0, 0), (199, 149), (144, 73, 0, 255), 24)
        cv2.circle(frame, (175, 125), 10, (1, 207, 255, 255), -1)
        return frame

    def badge_size(self, frame):
        gold = np.all(frame[..., :3] == (1, 207, 255), axis=2).astype(np.uint8)
        x, y, w, h = cv2.boundingRect(gold)
        return w, h

    def test_any_size_is_filled_exactly(self):
        for w, h in [(200, 150), (400, 150), (200, 380), (960, 639), (480, 720)]:
            with self.subTest(size=(w, h)):
                self.assertEqual(fit_frame(self.make_frame(), w, h).shape, (h, w, 4))

    def test_badge_keeps_its_shape(self):
        frame = self.make_frame()
        bw, bh = self.badge_size(frame)
        for w, h in [(400, 150), (200, 380)]:     # much wider, much taller
            with self.subTest(size=(w, h)):
                self.assertEqual(self.badge_size(fit_frame(frame, w, h)), (bw, bh))


class TestAssets(unittest.TestCase):
    def test_all_art_loads(self):
        art = load_art(APP_DIR / 'assets')
        self.assertEqual(len(art.mascots), 3)
        for pose in art.mascots:      # trimmed: Cody touches every edge of his image
            alpha = pose[..., 3] >= 16
            self.assertTrue(alpha[0].any() and alpha[-1].any() and alpha[:, 0].any() and alpha[:, -1].any())
        self.assertEqual(len(art.stickers), len(STICKERS))
        self.assertGreater(len(art.frames), 0)
        self.assertGreater(len(art.backgrounds), 0)


    def test_trim_removes_padding(self):
        img = np.zeros((100, 120, 4), np.uint8)
        img[30:60, 40:90] = 255          # visible art
        img[5, 5, 3] = 3                 # a faint speck that should not count
        self.assertEqual(trim_transparent(img).shape, (30, 50, 4))


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


class FakeTracker:
    # stands in for MediaPipe: no faces, no person
    def analyse_still(self, img):
        return [], None


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.art = load_art(APP_DIR / 'assets')
        self.slots = Slots()

    def test_each_slot_keeps_its_own_look(self):
        look = Look(preset=1)
        self.slots.put(0, test_photo(), look, FakeTracker())
        self.slots.put(1, test_photo(), look, FakeTracker())
        self.slots.slots[0].look.preset = 2           # edit slot 1 only
        self.assertEqual(self.slots.slots[1].look.preset, 1)
        self.assertEqual(look.preset, 1)               # the camera's look is untouched too

    def test_picture_is_cached_until_the_look_changes(self):
        self.slots.put(0, test_photo(), Look(), FakeTracker())
        slot = self.slots.slots[0]
        first = slot.picture(self.art)
        self.assertIs(slot.picture(self.art), first)
        slot.look.preset = 2
        self.assertIsNot(slot.picture(self.art), first)

    def test_layout_sizes(self):
        self.slots.put(0, test_photo(), Look(), FakeTracker())
        self.slots.put(2, test_photo(960, 640), Look(), FakeTracker())   # a different size is fitted in
        cell_w, cell_h = 640 + 2 * BORDER, 480 + 2 * BORDER
        grid, rects = self.slots.compose(self.art, 'Grid')
        self.assertEqual(grid.shape, (2 * cell_h, 2 * cell_w, 3))
        self.assertEqual(rects[3], (cell_w, cell_h, cell_w, cell_h))
        strip, _ = self.slots.compose(self.art, 'Strip')
        self.assertEqual(strip.shape, (4 * cell_h, cell_w, 3))           # empty slots shown on screen
        saved, _ = self.slots.compose(self.art, 'Strip', for_saving=True)
        self.assertEqual(saved.shape, (2 * cell_h, cell_w, 3))           # ... but left out when saving

    def test_nothing_to_save_when_empty(self):
        self.assertFalse(self.slots.any_filled())
        self.assertIsNone(self.slots.compose(self.art, 'Strip', for_saving=True)[0])


if __name__ == '__main__':
    unittest.main()
