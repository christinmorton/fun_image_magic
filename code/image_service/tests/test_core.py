# Quick checks for the picture code (no webcam or windows needed).
# Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import os
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core import ASSETS_DIR                                       # noqa: E402
from core.asset_library import STICKERS, load_art, trim_transparent   # noqa: E402
from core.env_file import load_env                                # noqa: E402
from core.filters import KERNELS, PRESETS                         # noqa: E402
from core.look import Look, render                                # noqa: E402
from core.masks import FOCUS_MODES, apply_focus, refine_mask      # noqa: E402
from core.overlays import fit_frame, paste_centered               # noqa: E402
from core.props import (MAX_SIZE, add_prop, bring_to_front, move_prop, prop_at,   # noqa: E402
                        remove_prop, resize_prop)
from core.slots import BORDER, Slots                              # noqa: E402
from desktop.booth import PhotoStrip                              # noqa: E402
from desktop.sources import MAX_IMAGE_H, MAX_IMAGE_W, load_image  # noqa: E402


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
        art = load_art(ASSETS_DIR)
        self.assertTrue(np.array_equal(render(img.copy(), Look(), art), img))

    def test_course_sliders_match_the_original_method(self):
        # the course version processed both colour and grey, then picked one
        img = test_photo()
        art = load_art(ASSETS_DIR)
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
        art = load_art(ASSETS_DIR)
        spread = [float(render(img.copy(), Look(contrast=c), art).std()) for c in (1.0, 1.1, 1.2)]
        self.assertLess(spread[0], spread[1])
        self.assertLess(spread[1], spread[2])

    def test_frame_and_mascot_keep_size(self):
        img = test_photo(960, 639)
        art = load_art(ASSETS_DIR)
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
        art = load_art(ASSETS_DIR)
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


class TestEnvFile(unittest.TestCase):
    def test_reads_keys_but_keeps_existing_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '.env'
            path.write_text('# a comment\nTEST_KEY_A=abc123\nTEST_KEY_B="quoted"\nTEST_KEY_EMPTY=\n'
                            'TEST_KEY_SET=from-file\n', encoding='utf-8')
            os.environ['TEST_KEY_SET'] = 'already-set'
            try:
                loaded = load_env(path)
                self.assertEqual(sorted(loaded), ['TEST_KEY_A', 'TEST_KEY_B'])
                self.assertEqual(os.environ['TEST_KEY_A'], 'abc123')
                self.assertEqual(os.environ['TEST_KEY_B'], 'quoted')
                self.assertEqual(os.environ['TEST_KEY_SET'], 'already-set')   # not overwritten
                self.assertEqual(load_env(Path(tmp) / 'missing.env'), [])    # no file is fine
            finally:
                for name in ('TEST_KEY_A', 'TEST_KEY_B', 'TEST_KEY_SET'):
                    os.environ.pop(name, None)


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


class TestMasks(unittest.TestCase):
    def raw_mask(self):
        # a soft "person" block in the middle, plus a stray speck the model got wrong
        mask = np.zeros((480, 640, 1), np.float32)
        mask[100:400, 200:440] = 0.9
        mask[20:23, 20:23] = 0.9
        return cv2.GaussianBlur(mask, (0, 0), 6)[..., None]

    def test_refine_mask_cleans_up(self):
        refined = refine_mask(self.raw_mask(), test_photo())
        self.assertEqual(refined.shape, (480, 640))
        self.assertTrue(0 <= refined.min() and refined.max() <= 1)
        self.assertAlmostEqual(float(refined[250, 320]), 1.0, places=3)   # firm inside the person
        self.assertLess(float(refined[21, 21]), 0.05)                      # speck removed
        raw = np.squeeze(self.raw_mask())
        soft = lambda m: int(((m > 0.05) & (m < 0.95)).sum())
        self.assertLess(soft(refined), soft(raw))                         # narrower soft edge

    def test_focus_modes(self):
        img = test_photo()
        mask = refine_mask(self.raw_mask(), img)
        for mode, name in enumerate(FOCUS_MODES):
            with self.subTest(mode=name):
                out = apply_focus(img.copy(), mode, mask)
                self.assertEqual((out.shape, out.dtype), (img.shape, np.uint8))
        popped = apply_focus(img, 1, mask)                                 # color pop
        b, g, r = popped[20, 600].tolist()
        self.assertTrue(b == g == r)                                       # background turned grey
        self.assertEqual(popped[250, 320].tolist(), img[250, 320].tolist())   # person unchanged

    def test_focus_off_needs_no_mask(self):
        art = load_art(ASSETS_DIR)
        self.assertFalse(Look().needs_person_mask())
        self.assertTrue(Look(focus=2).needs_person_mask())
        img = test_photo()
        # no mask available (e.g. MediaPipe found nothing): focus is skipped, not a crash
        self.assertTrue(np.array_equal(render(img.copy(), Look(focus=1), art, person_mask=None), img))


class TestProps(unittest.TestCase):
    def setUp(self):
        # one 100x200 prop: solid in the middle, see-through in the top-left corner
        self.prop = np.full((200, 100, 4), 255, np.uint8)
        self.prop[:40, :30, 3] = 0
        self.images = [self.prop]

    def test_add_move_resize_remove(self):
        props = add_prop((), 0, size=0.5)
        self.assertEqual((props[0].x, props[0].y, props[0].size), (0.5, 0.5, 0.5))
        props = move_prop(props, 0, 1.4, -0.2)                       # dragged off the photo
        self.assertEqual((props[0].x, props[0].y), (1.0, 0.0))       # centre kept on the photo
        for _ in range(50):
            props = resize_prop(props, 0, 1.1)
        self.assertEqual(props[0].size, MAX_SIZE)                    # size has limits
        self.assertEqual(remove_prop(props, 0), ())

    def test_click_finds_the_top_prop_but_not_see_through_corners(self):
        props = add_prop(add_prop((), 0), 0)                         # two props on top of each other
        self.assertEqual(prop_at(props, self.images, 0.5, 0.5, 640, 480), 1)        # the top one
        # the prop is 240 px tall, 120 wide, centred at (320, 240): its top-left corner is see-through
        self.assertIsNone(prop_at(props, self.images, (262 / 640), (122 / 480), 640, 480))
        self.assertIsNone(prop_at(props, self.images, 0.02, 0.02, 640, 480))      # nowhere near
        front = bring_to_front(add_prop(props, 0, size=0.2), 0)
        self.assertEqual([p.size for p in front], [0.5, 0.2, 0.5])

    def test_render_draws_props_and_keeps_size(self):
        art = load_art(ASSETS_DIR)
        img = test_photo()
        look = Look(props=add_prop((), 0))
        out = render(img.copy(), look, art)
        self.assertEqual(out.shape, img.shape)
        self.assertFalse(np.array_equal(out, img))                   # the prop is there
        self.assertTrue(np.array_equal(out[:20, :20], img[:20, :20]))   # and only near the middle

    def test_slot_click_mapping(self):
        slots = Slots()
        slots.put(0, test_photo(), Look(), FakeTracker())
        _, rects = slots.compose(load_art(ASSETS_DIR), 'Grid')
        self.assertEqual(slots.photo_rects[0], (BORDER, BORDER, 640, 480))
        self.assertEqual(slots.slot_at(700, 100, rects), 1)          # top-right cell
        self.assertEqual(slots.slot_at(100, 600, rects), 2)          # bottom-left cell
        self.assertIsNone(slots.slot_at(5000, 5000, rects))


class FakeTracker:
    # stands in for MediaPipe: no faces, no person
    def analyse_still(self, img):
        return [], None


class TestSlots(unittest.TestCase):
    def setUp(self):
        self.art = load_art(ASSETS_DIR)
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
