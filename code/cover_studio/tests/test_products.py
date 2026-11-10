# Checks for the product print files and mockups, at tiny sizes so they're quick (and the
# artwork only ever shrinks, so the upscaling models aren't needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from PIL import Image

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core import products                                                         # noqa: E402
from core.cover_layout import CoverWords, draw_cover_lettering                    # noqa: E402
from core.designs import save_lettering                                           # noqa: E402
from core.mockups import TILE, mockup_sheet                                       # noqa: E402
from core.products import (CASE_ART_TOP, CASE_LAYOUT, PRODUCTS, Product,           # noqa: E402
                           export_products, load_design, make_product)

WORDS = CoverWords(name='BIG MIKE', title='BOSS LIFE', featuring=('Dre', 'Mama Jo'))
SMALL = [Product('poster', 'Poster', 150, 200, 'poster'), Product('tee', 'T-shirt', 150, 180, 'garment'),
         Product('hoodie', 'Hoodie', 140, 120, 'garment'), Product('phone', 'Phone case', 100, 200, 'case')]


class TestProducts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        art = np.random.default_rng(0).integers(0, 255, (300, 300, 3)).astype(np.uint8)
        self.folder = save_lettering(WORDS, 'hero', print_size=200, picture=art, designs_dir=self.home / 'designs',
                                     finishes={'artwork': 'print', 'name': 'vhs'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_product_has_a_real_spec(self):
        self.assertEqual({p.key for p in PRODUCTS}, {'poster', 'tee', 'hoodie', 'sweatshirt', 'phone'})
        for p in PRODUCTS:
            self.assertGreaterEqual(min(p.width, p.height), 1500)          # print sizes, not screen sizes

    def test_each_kind_of_product(self):
        design = load_design(self.folder)
        poster, tee, hoodie, phone = (make_product(p, design) for p in SMALL)
        self.assertEqual(poster.shape, (200, 150, 3))                      # filled edge to edge
        self.assertEqual(tee.shape, (180, 150, 4))
        self.assertTrue((tee[:150, :, 3] == 255).all())                    # the square cover at the top...
        self.assertTrue((tee[160:, :, 3] == 0).all())                      # ...see-through below it
        self.assertEqual(hoodie.shape, (120, 140, 4))
        self.assertTrue((hoodie[:, :8, 3] == 0).all())                     # cover centred, see-through at the sides
        self.assertEqual(phone.shape, (200, 100, 3))

    def test_a_garment_cover_can_be_narrower_than_the_print_area(self):
        tee = make_product(Product('tee', 'T-shirt', 150, 180, 'garment', cover_in=0.4), load_design(self.folder))
        self.assertTrue((tee[:120, 15:135, 3] == 255).all())               # 0.4 in at 300 dpi: 120 px, centred
        self.assertTrue((tee[:, :15, 3] == 0).all() and (tee[121:, :, 3] == 0).all())
        self.assertEqual(products.PRODUCTS_BY_KEY['tee'].cover_in, 12)

    def test_the_phone_case_keeps_the_camera_corner_plain(self):
        layer = draw_cover_lettering(WORDS, CASE_LAYOUT, (100, 200), seed=1)
        self.assertEqual(layer.shape, (200, 100, 4))                       # a tall canvas works
        self.assertEqual((layer[:int(200 * 0.2), :, 3] > 128).sum(), 0)     # nothing under the camera
        self.assertGreater((layer[int(200 * 0.21):int(200 * CASE_ART_TOP), :, 3] > 128).sum(), 0)   # the name

    def test_export_writes_300_dpi_files_and_mockups(self):
        with mock.patch.object(products, 'PRODUCTS', SMALL):
            out = export_products(self.folder, exports_dir=self.home / 'exports', photos_dir=self.home / 'no photos')
        self.assertEqual(out.name, self.folder.name)
        self.assertEqual(sorted(p.name for p in out.iterdir()),
                         ['hoodie.png', 'mockups.jpg', 'phone.png', 'poster.png', 'tee.png'])
        info = Image.open(out / 'tee.png')
        self.assertEqual((info.size, info.mode), ((150, 180), 'RGBA'))
        self.assertAlmostEqual(info.info['dpi'][0], 300, delta=0.01)
        self.assertEqual(cv2.imread(str(out / 'mockups.jpg')).shape, (2 * TILE, 2 * TILE, 3))

    def test_mockup_sheet(self):
        tee = np.zeros((180, 150, 4), np.uint8)
        self.assertEqual(mockup_sheet({'tee': tee}).shape, (TILE, 2 * TILE, 3))     # one row, padded
        self.assertEqual(mockup_sheet({}).shape, (TILE, TILE, 3))


if __name__ == '__main__':
    unittest.main()
