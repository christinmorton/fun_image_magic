#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cover Studio (desktop): the lettering screen. Type the words, pick a layout and styles,
# watch the cover update, and save the lettering as a print-size transparent PNG.
# Run from the cover_studio folder:  .\.venv\Scripts\python.exe desktop\studio.py
# Free to use: no AI. The picture behind the words is a placeholder, or any image (U).
import ctypes
import sys
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

from core.cover_layout import (LAYOUTS, CoverWords, apply_lettering, draw_cover_lettering,   # noqa: E402
                               placeholder, square_crop)
from core.designs import save_lettering                                                      # noqa: E402
from core.finish import FINISHES, age                                                        # noqa: E402
from core.lettering import TREATMENTS                                                        # noqa: E402
from desktop.sources import choose_image_file, load_image                                    # noqa: E402

WINDOW = 'Cover Studio'
PREVIEW = 720              # the cover on screen, in pixels
BAR_H = 112                # the dark bar above it, with the settings and keys
LAYOUT_KEYS = list(LAYOUTS)
STYLE_NAMES = list(TREATMENTS)
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
    'k': ('sticker', 'Sticker', 'The sticker\'s lines, separated by "/" (leave empty for none):',
          ' / '.join, lambda text: tuple(line.strip() for line in text.split('/') if line.strip())),
}


class LetteringScreen:
    # everything on the lettering screen; no windows here, so it can be tested
    def __init__(self, ask=ask_text):
        self.words = CoverWords(name='BIG MIKE', title='BOSS LIFE')
        self.layout = LAYOUT_KEYS[0]
        self.styles = dict(LAYOUTS[self.layout].styles)
        self.seed = 1
        self.finish = 'print'                # aged like a 90s CD booklet (see core/finish.py)
        self.picture = None                  # the BGR picture behind the words (None = placeholder)
        self.ask = ask                       # how to ask for text (a dialog; replaced in tests)
        self.message, self.message_until = '', 0.0
        self._layer = (None, None)           # (settings, lettering), redrawn only when they change
        self._cover = (None, None)

    def settings(self):
        return (repr(self.words), self.layout, tuple(sorted(self.styles.items())), self.seed, self.finish)

    def cover(self):
        # the cover on screen: the picture with the (aged) lettering over it
        key = self.settings() + (id(self.picture),)
        if self._cover[0] != key:
            if self._layer[0] != self.settings():
                layer = draw_cover_lettering(self.words, self.layout, PREVIEW, self.styles, self.seed)
                self._layer = (self.settings(), age(layer, self.finish, 1.0, self.seed))
            if self.picture is None:
                picture = placeholder(PREVIEW, 4 if self.layout == 'crew_row' else 1)
            else:
                picture = cv2.resize(square_crop(self.picture), (PREVIEW, PREVIEW), interpolation=cv2.INTER_AREA)
            self._cover = (key, apply_lettering(picture, self._layer[1]))
        return self._cover[1]

    def screen(self, now=None):
        # the whole window: a bar with the settings and keys, above the cover
        bar = np.full((BAR_H, PREVIEW, 3), 40, np.uint8)
        layout = LAYOUTS[self.layout]
        status = (f'{layout.name}   name: {self.styles["name"]}   title: {self.styles["title"]}   '
                  f'finish: {self.finish}   look #{self.seed}')
        showing_message = self.message and (now or time.time()) < self.message_until
        cv2.putText(bar, self.message if showing_message else status, (14, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                    GOLD if showing_message else (255, 255, 255), 2, cv2.LINE_AA)
        hints = ['N name   T title   P presents   F featuring   K sticker',
                 'L layout   1 name style   2 title style   A aged finish   R reshuffle',
                 'U picture   B plain   S save print file   Q quit']
        for i, hint in enumerate(hints):
            cv2.putText(bar, hint, (14, 58 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
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
        k = chr(key & 0xFF).lower()
        if k == 'q':
            return 'quit'
        if k == 's':
            return 'save'
        if k in FIELDS:
            self.edit(k)
        elif k == 'l':
            self.layout = next_in(LAYOUT_KEYS, self.layout)
            self.styles = dict(LAYOUTS[self.layout].styles)        # each layout starts with its own styles
            self.say(f'{LAYOUTS[self.layout].name} layout')
        elif k == '1':
            self.styles['name'] = next_in(STYLE_NAMES, self.styles['name'])
        elif k == '2':
            self.styles['title'] = next_in(STYLE_NAMES, self.styles['title'])
        elif k == 'a':
            self.finish = next_in(FINISHES, self.finish)
            self.say(f'Finish: {self.finish}')
        elif k == 'r':
            self.seed += 1                   # new sparkles, gems, burn marks and grain
        elif k == 'u':
            path = choose_image_file()
            image = load_image(path) if path else None
            if image is not None:
                self.picture = image
            elif path:
                self.say('Could not open that picture')
        elif k == 'b':
            self.picture = None
        return None

    def save(self):
        return save_lettering(self.words, self.layout, self.styles, self.seed, self.picture, finish=self.finish)


def main():
    # Windows display scaling would blur the window; this keeps it sharp
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    screen = LetteringScreen()
    cv2.namedWindow(WINDOW)
    cv2.moveWindow(WINDOW, 40, 20)
    while True:
        cv2.imshow(WINDOW, screen.screen())
        key = cv2.waitKey(30)
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
