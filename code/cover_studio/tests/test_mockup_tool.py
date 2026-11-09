# Checks for the mockup tool's window logic (desktop/mockup_tool.py), with made-up photos and
# a made-up body finder, so no window, models or bought photos are needed.
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.photo_mockups import Analysis, load_placement                     # noqa: E402
from desktop.mockup_tool import BAR_H, MockupTool, sample_design            # noqa: E402
from core.products import PRODUCTS_BY_KEY                                   # noqa: E402
from tests.test_photo_mockups import body, labels_for                       # noqa: E402


class TestMockupTool(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.folder = self.home / 'mockup_photos'
        (self.folder / 'hoodie').mkdir(parents=True)
        for name in ('a tee.png', 'b tee.png', 'hoodie/c.png'):
            cv2.imwrite(str(self.folder / name), np.full((1000, 1000, 3), 200, np.uint8))
        self.design = self.home / 'tee.png'
        design = np.zeros((180, 150, 4), np.uint8)
        design[:150, :, 2], design[:150, :, 3] = 255, 255
        cv2.imwrite(str(self.design), design)
        self.tool = MockupTool(self.folder, finder=lambda photo: Analysis([body()], labels_for()),
                               background=lambda work: work(), exports_dir=self.home / 'exports',
                               choose_file=lambda: str(self.design))

    def tearDown(self):
        self.tmp.cleanup()

    def key(self, k):
        return self.tool.handle_key(ord(k))

    def test_the_screen(self):
        out = self.tool.screen()
        self.assertEqual(out.shape, (BAR_H + 860, 860, 3))
        self.assertIsNone(self.tool.placement)                   # nothing set up yet
        self.assertEqual(self.tool.product().key, 'tee')         # from the file name

    def test_guess_all_then_check(self):
        self.key('a')
        self.assertFalse(self.tool.busy)
        self.assertEqual([load_placement(p).status for p in self.tool.photos], ['good'] * 3)
        self.assertEqual(load_placement(self.tool.photos[2]).product, 'hoodie')
        self.tool.screen()                                       # draws the print with the sample design
        self.key('f')
        self.assertIn('Every photo is set up', self.tool.message)

    def test_keys_change_the_set_up(self):
        self.key('g')
        self.assertEqual(self.tool.placement.status, 'good')
        self.key('t')
        self.assertEqual(load_placement(self.tool.path).product, 'sweatshirt')
        self.key('v')
        self.assertEqual(load_placement(self.tool.path).view, 'back')
        self.key('c')                                            # looks right: saved, and on to the next
        self.assertEqual(load_placement(self.tool.photos[0]).status, 'set')
        self.assertEqual(self.tool.index, 1)
        self.key('s')
        self.assertEqual(load_placement(self.tool.photos[1]).status, 'skip')
        self.assertEqual(self.tool.index, 2)
        self.tool.handle_key(2424832)                            # left arrow
        self.assertEqual(self.tool.index, 1)
        self.assertEqual(self.key('q'), 'quit')

    def test_dragging_a_corner(self):
        self.key('g')
        s = self.tool.scale()
        (x, y) = self.tool.placement.corners[0]
        self.tool.handle_mouse(cv2.EVENT_LBUTTONDOWN, round(x * s), round(y * s) + BAR_H)
        self.tool.handle_mouse(cv2.EVENT_MOUSEMOVE, round(x * s) - 20, round(y * s) + BAR_H)
        self.tool.screen()                                       # an outline while dragging
        self.tool.handle_mouse(cv2.EVENT_LBUTTONUP, round(x * s) - 20, round(y * s) + BAR_H)
        saved = load_placement(self.tool.path)
        self.assertEqual(saved.status, 'set')
        self.assertAlmostEqual(saved.corners[0][0], x - 20 / s, delta=2)
        self.assertEqual(saved.corners[1], self.tool.placement.corners[1])

    def test_dragging_the_middle_moves_it_all(self):
        self.key('g')
        s = self.tool.scale()
        before = np.array(self.tool.placement.corners)
        cx, cy = before.mean(axis=0) * s
        self.tool.handle_mouse(cv2.EVENT_LBUTTONDOWN, int(cx), int(cy) + BAR_H)
        self.tool.handle_mouse(cv2.EVENT_MOUSEMOVE, int(cx) + 10, int(cy) + BAR_H)
        self.tool.handle_mouse(cv2.EVENT_LBUTTONUP, int(cx) + 10, int(cy) + BAR_H)
        moved = np.array(load_placement(self.tool.path).corners) - before
        # saved to a tenth of a pixel
        self.assertTrue(np.allclose(moved[:, 0], 10 / s, atol=0.06) and np.allclose(moved[:, 1], 0, atol=0.06))

    def test_writing_mockups_of_a_design(self):
        self.key('w')
        self.assertIn('Choose a design first', self.tool.message)
        self.key('a')
        self.key('d')
        self.tool.screen()
        self.key('w')
        out = self.home / 'exports' / 'mockups-tee'
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['tee-a tee.jpg', 'tee-b tee.jpg'])

    def test_no_photos_yet(self):
        tool = MockupTool(self.home / 'empty', finder=None)
        self.assertEqual(tool.screen().shape[1], 860)
        self.assertIsNone(tool.handle_key(ord('g')))
        self.assertEqual(tool.handle_key(ord('q')), 'quit')

    def test_sample_design_is_shaped_like_the_product(self):
        d = sample_design(PRODUCTS_BY_KEY['hoodie'])
        self.assertAlmostEqual(d.shape[1] / d.shape[0], 14 / 12, delta=0.01)


if __name__ == '__main__':
    unittest.main()
