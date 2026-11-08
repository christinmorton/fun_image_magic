# subjects: the people who have been scanned, each in their own folder in subjects/ (kept
# on this machine, never committed): one JPEG per angle (front.jpg, left.jpg, right.jpg)
# and subject.json (name, when, consent, how they were captured). A subject is only saved
# with the person's permission, and is deleted once their designs are done.
import json
import shutil
from datetime import datetime

import cv2

from . import CORE_DIR
from .designs import slug

SUBJECTS_DIR = CORE_DIR.parent / 'subjects'


def save_subject(name, captures, consent, source='scan', subjects_dir=SUBJECTS_DIR):
    # captures: angle key -> BGR picture. Returns the new folder
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
    now = datetime.now().isoformat(timespec='seconds')
    info = {'name': name, 'created': now, 'consent': True, 'consent_given': now,
            'source': source, 'angles': list(captures)}
    (folder / 'subject.json').write_text(json.dumps(info, indent=2), encoding='utf-8')
    return folder

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
