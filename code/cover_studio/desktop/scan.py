#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cover Studio (desktop): the guided face scan. Asks for the person's name and their
# permission, then guides them through three angles with the webcam (front, left, right),
# capturing each one automatically, and saves them to subjects/<name>/. Photos can be
# loaded instead (P, or when there's no webcam). Free to use: no AI.
# Run from the cover_studio folder:  .\.venv\Scripts\python.exe desktop\scan.py
# To show someone already scanned the current permission wording and record their answer:
#   .\.venv\Scripts\python.exe desktop\scan.py --reconfirm <their folder in subjects\>
import ctypes
import sys
import time
from pathlib import Path
from tkinter import BooleanVar, Button, Checkbutton, Label, Tk, filedialog, messagebox

import cv2
import numpy as np

# make `core` and `desktop` importable however this file is started
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from core import MODELS_DIR                                        # noqa: E402
from core.scan import ANGLES, FaceDetector, Scanner, sort_photos   # noqa: E402
from core.subjects import (CONSENT_TEXT, SUBJECTS_DIR, has_current_consent,   # noqa: E402
                           load_subject, reconfirm_consent, save_subject)
from desktop.sources import PictureSource                          # noqa: E402
from desktop.studio import ask_text, window_closed                 # noqa: E402

WINDOW = 'Cover Studio - Scan'
BAR_H, STRIP_H = 84, 190        # the instruction bar above the camera, the captures below it
GOLD, GREEN, WHITE = (1, 207, 255), (90, 220, 120), (255, 255, 255)
MAX_PHOTO_SIDE = 2048           # loaded photos bigger than this are shrunk


def ask_consent(name):
    # a permission box: Start only works once the box is ticked. True if they agreed
    root = Tk()
    root.title('Permission')
    root.attributes('-topmost', True)
    agreed, result = BooleanVar(value=False), {'ok': False}
    def start():
        result['ok'] = True
        root.destroy()
    Label(root, text=CONSENT_TEXT.format(name=name), justify='left', wraplength=460).pack(padx=16, pady=(16, 8))
    start_button = Button(root, text='Start', width=12, state='disabled', command=start)
    Checkbutton(root, text='I confirm all of the above', variable=agreed,
                command=lambda: start_button.config(state='normal' if agreed.get() else 'disabled')).pack(padx=16, anchor='w')
    start_button.pack(side='left', padx=(16, 4), pady=14)
    Button(root, text='Cancel', width=12, command=root.destroy).pack(side='left', pady=14)
    root.mainloop()
    return result['ok']

def choose_photos():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    paths = filedialog.askopenfilenames(title='Choose photos of the person: one straight on, and one turned each way',
                                        filetypes=[('Images', '*.jpg *.jpeg *.png *.bmp *.webp'), ('All files', '*.*')])
    root.destroy()
    return list(paths)

def read_photo(path):
    # a photo at full size (big ones shrunk to MAX_PHOTO_SIDE), or None
    try:
        img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    except OSError:
        return None
    if img is not None and max(img.shape[:2]) > MAX_PHOTO_SIDE:
        scale = MAX_PHOTO_SIDE / max(img.shape[:2])
        img = cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    return img

def tell(title, text):
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showinfo(title, text, parent=root)
    root.destroy()


def draw_scan(frame, scanner, flash=False, note=''):
    # the whole window: the instruction bar, the mirrored camera with the face guide, and
    # the captured angles (no windows here, so it can be tested)
    h, w = frame.shape[:2]
    view = frame.copy()
    angle = scanner.current
    centre, axes = (w // 2, int(h * 0.48)), (int(w * 0.17), int(h * 0.32))
    holding = scanner.progress > 0
    cv2.ellipse(view, centre, axes, 0, 0, 360, GREEN if holding else WHITE, 2, cv2.LINE_AA)
    if holding:                                         # a ring that fills while the pose is held
        cv2.ellipse(view, centre, (axes[0] + 8, axes[1] + 8), 0, -90, -90 + 360 * scanner.progress, GREEN, 6, cv2.LINE_AA)
    if angle is not None and angle.key != 'front':     # an arrow the way to turn (the picture is mirrored)
        y, x = int(h * 0.48), int(w * 0.12)
        start, end = ((x + 70, y), (x, y)) if angle.key == 'left' else ((w - x - 70, y), (w - x, y))
        cv2.arrowedLine(view, start, end, GOLD, 6, cv2.LINE_AA, tipLength=0.4)
    if flash:
        view[:] = 255
    bar = np.full((BAR_H, w, 3), 30, np.uint8)
    title = angle.prompt if angle else 'All three angles captured'
    cv2.putText(bar, title, (14, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, WHITE, 2, cv2.LINE_AA)
    message = note or (scanner.message if angle else 'S save   R start again   1 2 3 redo one angle')
    cv2.putText(bar, message, (14, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.65, GREEN if holding else GOLD, 2, cv2.LINE_AA)
    strip = np.full((STRIP_H, w, 3), 30, np.uint8)
    tw = (w - 4 * 12) // 3
    th = STRIP_H - 52
    for i, a in enumerate(ANGLES):
        x = 12 + i * (tw + 12)
        if a.key in scanner.captures:
            pic = scanner.captures[a.key]
            scale = min(tw / pic.shape[1], th / pic.shape[0])
            small = cv2.resize(pic, (int(pic.shape[1] * scale), int(pic.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            ox, oy = x + (tw - small.shape[1]) // 2, 10 + (th - small.shape[0]) // 2
            strip[oy:oy + small.shape[0], ox:ox + small.shape[1]] = small
        border = GOLD if angle is not None and a.key == angle.key else (90, 90, 90)
        cv2.rectangle(strip, (x, 10), (x + tw, 10 + th), border, 2)
        cv2.putText(strip, f'{i + 1} {a.key}', (x + 4, STRIP_H - 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
    cv2.putText(strip, 'R redo all   1 2 3 redo one   P load photos instead   S save   Q quit',
                (12, STRIP_H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
    return np.vstack([bar, view, strip])


def save_from_photos(name):
    # the "load photos" way: choose photos, sort them into angles, save what fits
    photos = [p for p in (read_photo(path) for path in choose_photos()) if p is not None]
    if not photos:
        return None
    detector = FaceDetector(MODELS_DIR, still=True)
    try:
        captures, problems = sort_photos(photos, detector)
    finally:
        detector.close()
    if not captures:
        tell('No usable photos', 'No single face was found in those photos.\n\n' + '\n'.join(problems))
        return None
    folder = save_subject(name, captures, consent=True, source='photos')
    missing = [a.key for a in ANGLES if a.key not in captures]
    tell('Saved', f'Saved {", ".join(captures)} to subjects/{folder.name}.'
         + (f'\n\nNot found: {", ".join(missing)}.' if missing else '') + ('\n\n' + '\n'.join(problems) if problems else ''))
    return folder

def reconfirm(folder_name):
    # show someone already scanned the current wording, and record it if they agree
    folder = SUBJECTS_DIR / folder_name
    if not (folder / 'subject.json').is_file():
        tell('Not found', f'There is no saved subject called "{folder_name}" in subjects/.')
        return
    info, _ = load_subject(folder)
    if has_current_consent(info):
        tell('Already agreed', f'{info["name"]} has already agreed to the current wording.')
    elif ask_consent(info['name']):
        reconfirm_consent(folder)
        tell('Recorded', f'Recorded that {info["name"]} agreed to the current wording.')

def main():
    # Windows display scaling would blur the window; this keeps it sharp
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    if len(sys.argv) == 3 and sys.argv[1] == '--reconfirm':
        reconfirm(sys.argv[2])
        return
    name = (ask_text('New scan', "The person's name:") or '').strip()
    if not name or not ask_consent(name):
        return
    source = PictureSource()
    if not source.open_webcam():
        tell('No webcam', 'No webcam was found, so choose photos instead.')
        save_from_photos(name)
        return
    detector = FaceDetector(MODELS_DIR)
    scanner = Scanner(detector)
    flash_until, note = 0.0, ''
    cv2.namedWindow(WINDOW)
    cv2.moveWindow(WINDOW, 40, 20)
    try:
        while True:
            frame = source.read()                       # mirrored, like a selfie camera
            if frame is None:
                break
            scanner.feed(frame)
            if scanner.just_captured:
                flash_until = time.time() + 0.12
            cv2.imshow(WINDOW, draw_scan(frame, scanner, time.time() < flash_until, note))
            key = cv2.waitKey(1)
            if window_closed(WINDOW) or key in (ord('q'), ord('Q')):
                break
            k = chr(key & 0xFF).lower() if key != -1 else ''
            if k == 'r':
                scanner.redo()
                note = ''
            elif k in ('1', '2', '3'):
                scanner.redo(ANGLES[int(k) - 1].key)
                note = ''
            elif k == 's' and scanner.done and not note:
                folder = save_subject(name, scanner.captures, consent=True)
                note = f'Saved to subjects/{folder.name}   (Q to finish)'
            elif k == 'p':
                source.release()
                cv2.destroyWindow(WINDOW)
                save_from_photos(name)
                break
    finally:
        source.release()
        detector.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
