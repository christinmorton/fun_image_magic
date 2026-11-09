# Checks for the lettering screen's logic (no windows open: the typing dialog is replaced
# by a fake). Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import LAYOUTS, STICKERS, CoverWords                     # noqa: E402
from core.designs import load_recipe, save_lettering                            # noqa: E402
from core.framing import Framing                                                # noqa: E402
from desktop.studio import BAR_H, MOVE, PREVIEW, TAB_KEY, LetteringScreen       # noqa: E402
from test_scan import face                                                      # noqa: E402


class FakeAsk:
    # answers the typing dialog with the next prepared answer, and remembers the questions
    def __init__(self, *answers):
        self.answers, self.asked = list(answers), []

    def __call__(self, title, prompt, initial=''):
        self.asked.append((title, initial))
        return self.answers.pop(0)


class TestLetteringScreen(unittest.TestCase):
    def test_screen_size(self):
        self.assertEqual(LetteringScreen().screen().shape, (BAR_H + PREVIEW, PREVIEW, 3))

    def test_typing_keys_edit_the_words(self):
        ask = FakeAsk('LIL RAY', 'Dre,  Mama Jo , ,Smoke', 'GOLD TEETH / CERTIFIED', None)
        screen = LetteringScreen(ask=ask)
        screen.handle_key(ord('n'))
        screen.handle_key(ord('f'))
        screen.handle_key(ord('e'))
        screen.handle_key(ord('t'))                                  # cancelled: the title stays
        self.assertEqual(screen.words.name, 'LIL RAY')
        self.assertEqual(screen.words.featuring, ('Dre', 'Mama Jo', 'Smoke'))
        self.assertEqual(screen.words.sticker, ('GOLD TEETH', 'CERTIFIED'))
        self.assertEqual(screen.words.title, 'BOSS LIFE')
        self.assertEqual(ask.asked[0], ('Name', 'BIG MIKE'))         # the dialog starts with the current words

    def test_layout_style_and_reshuffle_keys(self):
        screen = LetteringScreen()
        first = screen.layout
        screen.handle_key(ord('1'))
        self.assertNotEqual(screen.styles['name'], LAYOUTS[first].styles['name'])
        screen.handle_key(ord('l'))
        self.assertNotEqual(screen.layout, first)
        self.assertEqual(screen.styles['name'], LAYOUTS[screen.layout].styles['name'])   # a new layout brings
        self.assertEqual(screen.styles['title'], LAYOUTS[screen.layout].styles['title'])  # its own styles
        self.assertEqual(LAYOUTS[first].styles['name'], 'gold')          # ...and the old one wasn't changed
        before = screen.cover().copy()
        screen.handle_key(ord('r'))
        self.assertEqual(screen.seed, 2)
        self.assertFalse(np.array_equal(before, screen.cover()))         # the cover is redrawn

    def test_finish_for_all_parts_or_one(self):
        screen = LetteringScreen()
        self.assertEqual(set(screen.finishes.values()), {'print'})       # aged by default
        aged = screen.cover().copy()
        screen.handle_key(ord('a'))                                       # part "all"
        self.assertEqual(set(screen.finishes.values()), {'vhs'})
        self.assertFalse(np.array_equal(aged, screen.cover()))
        screen.handle_key(TAB_KEY)                                        # part "artwork"
        self.assertEqual(screen.part, 'artwork')
        screen.handle_key(TAB_KEY)                                        # part "name"
        self.assertEqual(screen.part, 'name')
        screen.handle_key(ord('a'))
        self.assertEqual(screen.finishes['name'], 'clean')
        self.assertEqual(screen.finishes['title'], 'vhs')                 # the other parts keep theirs

    def test_sticker_key_cycles_designs_and_none(self):
        screen = LetteringScreen()
        self.assertEqual(screen.words.sticker, ('CERTIFIED', 'HOOD CLASSIC'))
        seen = []
        for _ in STICKERS:
            screen.handle_key(ord('k'))
            seen.append((screen.words.sticker, screen.styles['sticker']))
        self.assertIn(((), 'badge'), seen)                                # no sticker
        self.assertEqual({look for _, look in seen}, {'badge', 'stamp', 'hazard'})
        self.assertEqual(seen[-1], (('CERTIFIED', 'HOOD CLASSIC'), 'badge'))   # round to the start
        screen.handle_key(ord('l'))
        self.assertEqual(screen.styles['sticker'], 'badge')               # kept when the layout changes

    def test_export_needs_a_saved_design(self):
        screen = LetteringScreen(background=lambda work: work())
        screen.handle_key(ord('x'))
        self.assertIn('Save the design first', screen.message)
        screen.saved = Path('designs/20261108-120000-big-mike')
        screen.saved_as = (screen.settings(), screen.framing)
        with mock.patch('desktop.studio.export_products', return_value=Path('exports/20261108-120000-big-mike')) as fake:
            screen.handle_key(ord('x'))
        fake.assert_called_once()
        self.assertEqual(fake.call_args.args[0], screen.saved)
        self.assertIn('exports/20261108-120000-big-mike', screen.message)
        self.assertFalse(screen.exporting)

    def test_open_a_saved_design_move_it_and_export(self):
        art = np.random.default_rng(0).integers(0, 255, (300, 300, 3)).astype(np.uint8)
        words = CoverWords(name='DEVIN MONEY', title='BOSS LIFE', sticker=('STREET', 'CERTIFIED'))
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_lettering(words, 'boss_desk', {'name': 'chrome', 'sticker': 'stamp'}, seed=7, picture=art,
                                    print_size=200, designs_dir=Path(tmp), finishes={'name': 'vhs'})
            screen = LetteringScreen(detect=lambda img: [], choose_design=lambda folders: folders[0],
                                     background=lambda work: work())
            with mock.patch('desktop.studio.list_designs', return_value=[folder]):
                screen.handle_key(ord('d'))
            self.assertEqual((screen.words, screen.layout, screen.seed), (words, 'boss_desk', 7))
            self.assertEqual((screen.styles['name'], screen.styles['sticker'], screen.finishes['name']),
                             ('chrome', 'stamp', 'vhs'))
            self.assertEqual(STICKERS[screen.sticker][0], 'Street Certified')
            self.assertIsNotNone(screen.picture)
            self.assertEqual(screen.saved, folder)
            screen.handle_key(2621440)                               # move the picture down, then export
            with mock.patch('desktop.studio.export_products', return_value=folder) as export:
                screen.handle_key(ord('x'))
            export.assert_called_once()
            self.assertGreater(load_recipe(folder)['framing']['dy'], 0)     # the saved design was updated
            screen.words = replace(screen.words, title='NEW TITLE')         # a real change: save it first
            with mock.patch('desktop.studio.export_products') as export:
                screen.handle_key(ord('x'))
            export.assert_not_called()
            self.assertIn('S saves it', screen.message)

    def test_quit_save_and_nothing(self):
        screen = LetteringScreen()
        self.assertEqual(screen.handle_key(ord('q')), 'quit')
        self.assertEqual(screen.handle_key(ord('S')), 'save')
        self.assertIsNone(screen.handle_key(-1))

    def test_the_picture_is_fitted_and_can_be_moved(self):
        art = np.random.default_rng(0).integers(0, 255, (512, 512, 3)).astype(np.uint8)
        under_the_name = lambda img: [face(box=(0.4, 0.14, 0.6, 0.30))]
        screen = LetteringScreen(picture=art, detect=under_the_name)
        self.assertGreater(screen.framing.dy, 0)                          # moved down off the name
        fitted = screen.framing
        screen.handle_key(2621440)                                         # the down arrow (Windows code)
        self.assertAlmostEqual(screen.framing.dy, fitted.dy + MOVE)
        self.assertFalse(screen.framing_auto)
        screen.handle_key(ord(']'))
        self.assertGreater(screen.framing.zoom, 1.0)
        screen.handle_key(ord('o'))                                        # back as the AI made it
        self.assertEqual(screen.framing, Framing())
        screen.handle_key(ord('z'))                                        # fitted again
        self.assertEqual(screen.framing, fitted)
        self.assertEqual(screen.cover().shape, (PREVIEW, PREVIEW, 3))

    def test_moving_keys_leave_the_placeholder_alone(self):
        screen = LetteringScreen(detect=lambda img: [])
        screen.handle_key(2621440)
        self.assertEqual(screen.framing, Framing())
        self.assertIn('placeholder', screen.message)

    def test_starting_with_artwork_and_a_name(self):
        art = np.random.default_rng(0).integers(0, 255, (512, 512, 3)).astype(np.uint8)
        screen = LetteringScreen(picture=art, name='OOUMARI', detect=lambda img: [])
        self.assertEqual(screen.words.name, 'OOUMARI')
        aged = screen.cover().copy()
        screen.handle_key(TAB_KEY)                                        # part "artwork"
        screen.handle_key(ord('a'))                                       # artwork: print -> vhs
        self.assertEqual(screen.finishes['artwork'], 'vhs')
        self.assertEqual(screen.finishes['name'], 'print')
        self.assertFalse(np.array_equal(aged, screen.cover()))           # the picture itself is aged

    def test_a_picture_behind_the_words(self):
        screen = LetteringScreen()
        plain = screen.cover().copy()
        screen.picture = np.full((480, 640, 3), (200, 50, 50), np.uint8)
        self.assertFalse(np.array_equal(plain, screen.cover()))
        screen.handle_key(ord('b'))
        self.assertTrue(np.array_equal(plain, screen.cover()))           # back to the placeholder


if __name__ == '__main__':
    unittest.main()
