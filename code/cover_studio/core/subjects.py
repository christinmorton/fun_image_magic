# subjects: the people who have been scanned, each in their own folder in subjects/ (kept
# on this machine, never committed): one JPEG per angle (front.jpg, left.jpg, right.jpg)
# and subject.json (name, when, the exact permission they gave, how they were captured).
# A subject is only saved with the person's permission, and is deleted once their
# designs are done.
import json
import shutil
from datetime import datetime

import cv2

from . import CORE_DIR
from .designs import slug

SUBJECTS_DIR = CORE_DIR.parent / 'subjects'

# what the person agrees to; saved with them, word for word. Raise the version whenever
# the wording changes in a way they should agree to again
CONSENT_VERSION = 2
CONSENT_TEXT = (
    '{name} has agreed to have their face scanned, and to it being used for their own designs.\n\n'
    "To make the artwork, their photos are sent to Google's Gemini image AI. Under Google's paid-tier "
    'terms, Google does not use them to improve its products, and keeps them only for a limited time '
    'to check for misuse.\n\n'
    'They are not under 18, and not a celebrity or other public figure.\n\n'
    'The photos are kept on this computer, and deleted once their designs are done.'
)


def consent_record(name):
    now = datetime.now().isoformat(timespec='seconds')
    return {'consent': True, 'consent_given': now, 'consent_version': CONSENT_VERSION,
            'consent_text': CONSENT_TEXT.format(name=name)}

def has_current_consent(info):
    # did they agree to the current wording (which covers sending photos to the image AI)?
    return info.get('consent') is True and info.get('consent_version', 1) >= CONSENT_VERSION

def save_subject(name, captures, consent, source='scan', subjects_dir=SUBJECTS_DIR):
    # captures: angle key -> BGR picture. consent: they agreed to CONSENT_TEXT. Returns
    # the new folder
    if not consent:
        raise ValueError('a person is only saved with their permission')
    if not captures:
        raise ValueError('there are no pictures to save')
    folder, n = subjects_dir / slug(name), 2
    while folder.exists():
        folder, n = subjects_dir / f'{slug(name)}-{n}', n + 1
    folder.mkdir(parents=True)
    for key, picture in captures.items():
        cv2.imwrite(str(folder / f'{key}.jpg'), picture, [cv2.IMWRITE_JPEG_QUALITY, 95])
    info = {'name': name, 'created': datetime.now().isoformat(timespec='seconds'), **consent_record(name),
            'source': source, 'angles': list(captures)}
    (folder / 'subject.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return folder

def reconfirm_consent(folder):
    # record that the person has agreed to the current wording (after being shown it)
    path = folder / 'subject.json'
    info = json.loads(path.read_text(encoding='utf-8'))
    info.update(consent_record(info['name']))
    path.write_text(json.dumps(info, indent=2), encoding='utf-8')
    return info

def load_subject(folder):
    # (info, {angle key: BGR picture}) for a saved subject
    info = json.loads((folder / 'subject.json').read_text(encoding='utf-8'))
    return info, {key: cv2.imread(str(folder / f'{key}.jpg')) for key in info['angles']}

def list_subjects(subjects_dir=SUBJECTS_DIR):
    # every saved subject's folder, oldest name first
    if not subjects_dir.exists():
        return []
    return sorted(f for f in subjects_dir.iterdir() if (f / 'subject.json').is_file())

def delete_subject(folder, subjects_dir=SUBJECTS_DIR):
    # removes a subject's pictures and details for good (only folders inside subjects_dir)
    folder = folder.resolve()
    if folder.parent != subjects_dir.resolve() or not (folder / 'subject.json').is_file():
        raise ValueError(f'{folder} is not a saved subject')
    shutil.rmtree(folder)
