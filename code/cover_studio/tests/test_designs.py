# Checks for saving designs (no AI or windows needed).
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

from core.cover_layout import CoverWords, draw_cover_lettering, square_crop   # noqa: E402
from core.designs import load_recipe, save_lettering, slug                    # noqa: E402

WORDS = CoverWords(name='Big Mike!', title='BOSS LIFE', featuring=('Dre', 'Mama Jo'))


class TestDesigns(unittest.TestCase):
    def test_save_and_remake(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_lettering(WORDS, 'hero', {'name': 'chrome'}, seed=4, print_size=300, designs_dir=Path(tmp))
            self.assertTrue(folder.name.endswith('big-mike'))
            lettering = cv2.imread(str(folder / 'lettering.png'), cv2.IMREAD_UNCHANGED)
            self.assertEqual(lettering.shape, (300, 300, 4))
            self.assertEqual(cv2.imread(str(folder / 'preview.jpg')).shape[2], 3)
            words, layout, styles, seed = load_recipe(folder)
            self.assertEqual((words, layout, styles['name'], seed), (WORDS, 'hero', 'chrome', 4))
            # the recipe draws exactly the same lettering again
            self.assertTrue(np.array_equal(draw_cover_lettering(words, layout, 300, styles, seed), lettering))
            again = save_lettering(WORDS, 'hero', print_size=300, designs_dir=Path(tmp))
            self.assertNotEqual(again, folder)                      # never overwrites a design

    def test_slug_and_square_crop(self):
        self.assertEqual((slug('Big Mike!'), slug('***')), ('big-mike', 'design'))
        self.assertEqual(square_crop(np.zeros((300, 500, 3))).shape, (300, 300, 3))


if __name__ == '__main__':
    unittest.main()
