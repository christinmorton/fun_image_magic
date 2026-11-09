# Checks for the artwork screen's logic, with a fake image AI and no windows: the yes/no
# box and the checklist are replaced, and "background" work runs straight away.
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.spending import Spending                                  # noqa: E402
from core.subjects import save_subject                              # noqa: E402
from desktop.artwork import ArtworkScreen                           # noqa: E402
from test_artwork import PICTURES, FakeGenerator                    # noqa: E402


class TestArtworkScreen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        self.folder = save_subject('Big Mike', PICTURES, consent=True, subjects_dir=home / 'subjects')
        self.spending = Spending(home / 'spending.json', limit=1.0)
        self.generator = FakeGenerator()
        self.answers = []                                           # what the yes/no box says

    def tearDown(self):
        self.tmp.cleanup()

    def screen(self, **extra):
        typed = extra.get('typed', [])                              # what the text boxes "type", in order
        return ArtworkScreen(self.folder, lambda: self.generator, self.spending,
                             confirm=lambda question: self.answers.pop(0) if self.answers else True,
                             choose_extras=extra.get('choose_extras', lambda j, a: (('rope_chain',), ('sunglasses',))),
                             background=lambda work: work(),
                             ask=lambda title, prompt, initial='': typed.pop(0) if typed else None)

    def test_details_and_a_custom_scene(self):
        screen = self.screen(typed=['A white tiger beside them.', 'On a speedboat at sunset.'])
        screen.handle_key(ord('d'))
        self.assertEqual(screen.request.details, 'A white tiger beside them.')
        while screen.request.scene != 'custom':                     # S round to Custom asks for the scene
            screen.handle_key(ord('s'))
        self.assertEqual(screen.request.custom_scene, 'On a speedboat at sunset.')
        self.assertEqual(screen.scene_name(), 'Custom')
        screen.handle_key(ord('g'))
        screen.poll()
        self.assertIn('speedboat', self.generator.calls[0][0])
        self.assertIn('white tiger', self.generator.calls[0][0])

    def test_cancelling_the_custom_scene_moves_on(self):
        screen = self.screen(typed=[])                              # every text box is cancelled
        scenes = screen.scenes()
        for _ in range(len(scenes) - 1):
            screen.handle_key(ord('s'))
        self.assertEqual(screen.request.scene, scenes[0])           # skipped Custom, back to the first

    def test_banned_words_are_refused_before_asking(self):
        self.answers = []
        asked = []
        screen = ArtworkScreen(self.folder, lambda: self.generator, self.spending,
                               confirm=lambda question: asked.append(question) or True,
                               background=lambda work: work(), ask=lambda *a: 'Wearing Gucci everything.')
        screen.handle_key(ord('d'))
        self.assertIn('gucci', screen.message)
        screen.handle_key(ord('g'))
        self.assertEqual((asked, self.generator.calls), ([], []))  # not even the cost question
        self.assertIn('Fix your words', screen.message)

    def test_choices_change_the_request(self):
        screen = self.screen()
        start = screen.request
        for key in 'scj':
            screen.handle_key(ord(key))
        self.assertNotEqual(screen.request.scene, start.scene)
        self.assertNotEqual(screen.request.clothing, start.clothing)
        self.assertEqual((screen.request.jewellery, screen.request.accessories), (('rope_chain',), ('sunglasses',)))

    def test_previews_pick_final_and_letter(self):
        screen = self.screen()
        self.assertEqual(screen.handle_key(ord('l')), None)        # nothing picked yet
        screen.handle_key(ord('g'))
        screen.poll()
        self.assertEqual(len(screen.results), 4)
        self.assertEqual(len(self.generator.calls), 4)
        saved = sorted(p.name for p in screen.set_folder.iterdir())
        self.assertIn('preview_1.png', saved)
        self.assertIn('request.json', saved)
        screen.handle_key(ord('3'))
        self.assertEqual(screen.picked, 3)
        screen.handle_key(ord('f'))
        screen.poll()
        self.assertIn(3, screen.finals)
        self.assertEqual(self.generator.calls[-1][3], '2K')
        self.assertTrue((screen.set_folder / 'final_3_2K.png').exists())
        self.assertIs(screen.chosen(), screen.finals[3])            # the final, not the preview
        self.assertEqual(screen.handle_key(ord('l')), 'letter')
        self.assertGreater(self.spending.spent_today(), 0.2)

    def test_saying_no_sends_nothing(self):
        self.answers = [False]
        screen = self.screen()
        screen.handle_key(ord('g'))
        screen.poll()
        self.assertEqual((self.generator.calls, screen.results), ([], []))
        self.assertEqual(self.spending.spent_today(), 0)

    def test_over_the_limit_sends_nothing(self):
        self.spending.limit = 0.05
        screen = self.screen()
        screen.handle_key(ord('g'))
        self.assertEqual(self.generator.calls, [])
        self.assertIn('limit', screen.message)

    def test_old_permission_sends_nothing(self):
        path = self.folder / 'subject.json'
        info = json.loads(path.read_text(encoding='utf-8'))
        del info['consent_version']
        path.write_text(json.dumps(info), encoding='utf-8')
        screen = self.screen()
        screen.handle_key(ord('g'))
        self.assertEqual(self.generator.calls, [])
        self.assertIn('reconfirm', screen.message)

    def test_keys_wait_while_the_ai_works(self):
        held = []
        screen = ArtworkScreen(self.folder, lambda: self.generator, self.spending, confirm=lambda q: True,
                               background=held.append)              # the work waits until we run it
        screen.handle_key(ord('g'))
        self.assertTrue(screen.busy)
        screen.handle_key(ord('s'))
        self.assertIn('Wait', screen.message)
        self.assertEqual(screen.screen().shape[2], 3)               # shows the timer while busy
        held[0]()
        screen.poll()
        self.assertIsNone(screen.busy)
        self.assertEqual(len(screen.results), 4)

    def test_a_crew(self):
        other = save_subject('Lil Ray', PICTURES, consent=True, subjects_dir=self.folder.parent)
        solo = self.screen()
        self.assertNotIn('crew_lineup', solo.scenes())                      # crew scenes only for crews
        crew = ArtworkScreen([self.folder, other], lambda: self.generator, self.spending, confirm=lambda q: True,
                             background=lambda work: work())
        self.assertTrue(crew.crew)
        self.assertEqual((crew.request.scene, crew.names()), ('crew_lineup', 'Big Mike, Lil Ray'))
        crew.handle_key(ord('g'))
        crew.poll()
        self.assertEqual(len(self.generator.calls[0][1]), 6)                 # both people's three angles
        self.assertEqual(crew.set_folder.parent.parent.name, '_crews')      # kept apart from each person
        info = json.loads((crew.set_folder / 'request.json').read_text(encoding='utf-8'))
        self.assertEqual(info['members'], ['Big Mike', 'Lil Ray'])
        self.assertEqual(crew.screen().shape, solo.screen().shape)

    def test_everyone_in_a_crew_must_have_agreed(self):
        other = save_subject('Lil Ray', PICTURES, consent=True, subjects_dir=self.folder.parent)
        path = other / 'subject.json'
        info = json.loads(path.read_text(encoding='utf-8'))
        del info['consent_version']
        path.write_text(json.dumps(info), encoding='utf-8')
        crew = ArtworkScreen([self.folder, other], lambda: self.generator, self.spending, confirm=lambda q: True,
                             background=lambda work: work())
        crew.handle_key(ord('g'))
        self.assertEqual(self.generator.calls, [])
        self.assertIn('Lil Ray', crew.message)

    def test_screen_draws_before_and_after(self):
        screen = self.screen()
        before = screen.screen()
        screen.handle_key(ord('g'))
        screen.poll()
        screen.handle_key(ord('1'))
        self.assertEqual(screen.screen().shape, before.shape)


if __name__ == '__main__':
    unittest.main()
