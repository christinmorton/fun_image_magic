#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cover Studio (desktop): the mockup tool. Goes through the photos in mockup_photos/ (people
# wearing blank garments), shows where a design would be printed on each with a sample
# design, and lets the guess be fixed: drag the corners, change the product, front or back,
# or skip the photo. A sets up every new photo at once; D picks any design PNG and W puts it
# on every set-up photo of the same product. Free to use: no AI.
# Run from the cover_studio folder:  .\.venv\Scripts\python.exe desktop\mockup_tool.py
# The models it needs are fetched once with  .\.venv\Scripts\python.exe tools\get_mockup_models.py
import ctypes
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path

import cv2
import numpy as np

# make `core` and `desktop` importable however this file is started
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import placeholder                                                   # noqa: E402
from core.photo_mockups import (MOCKUP_PHOTOS_DIR, BodyFinder, Placement, default_corners,   # noqa: E402
                                fit_design, guess, list_photos, load_clothes, load_placement, make_photo_mockups,
                                print_on, print_size_in, product_from_name, read_photo, refit, save_placement)
from core.products import EXPORTS_DIR, PRODUCTS_BY_KEY                                      # noqa: E402
from desktop.sources import choose_image_file                                               # noqa: E402
from desktop.studio import ARROWS, window_closed                                            # noqa: E402

WINDOW = 'Cover Studio - Mockups'
VIEW = 860                 # the photo on screen, longest side in pixels
BAR_H = 150                # the dark bar above it
GRAB = 18                  # how close (screen pixels) a click must be to grab a corner
GARMENTS = ['tee', 'sweatshirt', 'hoodie']
GOLD, GREEN, RED, WHITE = (1, 207, 255), (90, 220, 120), (80, 80, 255), (255, 255, 255)
STATUS_COLOURS = {'good': GREEN, 'set': GREEN, 'check': GOLD, 'skip': (150, 150, 150), None: RED}
STATUS_WORDS = {'good': 'guessed, looks right', 'set': 'set by hand', 'check': 'guessed: check it',
                'skip': 'skipped', None: 'not set up yet (G guesses, or drag the corners)'}


def sample_design(product):
    # a stand-in design shaped like the product's print file: the square cover at the top,
    # see-through below, as a garment print file has it
    w_in, h_in = print_size_in(product)
    w = 400
    h = round(w * h_in / w_in)
    out = np.zeros((h, w, 4), np.uint8)
    side = min(w, h, round(w * product.cover_in / w_in) if product.cover_in else w)
    x = (w - side) // 2
    out[:side, x:x + side, :3] = placeholder(side)
    out[:side, x:x + side, 3] = 255
    return out


class MockupTool:
    # everything in the mockup tool's window; no windows here, so it can be tested
    def __init__(self, folder=MOCKUP_PHOTOS_DIR, finder=None, background=None, exports_dir=EXPORTS_DIR,
                 choose_file=choose_image_file):
        self.folder = folder
        self.photos = list_photos(folder)
        self.index = 0
        self._finder = finder                # MediaPipe, made when first needed
        self.background = background or (lambda work: threading.Thread(target=work, daemon=True).start())
        self.exports_dir = exports_dir
        self.choose_file = choose_file       # how to pick a design (a dialog; replaced in tests)
        self.design, self.design_name = None, ''   # a chosen design PNG (None: the sample)
        self.message, self.message_until = '', 0.0
        self.busy = False                    # guessing every photo, or writing mockups
        self.drag = None                     # (corner index, or 'all', last point) while dragging
        self._photo = (None, None, None)     # (path, photo, clothes mask) of the photo on screen
        self._view = (None, None)            # (key, picture on screen), redrawn only when it changes
        self.placement = None
        self.load()

    # --- the photo on screen ---

    @property
    def path(self):
        return self.photos[self.index] if self.photos else None

    def load(self):
        self.placement = load_placement(self.path) if self.path else None
        self.drag = None

    def photo(self):
        # the current photo at full size, and its clothes mask (None if it hasn't been guessed)
        if self._photo[0] != self.path:
            self._photo = (self.path, read_photo(self.path), load_clothes(self.path))
        return self._photo[1], self._photo[2]

    def scale(self):
        photo, _ = self.photo()
        return VIEW / max(photo.shape[:2])

    def finder(self):
        if self._finder is None:
            self._finder = BodyFinder()
        return self._finder

    def product(self):
        key = self.placement.product if self.placement else product_from_name(self.path)
        return PRODUCTS_BY_KEY[key]

    def go(self, step):
        if self.photos:
            self.index = (self.index + step) % len(self.photos)
            self.load()

    def say(self, text, seconds=4):
        self.message, self.message_until = text, time.time() + seconds

    def save(self, placement):
        self.placement = placement
        save_placement(self.path, placement)

    # --- drawing ---

    def picture(self):
        # the photo on screen with the design printed where it would go, and the corners
        photo, clothes = self.photo()
        s = self.scale()
        p = self.placement
        key = (self.path, p, id(self.design), self.drag is not None, self._photo[2] is not None)
        if self._view[0] != key:
            view = cv2.resize(photo, (round(photo.shape[1] * s), round(photo.shape[0] * s)), interpolation=cv2.INTER_AREA)
            if p is not None and self.drag is None and p.status != 'skip':
                design = sample_design(self.product()) if self.design is None else fit_design(self.design, self.product())
                small = None if clothes is None else cv2.resize(clothes, (view.shape[1], view.shape[0]),
                                                                interpolation=cv2.INTER_NEAREST)
                view = print_on(view, [(x * s, y * s) for x, y in p.corners], design, small, p.dark)
            self._view = (key, view)
        view = self._view[1].copy()
        corners = self.placement.corners if self.placement else None
        if corners is not None:
            points = np.round(np.array(corners) * s).astype(np.int32)
            colour = STATUS_COLOURS[self.placement.status]
            cv2.polylines(view, [points], True, colour, 2, cv2.LINE_AA)
            for x, y in points:
                cv2.circle(view, (int(x), int(y)), 7, colour, -1, cv2.LINE_AA)
                cv2.circle(view, (int(x), int(y)), 7, (0, 0, 0), 1, cv2.LINE_AA)
        return view

    def screen(self, now=None):
        # the whole window: a bar with the photo's set-up and the keys, above the photo
        if not self.photos:
            out = np.full((BAR_H + 300, VIEW, 3), 40, np.uint8)
            lines = ['No mockup photos yet.', f'Put them in {self.folder}',
                     '(sub-folders named tee, sweatshirt or hoodie help), then start this again.', 'Q quit']
            for i, line in enumerate(lines):
                cv2.putText(out, line, (20, 60 + 40 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.65, WHITE, 1, cv2.LINE_AA)
            return out
        view = self.picture()
        width = max(VIEW, view.shape[1])
        bar = np.full((BAR_H, width, 3), 40, np.uint8)
        p = self.placement
        status = p.status if p else None
        title = f'{self.index + 1}/{len(self.photos)}   {self.path.relative_to(self.folder)}'
        cv2.putText(bar, title[:95], (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
        about = f'{self.product().key}   {p.view if p else "front"}   {"dark" if p and p.dark else "light"} garment   '
        cv2.putText(bar, about, (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, WHITE, 1, cv2.LINE_AA)
        x = 14 + cv2.getTextSize(about, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)[0][0]
        cv2.putText(bar, STATUS_WORDS[status], (x, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, STATUS_COLOURS[status], 2, cv2.LINE_AA)
        showing = self.message and (now or time.time()) < self.message_until
        line = self.message if showing else ('; '.join(p.notes) if p and p.notes else
                                             f'design: {self.design_name or "the sample"}')
        cv2.putText(bar, line[:110], (14, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GOLD, 1, cv2.LINE_AA)
        hints = ['<- -> photos   F next to check   G guess this one   A guess all new ones   drag corners or the middle',
                 'C looks right   T product   V front/back   S skip   D choose a design   W write mockups   Q quit']
        for i, hint in enumerate(hints):
            cv2.putText(bar, hint, (14, 108 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)
        if view.shape[1] < width:
            view = np.hstack([view, np.full((view.shape[0], width - view.shape[1], 3), 40, np.uint8)])
        return np.vstack([bar, view])

    # --- keys ---

    def handle_key(self, key):
        # one key press; returns 'quit' or None
        if key == -1:
            return None
        if key in ARROWS:
            dx, dy = ARROWS[key]
            self.go(dx or dy)
            return None
        k = chr(key & 0xFF).lower()
        if k == 'q':
            return 'quit'
        if not self.photos:
            return None
        if self.busy and k in 'gaw':
            self.say('Still working...')
            return None
        if k in ' .':
            self.go(1)
        elif k == ',':
            self.go(-1)
        elif k == 'f':
            self.next_to_check()
        elif k == 'g':
            self.guess_this()
        elif k == 'a':
            self.guess_all()
        elif k in ('c', '\r'):
            if self.placement:
                self.save(replace(self.placement, status='set'))
                self.go(1)
        elif k == 't':
            product = PRODUCTS_BY_KEY[GARMENTS[(GARMENTS.index(self.product().key) + 1) % len(GARMENTS)]]
            placement = self.placement or self.default_placement()
            self.save(refit(placement, product))
            self.say(f'Product: {product.name}')
        elif k == 'v':
            placement = self.placement or self.default_placement()
            self.save(replace(placement, view='back' if placement.view == 'front' else 'front'))
        elif k == 's':
            placement = self.placement or self.default_placement()
            self.save(replace(placement, status='check' if placement.status == 'skip' else 'skip'))
            if self.placement.status == 'skip':
                self.go(1)
        elif k == 'd':
            self.choose_design()
        elif k == 'w':
            self.write_mockups()
        return None

    def default_placement(self):
        photo, _ = self.photo()
        product = self.product()
        return Placement(product.key, default_corners(print_size_in(product), photo.shape), status='check')

    def next_to_check(self):
        # the next photo that's not set up or needs a look
        for step in range(1, len(self.photos) + 1):
            i = (self.index + step) % len(self.photos)
            p = load_placement(self.photos[i])
            if p is None or p.status == 'check':
                self.index = i
                self.load()
                return
        self.say('Every photo is set up')

    def guess_this(self):
        product = self.placement.product if self.placement else None
        self.say('Guessing...', 30)
        self.placement = guess(self.path, self.finder(), PRODUCTS_BY_KEY, product)
        self._photo = (None, None, None)     # the new clothes mask
        self.say('Guessed: looks right' if self.placement.status == 'good' else 'Guessed: check it')

    def guess_all(self):
        # set up every photo that isn't yet, in the background, then go to the first to check
        todo = [p for p in self.photos if load_placement(p) is None]
        if not todo:
            self.say('Every photo is already set up (G guesses one again)')
            return
        self.busy = True
        def work():
            try:
                checks = 0
                for i, path in enumerate(todo):
                    self.say(f'Guessing {i + 1} of {len(todo)}: {path.name}', 60)
                    checks += guess(path, self.finder(), PRODUCTS_BY_KEY).status == 'check'
                self.say(f'Set up {len(todo)} photos: {checks} to check (F goes to the next one)', 12)
            except Exception as error:
                self.say(f'Guessing failed: {type(error).__name__}: {error}'[:100], 12)
            finally:
                self.busy = False
                self._photo = (None, None, None)     # the new clothes masks
                self.load()
        self.background(work)

    def choose_design(self):
        path = self.choose_file()
        if not path:
            return
        try:
            design = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_UNCHANGED)
        except OSError:
            design = None
        if design is None or design.ndim != 3:
            self.say('Could not open that design')
            return
        self.design, self.design_name = design, Path(path).name
        self.say(f'Design: {self.design_name}   (W puts it on every {self.product().key} photo)')

    def write_mockups(self):
        # the chosen design on every set-up front photo of the current photo's product
        if self.design is None:
            self.say('Choose a design first (D): a print file like exports\\<design>\\tee.png')
            return
        key = self.product().key
        out = self.exports_dir / f'mockups-{Path(self.design_name).stem}'
        self.busy = True
        design = fit_design(self.design, self.product())
        def work():
            try:
                written = make_photo_mockups({key: design}, out, self.folder, limit=None,
                                             progress=lambda text: self.say(text, 60))
                self.say(f'Wrote {len(written)} {key} mockups to exports\\{out.name}' if written else
                         f'No {key} photos are set up as front views yet', 12)
            except Exception as error:
                self.say(f'Writing mockups failed: {type(error).__name__}: {error}'[:100], 12)
            finally:
                self.busy = False
        self.background(work)

    # --- the mouse ---

    def handle_mouse(self, event, x, y):
        # drag a corner, or the middle to move the whole print area; letting go saves it
        if not self.photos:
            return
        s = self.scale()
        y -= BAR_H
        point = np.array([x / s, y / s])
        if event == cv2.EVENT_LBUTTONDOWN:
            placement = self.placement or self.default_placement()
            corners = np.array(placement.corners)
            distances = np.linalg.norm(corners - point, axis=1) * s
            if distances.min() <= GRAB:
                self.drag = (int(distances.argmin()), point)
            elif cv2.pointPolygonTest(corners.astype(np.float32), (float(point[0]), float(point[1])), False) >= 0:
                self.drag = ('all', point)
            else:
                return
            self.placement = placement
        elif event == cv2.EVENT_MOUSEMOVE and self.drag is not None:
            which, last = self.drag
            corners = np.array(self.placement.corners)
            if which == 'all':
                corners += point - last
            else:
                corners[which] = point
            self.placement = replace(self.placement, corners=tuple((float(a), float(b)) for a, b in corners))
            self.drag = (which, point)
        elif event == cv2.EVENT_LBUTTONUP and self.drag is not None:
            self.drag = None
            self.save(replace(self.placement, status='set', notes=()))


def main():
    # Windows display scaling would blur the window; this keeps it sharp
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    MOCKUP_PHOTOS_DIR.mkdir(exist_ok=True)
    tool = MockupTool()
    cv2.namedWindow(WINDOW)
    cv2.moveWindow(WINDOW, 40, 20)
    cv2.setMouseCallback(WINDOW, lambda event, x, y, flags, param: tool.handle_mouse(event, x, y))
    while True:
        cv2.imshow(WINDOW, tool.screen())
        key = cv2.waitKeyEx(30)              # Ex: tells the arrow keys apart
        if window_closed(WINDOW):
            break
        if tool.handle_key(key) == 'quit':
            break
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
