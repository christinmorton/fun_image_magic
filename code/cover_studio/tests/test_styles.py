# Checks for the style prompt pieces (no AI is called).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.styles import (BANNED_NAMES, CUSTOM, GUARDRAILS, MAX_CREW, MAX_USER_TEXT,     # noqa: E402
                         NEW_ORLEANS, STYLES, build_prompt, check_user_text)

NEVER = BANNED_NAMES        # names that must never reach the AI


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

    def test_the_users_own_words(self):
        plain = build_prompt(NEW_ORLEANS, 'boss_office', 3)
        self.assertNotIn(GUARDRAILS, plain)                               # only when the user adds words
        detailed = build_prompt(NEW_ORLEANS, 'boss_office', 3, details='A white tiger sits beside them.')
        self.assertIn('red velvet', detailed)                            # the scene is kept...
        self.assertIn('white tiger', detailed)                           # ...with the details added
        self.assertTrue(detailed.endswith(GUARDRAILS))                   # and the rules repeated last
        custom = build_prompt(NEW_ORLEANS, CUSTOM, 3, custom_scene='On a speedboat on the lake at sunset.')
        self.assertIn('speedboat', custom)
        self.assertIn('late-1990s Southern rap album cover', custom)    # still the era's look
        self.assertNotIn('red velvet', custom)
        self.assertTrue(custom.endswith(GUARDRAILS))
        with self.assertRaises(ValueError):
            build_prompt(NEW_ORLEANS, CUSTOM, 3, custom_scene='  ')
        # words typed without a full stop don't run into the next sentence
        self.assertIn('beside them. Keep', build_prompt(NEW_ORLEANS, 'inferno', 3, details='a tiger beside them'))

    def test_checking_the_users_words(self):
        self.assertEqual(check_user_text('a white tiger and purple neon lights'), [])
        self.assertIn('gucci', check_user_text('wearing a Gucci jacket')[0])
        self.assertIn('rolls-royce', check_user_text('next to a Rolls-Royce')[0])
        self.assertIn('pen & pixel', check_user_text('in the style of Pen & Pixel')[0])
        self.assertEqual(check_user_text('a supremely shiny car'), [])   # whole words only
        self.assertIn('too long', check_user_text('x' * (MAX_USER_TEXT + 1))[0])

    def test_a_crew_prompt(self):
        three_angles = build_prompt(NEW_ORLEANS, 'crew_lineup', 3, clothing='camo', people=2)
        self.assertIn('2 different people', three_angles)
        self.assertIn('photos 1 to 3 are the first person', three_angles)
        self.assertIn('photos 4 to 6 are the second person', three_angles)
        self.assertIn('never mix their features up', three_angles)
        self.assertIn('They all wear matching camouflage jacket', three_angles)
        self.assertIn('None of them wear any jewellery', three_angles)
        self.assertIn('top of their heads', three_angles)
        fronts = build_prompt(NEW_ORLEANS, 'boss_office', 1, people=5)
        self.assertIn('photo 5 is the fifth person', fronts)
        self.assertIn('applies to the whole crew', fronts)            # the scene's "person" means all of them
        with self.assertRaises(ValueError):
            build_prompt(NEW_ORLEANS, 'inferno', 1, people=MAX_CREW + 1)

    def test_extras_and_unknown_scenes(self):
        self.assertIn('gold rope chain', build_prompt(NEW_ORLEANS, 'boss_office', extras='They wear a gold rope chain.'))
        with self.assertRaises(ValueError):
            build_prompt(NEW_ORLEANS, 'beach_party')


if __name__ == '__main__':
    unittest.main()
