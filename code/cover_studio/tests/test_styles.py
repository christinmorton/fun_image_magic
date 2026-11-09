# Checks for the style prompt pieces (no AI is called).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.styles import NEW_ORLEANS, STYLES, build_prompt     # noqa: E402

# names that must never reach the AI: artists, labels, design studios, albums, marks
NEVER = ['no limit', 'cash money', 'pen & pixel', 'pen and pixel', 'master p', 'juvenile', 'lil wayne',
         'hot boys', 'mystikal', 'parental advisory', 'riaa', '400 degreez', 'rolls', 'bentley', 'mercedes']


class TestStyles(unittest.TestCase):
    def test_every_prompt_asks_for_no_text_and_names_nobody(self):
        for style in STYLES.values():
            for scene in style.scenes:
                for references in (1, 3):
                    with self.subTest(style=style.key, scene=scene, references=references):
                        prompt = build_prompt(style, scene, references)
                        self.assertIn('No text', prompt)
                        self.assertIn('top fifth and the bottom fifth', prompt)    # room for the lettering
                        self.assertIn('recognisable', prompt)
                        lower = prompt.lower()
                        for name in NEVER:
                            self.assertNotIn(name, lower)

    def test_fire_only_where_a_scene_asks_for_it(self):
        # the base goes with every scene, so it mustn't bring fire into all of them
        for style in STYLES.values():
            self.assertNotIn('fire', style.base.lower())
        prompts = {scene: build_prompt(NEW_ORLEANS, scene) for scene in NEW_ORLEANS.scenes}
        self.assertIn('flames', prompts['inferno'])
        for scene in ('boss_office', 'mansion_life', 'block_at_dusk'):
            self.assertIn('No fire or flames', prompts[scene])

    def test_one_photo_or_several_angles(self):
        one = build_prompt('new_orleans', 'inferno', 1)
        three = build_prompt('new_orleans', 'inferno', 3)
        self.assertIn('the reference photo is', one)
        self.assertIn('3 reference photos show the same person', three)

    def test_clothing_and_jewellery_are_choices(self):
        bare = build_prompt(NEW_ORLEANS, 'inferno', 3, clothing='white_tee')
        self.assertIn('white tee', bare)
        self.assertIn('no jewellery at all', bare)                       # otherwise the AI adds chains
        dressed = build_prompt(NEW_ORLEANS, 'inferno', 3, clothing='fur_coat', jewellery=('rope_chain', 'pendant'),
                               accessories=('sunglasses',))
        self.assertIn('rope chain', dressed)
        self.assertIn('no letters or logos', dressed)                    # the pendant
        self.assertIn('sunglasses', dressed)
        self.assertNotIn('no jewellery', dressed)
        self.assertNotIn('They wear', build_prompt(NEW_ORLEANS, 'inferno', 3))   # no choices: the AI decides

    def test_extras_and_unknown_scenes(self):
        self.assertIn('gold rope chain', build_prompt(NEW_ORLEANS, 'boss_office', extras='They wear a gold rope chain.'))
        with self.assertRaises(ValueError):
            build_prompt(NEW_ORLEANS, 'beach_party')


if __name__ == '__main__':
    unittest.main()
