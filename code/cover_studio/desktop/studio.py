#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cover Studio (desktop): the lettering screen. Type the words, pick a layout and styles,
# watch the cover update, and save the lettering as a print-size transparent PNG.
# Run from the cover_studio folder:  .\.venv\Scripts\python.exe desktop\studio.py
# Free to use: no AI. The picture behind the words is a placeholder, or any image (U).
import ctypes
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from tkinter import Button, Entry, Frame, Label, Tk

import cv2
import numpy as np

# make `core` and `desktop` importable however this file is started
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from core.cover_layout import (LAYOUTS, STICKERS, CoverWords, apply_lettering,              # noqa: E402
                               draw_cover_lettering, placeholder)
from core.designs import save_lettering                                                      # noqa: E402
from core import MODELS_DIR                                                                  # noqa: E402
from core.finish import FINISHES, age                                                        # noqa: E402
from core.framing import Framing, auto_framing, frame_artwork                                # noqa: E402
from core.scan import FaceDetector                                                           # noqa: E402
from core.products import export_products                                                    # noqa: E402
from core.lettering import TREATMENTS                                                        # noqa: E402
from desktop.sources import choose_image_file, load_image                                    # noqa: E402

WINDOW = 'Cover Studio'
PREVIEW = 720              # the cover on screen, in pixels
BAR_H = 160                # the dark bar above it, with the settings and keys
# arrow keys as cv2.waitKeyEx() reports them (Windows, then Linux): how they move the picture
ARROWS = {2424832: (-1, 0), 2555904: (1, 0), 2490368: (0, -1), 2621440: (0, 1),
          65361: (-1, 0), 65363: (1, 0), 65362: (0, -1), 65364: (0, 1)}
MOVE, ZOOM = 0.02, 1.05     # each press moves the picture 2% of the cover, or zooms it 5%
LAYOUT_KEYS = list(LAYOUTS)
STYLE_NAMES = list(TREATMENTS)
PARTS = ['all', 'artwork', 'name', 'title', 'presents', 'featuring', 'sticker']   # what Tab picks for A to age
TAB_KEY = 9
GOLD = (1, 207, 255)


def ask_text(title, prompt, initial=''):
    # a small window to type in, kept in front of the cover; returns None if cancelled
    root = Tk()
    root.title(title)
    root.attributes('-topmost', True)
    result = {'text': None}
    def ok(event=None):
        result['text'] = entry.get()
        root.destroy()
    Label(root, text=prompt, anchor='w', justify='left').pack(fill='x', padx=12, pady=(12, 4))
    entry = Entry(root, width=60)
    entry.insert(0, initial)
    entry.pack(padx=12, fill='x')
    buttons = Frame(root)
    buttons.pack(pady=10)
    Button(buttons, text='OK', width=10, command=ok).pack(side='left', padx=4)
    Button(buttons, text='Cancel', width=10, command=root.destroy).pack(side='left', padx=4)
    root.bind('<Return>', ok)
    root.bind('<Escape>', lambda event: root.destroy())
    entry.select_range(0, 'end')
    entry.focus_force()
    root.mainloop()
    return result['text']

def next_in(items, current, step=1):
    return items[(items.index(current) + step) % len(items)]

def window_closed(name):
    # True once the window's X button has been clicked
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True


# what each typing key edits: (field, dialog title, prompt, field -> text, text -> field)
FIELDS = {
    'n': ('name', 'Name', 'The name, big across the top:', str, str.strip),
    't': ('title', 'Title', 'The title across the bottom (leave empty for none):', str, str.strip),
    'p': ('presents', 'Presents line', 'A small line, e.g. "Big Tee presents" (leave empty for none):',
          str, str.strip),
    'f': ('featuring', 'Featuring', 'Names, separated by commas (leave empty for none):',
          ', '.join, lambda text: tuple(n.strip() for n in text.split(',') if n.strip())),
    'e': ('sticker', 'Sticker words', 'The sticker\'s lines, separated by "/" (leave empty for none):',
          ' / '.join, lambda text: tuple(line.strip() for line in text.split('/') if line.strip())),
}


class LetteringScreen:
    # everything on the lettering screen; no windows here, so it can be tested
    def __init__(self, ask=ask_text, picture=None, name='BIG MIKE', background=None, detect=None):
        self.sticker = 1                     # index into STICKERS: Hood Classic
        _, lines, look = STICKERS[self.sticker]
        self.words = CoverWords(name=name, title='BOSS LIFE', sticker=lines)
        self.layout = LAYOUT_KEYS[0]
        self.styles = {**LAYOUTS[self.layout].styles, 'sticker': look}
        self.seed = 1
        # each part aged like a 90s CD booklet, the picture ("artwork") too
        self.finishes = {part: 'print' for part in PARTS[1:]}
        self.part = 'all'                    # what A changes the finish of (Tab picks)
        self.picture = picture               # the BGR picture behind the words (None = placeholder)
        self.ask = ask                       # how to ask for text (a dialog; replaced in tests)
        self.message, self.message_until = '', 0.0
        self._layer = (None, None)           # (settings, lettering), redrawn only when they change
        self._cover = (None, None)
        self.saved = None                    # the latest saved design's folder (X exports it)
        self.exporting = False
        # print files take about a minute, so they're made in the background (not a daemon
        # thread: closing the window still lets an export finish)
        self.background = background or (lambda work: threading.Thread(target=work).start())
        # where the picture sits under the lettering: fitted automatically so the name and
        # title don't cover the face, until it's moved by hand
        self.framing, self.framing_auto = Framing(), True
        self._detect = detect                # finds faces (MediaPipe, made when first needed)
        if picture is not None:
            self.fit_picture()

    def detect(self, image):
        if self._detect is None:
            self._detect = FaceDetector(MODELS_DIR, still=True)
        return self._detect(image)

    def fit_picture(self):
        # move the picture so the layout's name and title stay off the face(s)
        self.framing, self.framing_auto = auto_framing(self.picture, self.layout, self.detect), True
        if self.framing != Framing():
            self.say('Moved the picture so the lettering doesn\'t cover the face   (arrows [ ] adjust, O undo)', 6)

    def nudge(self, dx=0.0, dy=0.0, zoom=1.0):
        # move or zoom the picture by hand
        f = self.framing
        self.framing = Framing(round(min(2.0, max(0.5, f.zoom * zoom)), 3),
                               round(min(0.5, max(-0.5, f.dx + dx)), 3), round(min(0.5, max(-0.5, f.dy + dy)), 3))
        self.framing_auto = False

    def settings(self):
        return (repr(self.words), self.layout, tuple(sorted(self.styles.items())), self.seed,
                tuple(sorted(self.finishes.items())))

    def cover(self):
        # the cover on screen: the picture with the (aged) lettering over it
        key = self.settings() + (id(self.picture), self.framing)
        if self._cover[0] != key:
            if self._layer[0] != self.settings():
                self._layer = (self.settings(), draw_cover_lettering(self.words, self.layout, PREVIEW, self.styles,
                                                                     self.seed, self.finishes))
            if self.picture is None:
                picture = placeholder(PREVIEW, 4 if self.layout == 'crew_row' else 1)
            else:
                picture = frame_artwork(self.picture, PREVIEW, self.framing)
            picture = age(picture, self.finishes['artwork'], 1.0, self.seed, unit_size=PREVIEW)
            self._cover = (key, apply_lettering(picture, self._layer[1]))
        return self._cover[1]

    def screen(self, now=None):
        # the whole window: a bar with the settings and keys, above the cover
        bar = np.full((BAR_H, PREVIEW, 3), 40, np.uint8)
        layout = LAYOUTS[self.layout]
        status = (f'{layout.name}   name: {self.styles["name"]}   title: {self.styles["title"]}   '
                  f'sticker: {STICKERS[self.sticker][0].lower()}   look #{self.seed}')
        showing_message = self.message and (now or time.time()) < self.message_until
        cv2.putText(bar, self.message if showing_message else status, (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    GOLD if showing_message else (255, 255, 255), 2, cv2.LINE_AA)
        # each part's finish, with the part that A changes in gold (smaller text if it's long)
        texts = ['finish:'] + [f'{part} {self.finishes[part]}' for part in PARTS[1:]]
        wide = sum(cv2.getTextSize(t, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0][0] + 12 for t in texts)
        scale, x = min(0.5, 0.5 * (PREVIEW - 28) / wide), 14
        for i, text in enumerate(texts):
            chosen = i > 0 and self.part in ('all', PARTS[i])
            cv2.putText(bar, text, (x, 56), cv2.FONT_HERSHEY_SIMPLEX, scale, GOLD if chosen else (200, 200, 200),
                        2 if chosen else 1, cv2.LINE_AA)
            x += cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)[0][0] + int(12 * scale / 0.5)
        hints = ['N name   T title   P presents   F featuring   E sticker words   K sticker',
                 'L layout   1 name style   2 title style   TAB part   A finish   R reshuffle',
                 'U picture   B plain   S save   X print files   Q quit',
                 'Arrows move the picture   [ ] zoom out / in   Z fit to the lettering   O as made']
        for i, hint in enumerate(hints):
            cv2.putText(bar, hint, (14, 84 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        return np.vstack([bar, self.cover()])

    def say(self, text, seconds=4):
        self.message, self.message_until = text, time.time() + seconds

    def edit(self, key):
        field, title, prompt, to_text, from_text = FIELDS[key]
        text = self.ask(title, prompt, to_text(getattr(self.words, field)))
        if text is not None:                 # None = cancelled: keep what was there
            self.words = replace(self.words, **{field: from_text(text)})

    def handle_key(self, key):
        # one key press; returns 'quit', 'save' or None
        if key == -1:
            return None
        if key in ARROWS or chr(key & 0xFF) in '[]zZoO':
            self.frame_key(key)
            return None
        if key & 0xFF == TAB_KEY:
            self.part = next_in(PARTS, self.part)
            self.say(f'A now changes the finish of: {self.part}')
            return None
        k = chr(key & 0xFF).lower()
        if k == 'q':
            return 'quit'
        if k == 's':
            return 'save'
        if k in FIELDS:
            self.edit(k)
        elif k == 'l':
            self.layout = next_in(LAYOUT_KEYS, self.layout)
            # each layout starts with its own name and title styles; the sticker stays
            self.styles = {**LAYOUTS[self.layout].styles, 'sticker': self.styles['sticker']}
            self.say(f'{LAYOUTS[self.layout].name} layout')
            if self.picture is not None and self.framing_auto:
                self.fit_picture()           # the name and title moved: fit the picture again
        elif k == 'k':
            self.sticker = (self.sticker + 1) % len(STICKERS)
            name, lines, look = STICKERS[self.sticker]
            self.words = replace(self.words, sticker=lines)
            self.styles['sticker'] = look
            self.say(f'Sticker: {name}' + ('   (E changes its words)' if lines else ''))
        elif k == '1':
            self.styles['name'] = next_in(STYLE_NAMES, self.styles['name'])
        elif k == '2':
            self.styles['title'] = next_in(STYLE_NAMES, self.styles['title'])
        elif k == 'a':
            parts = PARTS[1:] if self.part == 'all' else [self.part]
            new = next_in(FINISHES, self.finishes[parts[-1]])
            for piece in parts:
                self.finishes[piece] = new
            self.say(f'Finish of {self.part}: {new}')
        elif k == 'r':
            self.seed += 1                   # new sparkles, gems, burn marks and grain
        elif k == 'u':
            path = choose_image_file()
            image = load_image(path) if path else None
            if image is not None:
                self.picture = image
                self.fit_picture()
            elif path:
                self.say('Could not open that picture')
        elif k == 'b':
            self.picture, self.framing, self.framing_auto = None, Framing(), True
        elif k == 'x':
            self.start_export()
        return None

    def frame_key(self, key):
        # arrows move the picture, [ ] zoom it, Z fits it to the lettering, O puts it back
        if self.picture is None:
            self.say('The placeholder can\'t be moved: these keys move real artwork')
            return
        k = chr(key & 0xFF).lower()
        if key in ARROWS:
            dx, dy = ARROWS[key]
            self.nudge(dx=dx * MOVE, dy=dy * MOVE)
        elif k == '[':
            self.nudge(zoom=1 / ZOOM)
        elif k == ']':
            self.nudge(zoom=ZOOM)
        elif k == 'z':
            self.fit_picture()
            if self.framing == Framing():
                self.say('The lettering already clears the face')
        elif k == 'o':
            self.framing, self.framing_auto = Framing(), False
            self.say('The picture is back as the AI made it')

    def save(self):
        self.saved = save_lettering(self.words, self.layout, self.styles, self.seed, self.picture,
                                    finishes=self.finishes, framing=self.framing)
        return self.saved

    def start_export(self):
        # the latest saved design's print files and mockups, made in the background
        if self.exporting:
            self.say('Still making the print files...')
            return
        if self.saved is None:
            self.say('Save the design first (S), then X makes its print files')
            return
        self.exporting = True
        folder = self.saved
        def work():
            try:
                out = export_products(folder, progress=lambda text: self.say(text, 300))
                self.say(f'Print files and mockups are in exports/{out.name}', 12)
            except Exception as error:
                self.say(f'The print files failed: {type(error).__name__}: {error}'[:100], 12)
            finally:
                self.exporting = False
        self.background(work)


def main(picture=None, name='BIG MIKE'):
    # picture: artwork to letter (from desktop/artwork.py), or None for the placeholder
    # Windows display scaling would blur the window; this keeps it sharp
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    screen = LetteringScreen(picture=picture, name=name)
    cv2.namedWindow(WINDOW)
    cv2.moveWindow(WINDOW, 40, 20)
    while True:
        cv2.imshow(WINDOW, screen.screen())
        key = cv2.waitKeyEx(30)              # Ex: tells the arrow keys apart
        if window_closed(WINDOW):
            break
        action = screen.handle_key(key)
        if action == 'quit':
            break
        if action == 'save':
            screen.say('Saving the print file...', 120)
            cv2.imshow(WINDOW, screen.screen())
            cv2.waitKey(1)                   # show the message before the slow part
            start = time.perf_counter()
            folder = screen.save()
            screen.say(f'Saved designs/{folder.name} ({time.perf_counter() - start:.1f} s)', 8)
    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
