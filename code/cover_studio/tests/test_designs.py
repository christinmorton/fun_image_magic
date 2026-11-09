# Checks for saving designs (no AI or windows needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import CoverWords, draw_cover_lettering, square_crop   # noqa: E402
from core.designs import (list_designs, load_artwork, load_recipe, save_lettering,   # noqa: E402
                          slug, update_framing)
from core.framing import Framing                                              # noqa: E402

WORDS = CoverWords(name='Big Mike!', title='BOSS LIFE', featuring=('Dre', 'Mama Jo'))


class TestDesigns(unittest.TestCase):
    def test_save_and_remake(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_lettering(WORDS, 'hero', {'name': 'chrome', 'sticker': 'stamp'}, seed=4, print_size=300,
                                    designs_dir=Path(tmp), finishes={'name': 'vhs', 'title': 'print'}, strength=0.8)
            self.assertTrue(folder.name.endswith('big-mike'))
            lettering = cv2.imread(str(folder / 'lettering.png'), cv2.IMREAD_UNCHANGED)
            self.assertEqual(lettering.shape, (300, 300, 4))
            self.assertEqual(cv2.imread(str(folder / 'preview.jpg')).shape[2], 3)
            r = load_recipe(folder)
            self.assertEqual((r['words'], r['layout'], r['styles']['name'], r['styles']['sticker'], r['seed'],
                              r['strength']), (WORDS, 'hero', 'chrome', 'stamp', 4, 0.8))
            self.assertEqual((r['finishes']['name'], r['finishes']['title'], r['finishes']['featuring']),
                             ('vhs', 'print', 'clean'))
            # the recipe draws exactly the same lettering again
            again = draw_cover_lettering(r['words'], r['layout'], 300, r['styles'], r['seed'], r['finishes'],
                                         r['strength'])
            self.assertTrue(np.array_equal(again, lettering))

    def test_a_design_with_artwork_saves_the_whole_cover(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = np.full((400, 500, 3), 120, np.uint8)                      # not square: cropped
            folder = save_lettering(WORDS, 'hero', print_size=300, picture=art, designs_dir=Path(tmp),
                                    finishes={'artwork': 'print'})
            self.assertEqual(cv2.imread(str(folder / 'artwork.png')).shape, (400, 400, 3))
            self.assertEqual(cv2.imread(str(folder / 'cover.jpg')).shape, (400, 400, 3))
            self.assertEqual(load_recipe(folder)['finishes']['artwork'], 'print')
            moved = save_lettering(WORDS, 'hero', print_size=300, picture=art, designs_dir=Path(tmp),
                                   framing=Framing(zoom=0.9, dy=0.1))
            self.assertEqual(load_recipe(moved)['framing'], {'zoom': 0.9, 'dx': 0.0, 'dy': 0.1})
            self.assertEqual(load_recipe(folder)['framing'], {'zoom': 1.0, 'dx': 0.0, 'dy': 0.0})
            plain = save_lettering(WORDS, 'hero', print_size=300, designs_dir=Path(tmp))
            self.assertFalse((plain / 'cover.jpg').exists())                 # only with real artwork

    def test_list_and_update_framing(self):
        with tempfile.TemporaryDirectory() as tmp:
            art = np.random.default_rng(0).integers(0, 255, (300, 300, 3)).astype(np.uint8)
            first = save_lettering(WORDS, 'hero', print_size=200, picture=art, designs_dir=Path(tmp))
            second = save_lettering(WORDS, 'hero', print_size=200, designs_dir=Path(tmp))
            self.assertEqual(list_designs(Path(tmp)), [second, first])           # newest first
            self.assertEqual(list_designs(Path(tmp) / 'nothing-here'), [])
            cover_before = cv2.imread(str(first / 'cover.jpg'))
            lettering_before = (first / 'lettering.png').read_bytes()
            update_framing(first, Framing(dy=0.15))
            self.assertEqual(load_recipe(first)['framing']['dy'], 0.15)
            self.assertFalse(np.array_equal(cv2.imread(str(first / 'cover.jpg')), cover_before))
            self.assertEqual((first / 'lettering.png').read_bytes(), lettering_before)   # the words didn't change
            self.assertIsNone(load_artwork(second))                               # the placeholder design

    def test_an_older_recipe_with_one_finish(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_lettering(WORDS, 'hero', print_size=200, designs_dir=Path(tmp))
            recipe = json.loads((folder / 'recipe.json').read_text(encoding='utf-8'))
            del recipe['finishes']
            recipe['finish'] = 'vhs'
            (folder / 'recipe.json').write_text(json.dumps(recipe), encoding='utf-8')
            self.assertEqual(set(load_recipe(folder)['finishes'].values()), {'vhs'})
            again = save_lettering(WORDS, 'hero', print_size=300, designs_dir=Path(tmp))
            self.assertNotEqual(again, folder)                      # never overwrites a design

    def test_slug_and_square_crop(self):
        self.assertEqual((slug('Big Mike!'), slug('***')), ('big-mike', 'design'))
        self.assertEqual(square_crop(np.zeros((300, 500, 3))).shape, (300, 300, 3))


if __name__ == '__main__':
    unittest.main()
