# Checks for the lettering screen's logic (no windows open: the typing dialog is replaced
# by a fake). Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import LAYOUTS, STICKERS                         # noqa: E402
from desktop.studio import BAR_H, PREVIEW, TAB_KEY, LetteringScreen     # noqa: E402


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

    def test_quit_save_and_nothing(self):
        screen = LetteringScreen()
        self.assertEqual(screen.handle_key(ord('q')), 'quit')
        self.assertEqual(screen.handle_key(ord('S')), 'save')
        self.assertIsNone(screen.handle_key(-1))

    def test_a_picture_behind_the_words(self):
        screen = LetteringScreen()
        plain = screen.cover().copy()
        screen.picture = np.full((480, 640, 3), (200, 50, 50), np.uint8)
        self.assertFalse(np.array_equal(plain, screen.cover()))
        screen.handle_key(ord('b'))
        self.assertTrue(np.array_equal(plain, screen.cover()))           # back to the placeholder


if __name__ == '__main__':
    unittest.main()
