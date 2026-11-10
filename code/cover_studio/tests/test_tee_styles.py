# Checks for the tee styles (core/tee_styles.py): halftone dots, faded edges and knockout.
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.tee_styles import halftone, knockout_coverage, style_cover, style_print_file   # noqa: E402

BLACK, WHITE, RED = (25, 25, 25), (245, 245, 245), (40, 40, 200)


class TestTeeStyles(unittest.TestCase):
    def test_halftone_dots_cover_about_as_much_as_asked(self):
        for coverage in (0.1, 0.3, 0.6):
            dots = halftone(np.full((300, 300), coverage, np.float32), 12)
            self.assertAlmostEqual(dots.mean(), coverage, delta=0.04)
        self.assertFalse(halftone(np.zeros((50, 50), np.float32), 12).any())

    def test_classic_is_the_whole_square(self):
        cover = np.full((200, 200, 3), 128, np.uint8)
        self.assertTrue((style_cover(cover, 'classic')[..., 3] == 255).all())
        with self.assertRaises(ValueError):
            style_cover(cover, 'sparkly')

    def test_faded_dissolves_the_edges_and_keeps_the_middle(self):
        cover = np.full((400, 400, 3), 128, np.uint8)
        alpha = style_cover(cover, 'faded')[..., 3]
        self.assertTrue((alpha[150:250, 150:250] == 255).all())        # solid in the middle
        self.assertLess(alpha[:4].mean(), 30)                          # almost nothing at the edge
        middle_band = alpha[30:40, 100:300]
        self.assertTrue(0 < middle_band.mean() < 255)                  # dots on the way in
        self.assertTrue(set(np.unique(alpha)) <= {0, 255})             # dots, never see-through ink

    def test_knockout_lets_a_dark_shirt_stand_in_for_the_dark_parts(self):
        cover = np.zeros((100, 100, 3), np.uint8)
        cover[:, 50:] = (60, 180, 230)                                 # a bright gold half
        coverage = knockout_coverage(cover, BLACK)
        self.assertTrue((coverage[:, :50] == 0).all())                 # the black half is the shirt
        self.assertTrue((coverage[:, 50:] == 1).all())
        alpha = style_cover(cover, 'knockout', BLACK)[..., 3]
        self.assertEqual(alpha[:, :50].max(), 0)
        self.assertEqual(alpha[:, 50:].min(), 255)

    def test_knockout_on_light_and_coloured_shirts(self):
        cover = np.zeros((10, 20, 3), np.uint8)
        cover[:, :10] = WHITE
        self.assertTrue((knockout_coverage(cover, WHITE)[:, :10] == 0).all())   # white parts on a white shirt
        self.assertTrue((knockout_coverage(cover, WHITE)[:, 10:] == 1).all())
        cover[:, :10] = RED
        self.assertTrue((knockout_coverage(cover, RED)[:, :10] == 0).all())     # the shirt's own colour
        self.assertTrue((knockout_coverage(cover, RED)[:, 10:] == 1).all())     # black on red still prints

    def test_a_print_file_keeps_its_see_through_surround(self):
        print_file = np.zeros((360, 300, 4), np.uint8)
        print_file[:240, 30:270, :3], print_file[:240, 30:270, 3] = 128, 255     # the cover
        out = style_print_file(print_file, 'faded_knockout', BLACK)
        self.assertEqual(out[240:, :, 3].max(), 0)
        self.assertEqual(out[:, :30, 3].max(), 0)
        self.assertTrue((out[100:140, 130:170, 3] == 255).all())
        self.assertIs(style_print_file(print_file, 'classic'), print_file)


if __name__ == '__main__':
    unittest.main()
