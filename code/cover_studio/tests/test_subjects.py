# Checks for saving scanned people (no webcam or windows needed).
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

from core.subjects import (CONSENT_VERSION, delete_subject, has_current_consent,     # noqa: E402
                           list_subjects, load_subject, reconfirm_consent, save_subject)

CAPTURES = {key: np.full((60, 80, 3), value, np.uint8) for key, value in [('front', 40), ('left', 120), ('right', 200)]}


class TestSubjects(unittest.TestCase):
    def test_save_load_list_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            folder = save_subject('Big Mike', CAPTURES, consent=True, subjects_dir=home)
            self.assertEqual(folder.name, 'big-mike')
            info, pictures = load_subject(folder)
            self.assertEqual((info['name'], info['consent'], info['source'], info['angles']),
                             ('Big Mike', True, 'scan', ['front', 'left', 'right']))
            self.assertAlmostEqual(float(pictures['left'].mean()), 120, delta=2)     # JPEG, so nearly equal
            second = save_subject('Big Mike', {'front': CAPTURES['front']}, consent=True, source='photos',
                                  subjects_dir=home)
            self.assertEqual(second.name, 'big-mike-2')                              # never overwrites
            self.assertEqual(list_subjects(home), [folder, second])
            delete_subject(folder, home)
            self.assertEqual(list_subjects(home), [second])

    def test_the_exact_permission_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_subject('Big Mike', CAPTURES, consent=True, subjects_dir=Path(tmp))
            info, _ = load_subject(folder)
            self.assertEqual(info['consent_version'], CONSENT_VERSION)
            self.assertIn('Big Mike has agreed', info['consent_text'])
            self.assertIn("Google's Gemini image AI", info['consent_text'])      # they know where photos go
            self.assertTrue(has_current_consent(info))

    def test_older_permission_needs_confirming_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = save_subject('Big Mike', CAPTURES, consent=True, subjects_dir=Path(tmp))
            path = folder / 'subject.json'
            old = json.loads(path.read_text(encoding='utf-8'))
            for key in ('consent_version', 'consent_text'):                       # saved before the AI wording
                del old[key]
            path.write_text(json.dumps(old), encoding='utf-8')
            self.assertFalse(has_current_consent(load_subject(folder)[0]))
            reconfirm_consent(folder)
            self.assertTrue(has_current_consent(load_subject(folder)[0]))

    def test_never_without_permission_or_pictures(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                save_subject('Big Mike', CAPTURES, consent=False, subjects_dir=Path(tmp))
            with self.assertRaises(ValueError):
                save_subject('Big Mike', {}, consent=True, subjects_dir=Path(tmp))
            self.assertEqual(list_subjects(Path(tmp)), [])

    def test_delete_only_touches_subjects(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / 'subjects'
            outside = Path(tmp) / 'other'
            outside.mkdir()
            (outside / 'subject.json').write_text('{}', encoding='utf-8')
            with self.assertRaises(ValueError):
                delete_subject(outside, home)
            self.assertTrue(outside.exists())


if __name__ == '__main__':
    unittest.main()
