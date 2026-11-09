# Checks for the upscaler. The models aren't in git (tools/get_upscale_models.py fetches
# them), so the tests that need one are skipped where they haven't been fetched.
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core import upscale as up                     # noqa: E402


def detailed(w=120, h=90):
    return np.random.default_rng(0).integers(0, 255, (h, w, 3)).astype(np.uint8)


class TestUpscale(unittest.TestCase):
    def test_choosing_a_model(self):
        self.assertEqual(up.pick_model(3.5), 'fsrcnn_x4')               # fast by default
        self.assertEqual(up.pick_model(1.8, 'best'), 'edsr_x2')
        self.assertEqual(up.pick_model(3.5, 'best'), 'edsr_x4')

    def test_shrinking_needs_no_model(self):
        with mock.patch.object(up, 'network', side_effect=AssertionError('no network for shrinking')):
            self.assertEqual(up.upscale(detailed(), 60).shape, (45, 60, 3))
            self.assertEqual(up.upscale(detailed(), 125).shape, (94, 125, 3))   # a tiny change: plain resize

    def test_a_missing_model_says_how_to_get_it(self):
        with mock.patch.object(up, 'UPSCALE_DIR', Path('no-such-folder')), mock.patch.dict(up._loaded, clear=True):
            with self.assertRaises(FileNotFoundError) as caught:
                up.network('edsr_x4')
            self.assertIn('get_upscale_models', str(caught.exception))

    @unittest.skipUnless(up.available('fsrcnn_x4'), 'run tools\\get_upscale_models.py to test with the model')
    def test_fast_upscale_to_an_exact_size(self):
        big = up.upscale(detailed(), 400, 300)
        self.assertEqual(big.shape, (300, 400, 3))
        self.assertEqual(up.upscale(detailed(), 360).shape, (270, 360, 3))   # keeps the shape

    @unittest.skipUnless(up.available('fsrcnn_x4'), 'run tools\\get_upscale_models.py to test with the model')
    def test_sharper_than_a_plain_resize(self):
        # a soft photo-like picture: the network should keep more edge detail than bicubic
        small = cv2.GaussianBlur(detailed(200, 200), (0, 0), 1.5)
        plain = cv2.resize(small, (800, 800), interpolation=cv2.INTER_CUBIC)
        detail = lambda img: cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()
        self.assertGreater(detail(up.upscale(small, 800)), detail(plain))


if __name__ == '__main__':
    unittest.main()
