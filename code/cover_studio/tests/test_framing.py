# Checks for moving the artwork under the lettering, with made-up faces (no AI or
# windows needed). Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import LAYOUTS                                        # noqa: E402
from core.framing import MARGIN, Framing, auto_framing, face_span, frame_artwork   # noqa: E402
from test_scan import face                                                   # noqa: E402

ART = np.zeros((200, 200, 3), np.uint8)
ART[:100] = (0, 0, 200)          # red top half, blue bottom half, to see where it moved
ART[100:] = (200, 0, 0)


def detect_at(top, bottom):
    # a fake face finder: one face spanning top-bottom (fractions of the picture's height)
    return lambda img: [face(box=(0.4, top, 0.6, bottom))]


class TestFraming(unittest.TestCase):
    def test_no_change_is_a_plain_resize(self):
        self.assertTrue(np.array_equal(frame_artwork(ART, 100), frame_artwork(ART, 100, Framing())))
        self.assertEqual(frame_artwork(ART, 100).shape, (100, 100, 3))

    def test_moving_and_zooming(self):
        down = frame_artwork(ART, 100, Framing(dy=0.2))
        self.assertGreater(down[60, 50, 2], 150)                 # the red half reaches lower now
        self.assertLess(down[5, 50, 2], 150)                     # the gap at the top is the blurred, darker fill
        small = frame_artwork(ART, 100, Framing(zoom=0.5))
        self.assertEqual(small.shape, (100, 100, 3))
        self.assertGreater(small[30, 50, 2], 150)                # the whole picture, smaller, in the middle

    def test_face_span(self):
        self.assertEqual(face_span(ART, lambda img: []), None)
        top, bottom = face_span(ART, detect_at(0.1, 0.3))
        self.assertAlmostEqual(top, 0.1, delta=0.01)
        self.assertAlmostEqual(bottom, 0.3, delta=0.01)

    def test_auto_framing_clears_the_name_and_title(self):
        hero = LAYOUTS['hero']
        name_bottom = hero.spots['name'].y + hero.spots['name'].h
        title_top = hero.spots['title'].y
        self.assertEqual(auto_framing(ART, 'hero', detect_at(0.35, 0.6)), Framing())      # already clear
        self.assertEqual(auto_framing(ART, 'hero', lambda img: []), Framing())           # no face: no change
        high = auto_framing(ART, 'hero', detect_at(0.14, 0.30))                           # under the name
        self.assertEqual(high.zoom, 1.0)
        self.assertAlmostEqual(0.14 + high.dy, name_bottom + MARGIN, delta=0.01)          # moved just below it
        low = auto_framing(ART, 'hero', detect_at(0.6, 0.85))                             # under the title
        self.assertAlmostEqual(0.85 + low.dy, title_top - MARGIN, delta=0.01)             # moved up above it
        tall = auto_framing(ART, 'hero', detect_at(0.1, 0.95))                            # can't fit: zoom out
        self.assertLess(tall.zoom, 1.0)
        self.assertAlmostEqual(0.5 + (0.1 - 0.5) * tall.zoom + tall.dy, name_bottom + MARGIN, delta=0.01)


if __name__ == '__main__':
    unittest.main()
