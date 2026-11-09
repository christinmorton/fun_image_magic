# Checks for the photo mockups: guessing where the print goes from what the models found
# (made-up bodies, so MediaPipe isn't needed), the set-up files, and printing a design on a
# photo. Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.photo_mockups import (CLOTHES, FACE_SKIN, PRINT_TOP_IN, SHOULDER_IN, TORSO_IN,   # noqa: E402
                                Analysis, Placement, fit_design, guess, list_photos, load_clothes,
                                load_placement, make_photo_mockups, place, print_on, product_from_name,
                                ready_photos, refit, save_placement)
from core.products import PRODUCTS_BY_KEY                                                    # noqa: E402

TEE, HOODIE = PRODUCTS_BY_KEY['tee'], PRODUCTS_BY_KEY['hoodie']


def body(left=(650, 400), right=(350, 400), hips=((600, 820), (400, 820)), seen=1.0):
    # a made-up person facing the camera: their left shoulder is on the photo's right
    return {'nose': (500, 250, seen), 'left_shoulder': (*left, seen), 'right_shoulder': (*right, seen),
            'left_hip': (*hips[0], seen), 'right_hip': (*hips[1], seen)}

def labels_for(corners=None, shape=(1000, 1000), face=True):
    # everything is clothes, with a face at the top
    labels = np.full(shape, CLOTHES, np.uint8)
    if face:
        labels[150:300, 420:580] = FACE_SKIN
    return labels


class TestGuessing(unittest.TestCase):
    def setUp(self):
        self.photo = np.full((1000, 1000, 3), 200, np.uint8)

    def test_the_print_area_sits_on_the_chest_at_its_real_size(self):
        p = place(self.photo, Analysis([body()], labels_for()), TEE)
        self.assertEqual((p.product, p.view, p.status), ('tee', 'front', 'good'))
        self.assertEqual(len(p.notes), 1)
        self.assertIn('A small photo (1000 x 1000)', p.notes[0])   # said, but it doesn't need checking
        tl, tr, br, bl = p.corners
        per_in = 300 / SHOULDER_IN                       # the shoulders are 300 px apart
        self.assertAlmostEqual(tr[0] - tl[0], 15 * per_in, delta=0.5)       # 15 in wide
        self.assertAlmostEqual((tl[0] + tr[0]) / 2, 500, delta=0.5)         # centred between the shoulders
        per_in_y = 420 / TORSO_IN                        # the hips are 420 px below them
        self.assertAlmostEqual(tl[1], 400 + PRINT_TOP_IN['tee'] * per_in_y, delta=0.5)
        self.assertAlmostEqual(bl[1] - tl[1], 18 * per_in_y, delta=0.5)     # 18 in tall
        self.assertEqual(p.colour, (200, 200, 200))
        self.assertFalse(p.dark)

    def test_a_hoodie_print_starts_lower(self):
        tee = place(self.photo, Analysis([body()], labels_for()), TEE)
        hoodie = place(self.photo, Analysis([body()], labels_for()), HOODIE)
        self.assertGreater(hoodie.corners[0][1], tee.corners[0][1])

    def test_hips_out_of_the_photo(self):
        p = place(self.photo, Analysis([body(hips=((600, 1500), (400, 1500)))], labels_for()), TEE)
        tl, tr, _, bl = p.corners
        self.assertAlmostEqual((bl[1] - tl[1]) / 18, (tr[0] - tl[0]) / 15, delta=0.01)   # same scale both ways
        self.assertEqual(p.status, 'good')

    def test_a_sloping_body_turns_the_print(self):
        p = place(self.photo, Analysis([body(left=(650, 460), right=(350, 400))], labels_for()), TEE)
        self.assertGreater(p.corners[1][1], p.corners[0][1])

    def test_no_person(self):
        p = place(self.photo, Analysis([], labels_for(face=False)), TEE)
        self.assertEqual(p.status, 'check')
        self.assertIn('No person found', p.notes[0])
        self.assertEqual(p.view, 'back')

    def test_the_shoulders_tell_front_from_back(self):
        # from behind, the person's left shoulder is on the photo's left, face or no face
        p = place(self.photo, Analysis([body(left=(350, 400), right=(650, 400))], labels_for()), TEE)
        self.assertEqual((p.view, p.status), ('back', 'check'))
        self.assertIn('Looks like a back view', p.notes)
        p = place(self.photo, Analysis([body()], labels_for(face=False)), TEE)
        self.assertEqual(p.view, 'front')

    def test_two_people_uses_the_biggest(self):
        small = body(left=(300, 400), right=(200, 400), hips=((280, 540), (220, 540)))
        p = place(self.photo, Analysis([small, body()], labels_for()), TEE)
        self.assertIn('2 people: used the biggest', p.notes)
        self.assertAlmostEqual((p.corners[0][0] + p.corners[1][0]) / 2, 500, delta=0.5)

    def test_something_in_front_of_the_shirt(self):
        labels = labels_for()
        labels[600:800, 300:700] = 2                     # an arm across the chest
        p = place(self.photo, Analysis([body()], labels), TEE)
        self.assertEqual(p.status, 'check')
        self.assertTrue(any('isn\'t shirt' in note for note in p.notes))

    def test_a_dark_garment(self):
        p = place(np.full((1000, 1000, 3), 25, np.uint8), Analysis([body()], labels_for()), TEE)
        self.assertTrue(p.dark)

    def test_refit_keeps_the_width_and_top(self):
        p = place(self.photo, Analysis([body()], labels_for()), TEE)
        h = refit(p, HOODIE)
        self.assertEqual(h.product, 'hoodie')
        self.assertEqual(h.corners[:2], p.corners[:2])
        width, height = h.corners[1][0] - h.corners[0][0], h.corners[3][1] - h.corners[0][1]
        self.assertAlmostEqual(height / width, 12 / 14, delta=0.01)

    def test_product_from_name(self):
        self.assertEqual(product_from_name(Path('MEN_S HOODIE/Orange hoodie_(2).png')), 'hoodie')
        self.assertEqual(product_from_name(Path('Gildan 18000 Black woman 01.png')), 'sweatshirt')
        self.assertEqual(product_from_name(Path('WOMEN_S SWEATSHIRT/Love.png')), 'sweatshirt')
        self.assertEqual(product_from_name(Path('MEN_S T-SHIRT/Love.png')), 'tee')


class TestFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.photo = self.folder / 'tee' / 'man in white.png'
        self.photo.parent.mkdir()
        cv2.imwrite(str(self.photo), np.full((1000, 1000, 3), 200, np.uint8))

    def tearDown(self):
        self.tmp.cleanup()

    def finder(self, photo):
        return Analysis([body()], labels_for())

    def test_guess_keeps_the_set_up_and_the_clothes_next_to_the_photo(self):
        p = guess(self.photo, self.finder, PRODUCTS_BY_KEY)
        self.assertEqual(load_placement(self.photo), p)
        self.assertEqual(load_clothes(self.photo).shape, (1000, 1000))
        self.assertEqual(list_photos(self.folder), [self.photo])       # the mask isn't a photo
        self.assertIsNone(load_placement(self.folder / 'nothing.png'))

    def test_a_placement_survives_saving(self):
        p = Placement('hoodie', ((1.5, 2), (3, 2), (3, 4), (1.5, 4)), 'back', (10, 20, 30), 'set', ('a note',))
        save_placement(self.photo, p)
        self.assertEqual(load_placement(self.photo), p)

    def test_only_usable_front_views_get_mockups(self):
        guess(self.photo, self.finder, PRODUCTS_BY_KEY)
        for name, change in [('back.png', {'view': 'back'}), ('skipped.png', {'status': 'skip'}),
                             ('hoodie.png', {'product': 'hoodie'}), ('by hand.png', {'status': 'set'})]:
            path = self.folder / name
            cv2.imwrite(str(path), np.full((1000, 1000, 3), 200, np.uint8))
            p = guess(path, self.finder, PRODUCTS_BY_KEY, 'tee')
            from dataclasses import replace
            save_placement(path, replace(p, **change))
        self.assertEqual([p.name for p, _ in ready_photos('tee', self.folder)], ['by hand.png', 'man in white.png'])
        design = np.zeros((180, 150, 4), np.uint8)
        design[:150, :, :3], design[:150, :, 3] = (0, 0, 255), 255
        written = make_photo_mockups({'tee': design, 'poster': design}, self.folder / 'out', self.folder, limit=1)
        self.assertEqual([p.name for p in written], ['tee-by hand.jpg'])
        self.assertEqual(cv2.imread(str(written[0])).shape, (1000, 1000, 3))


class TestPrinting(unittest.TestCase):
    def setUp(self):
        self.photo = np.full((400, 400, 3), 220, np.uint8)
        self.corners = ((100, 100), (300, 100), (300, 340), (100, 340))
        self.design = np.zeros((180, 150, 4), np.uint8)
        self.design[:150, :, :3], self.design[:150, :, 3] = (0, 0, 255), 255     # red on top, see-through below

    def test_the_design_lands_in_the_corners(self):
        out = print_on(self.photo, self.corners, self.design)
        self.assertTrue((out[:90] == 220).all() and (out[:, :90] == 220).all())   # nothing outside
        b, g, r = out[150, 200].astype(int)
        self.assertGreater(r, 150)
        self.assertLess(g, 80)
        self.assertTrue((abs(out[325, 200].astype(int) - 220) < 6).all())         # the see-through part

    def test_a_bgr_design_works_too(self):
        out = print_on(self.photo, self.corners, self.design[..., :3])
        self.assertLess(int(out[325, 200, 2]), 50)                                 # all of it printed (black)

    def test_whatever_is_in_front_of_the_shirt_stays_in_front(self):
        clothes = np.full((400, 400), 255, np.uint8)
        clothes[140:180, :] = 0                                                    # an arm
        out = print_on(self.photo, self.corners, self.design, clothes)
        self.assertTrue((abs(out[160, 200].astype(int) - 220) < 6).all())
        self.assertGreater(int(out[220, 200, 2]), 150)

    def test_folds_shade_the_print(self):
        photo = self.photo.copy()
        photo[:, 195:215] = 120                                                    # a shadowed fold
        out = print_on(photo, self.corners, self.design)
        self.assertLess(int(out[150, 205, 2]), int(out[150, 150, 2]) - 30)

    def test_fit_design_pads_rather_than_stretches(self):
        hoodie = fit_design(self.design, HOODIE)                                   # 14 x 12: wider
        self.assertAlmostEqual(hoodie.shape[1] / hoodie.shape[0], 14 / 12, delta=0.01)
        self.assertEqual(hoodie.shape[0], 180)
        self.assertTrue((hoodie[:, :10, 3] == 0).all())                            # padded at the sides
        self.assertIs(fit_design(self.design, PRODUCTS_BY_KEY['tee']), self.design)


if __name__ == '__main__':
    unittest.main()
