#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Cover Studio (desktop): the artwork screen - the step that costs money. Pick a saved
# person, then a scene, clothes and jewellery; make four previews (about $0.18, asked
# first), pick one, make it again bigger if you like (a 2K final), and send it to the
# lettering screen to finish the cover. Everything made is saved with the person, in
# subjects/<name>/artwork/. Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe desktop\artwork.py
import ctypes
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from tkinter import BooleanVar, Button, Checkbutton, Frame, Label, Listbox, Tk, messagebox

import cv2
import numpy as np

# make `core` and `desktop` importable however this file is started
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from core.ai import GeminiGenerator                                                          # noqa: E402
from core.artwork import (PREVIEW_COUNT, ArtworkRequest, final_cost, make_final,              # noqa: E402
                          make_previews, preview_cost, reference_photos, save_final, save_previews)
from core.env_file import load_env                                                           # noqa: E402
from core.spending import OverLimit, Spending                                                # noqa: E402
from core.styles import ACCESSORIES, CLOTHING, JEWELLERY, STYLES                             # noqa: E402
from core.subjects import has_current_consent, list_subjects, load_subject                   # noqa: E402
from desktop.studio import next_in, window_closed                                            # noqa: E402

WINDOW = 'Cover Studio - Artwork'
PANEL_W, TILE, GAP, BAR_H = 360, 330, 12, 64     # settings panel, preview tiles, keys bar
FINAL_SIZE = '2K'
GOLD, WHITE, GREY, RED = (1, 207, 255), (255, 255, 255), (170, 170, 170), (80, 80, 255)


def label(key):
    return key.replace('_', ' ')

def hidden_root():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    return root

def confirm(question):
    # a yes/no box in front of the window; True for yes
    root = hidden_root()
    answer = messagebox.askyesno('Cover Studio', question, parent=root)
    root.destroy()
    return answer

def choose_subject(folders):
    # a list of the saved people; returns the chosen folder, or None
    root = Tk()
    root.title('Choose a person')
    root.attributes('-topmost', True)
    chosen = {'folder': None}
    names = Listbox(root, width=40, height=min(12, max(4, len(folders))))
    for folder in folders:
        info, _ = load_subject(folder)
        names.insert('end', f'{info["name"]}   ({", ".join(info["angles"])})')
    names.selection_set(0)
    names.pack(padx=12, pady=12)
    def ok(event=None):
        if names.curselection():
            chosen['folder'] = folders[names.curselection()[0]]
        root.destroy()
    names.bind('<Double-Button-1>', ok)
    root.bind('<Return>', ok)
    Button(root, text='OK', width=12, command=ok).pack(pady=(0, 12))
    root.mainloop()
    return chosen['folder']

def choose_extras(jewellery, accessories):
    # checkboxes for the jewellery and accessories; returns (jewellery, accessories) or None
    root = Tk()
    root.title('Jewellery and extras')
    root.attributes('-topmost', True)
    marks = {}
    for heading, options, picked in [('Jewellery (none ticked = no jewellery)', JEWELLERY, jewellery),
                                     ('Extras', ACCESSORIES, accessories)]:
        Label(root, text=heading, anchor='w').pack(fill='x', padx=12, pady=(10, 2))
        for key in options:
            marks[key] = BooleanVar(value=key in picked)
            Checkbutton(root, text=label(key), variable=marks[key], anchor='w').pack(fill='x', padx=24)
    result = {'picks': None}
    def ok():
        result['picks'] = (tuple(k for k in JEWELLERY if marks[k].get()), tuple(k for k in ACCESSORIES if marks[k].get()))
        root.destroy()
    buttons = Frame(root)
    buttons.pack(pady=12)
    Button(buttons, text='OK', width=10, command=ok).pack(side='left', padx=4)
    Button(buttons, text='Cancel', width=10, command=root.destroy).pack(side='left', padx=4)
    root.mainloop()
    return result['picks']


class ArtworkScreen:
    # everything on the artwork screen; no windows here, so it can be tested. Paid work
    # runs in the background (background(work)), and poll() picks up the result
    def __init__(self, folder, make_generator, spending, confirm=confirm, choose_extras=choose_extras,
                 background=None):
        self.folder = folder
        self.info, self.pictures = load_subject(folder)
        self.request = ArtworkRequest()
        self.make_generator = make_generator          # made on first use, so the screen opens without a key
        self.generator = None
        self.spending, self.confirm, self.choose_extras = spending, confirm, choose_extras
        self.background = background or (lambda work: threading.Thread(target=work, daemon=True).start())
        self.results = []                             # (image or None, error or None) per preview
        self.set_folder = None                        # where the latest previews were saved
        self.picked = None                            # the chosen preview's number (1-4)
        self.finals = {}                              # preview number -> its final
        self.busy = None                              # (what, started) while the AI works
        self.message = 'S scene, C clothes, J jewellery, then G to make previews'
        self._done = None                             # finished background work, for poll()

    def scenes(self):
        return list(STYLES[self.request.style].scenes)

    def chosen(self):
        # the picked artwork: its final if one was made, else the preview
        if self.picked is None:
            return None
        return self.finals.get(self.picked, self.results[self.picked - 1][0])

    def handle_key(self, key):
        # one key press; returns 'quit', 'letter' (send the pick to the lettering) or None
        if key == -1:
            return None
        k = chr(key & 0xFF).lower()
        if k == 'q':
            return 'quit'
        if self.busy:
            self.message = 'Wait for the AI to finish...'
            return None
        if k == 's':
            self.request = replace(self.request, scene=next_in(self.scenes(), self.request.scene))
        elif k == 'c':
            self.request = replace(self.request, clothing=next_in(list(CLOTHING), self.request.clothing))
        elif k == 'j':
            picks = self.choose_extras(self.request.jewellery, self.request.accessories)
            if picks is not None:
                self.request = replace(self.request, jewellery=picks[0], accessories=picks[1])
        elif k == 'g':
            self.start_previews()
        elif k in ('1', '2', '3', '4'):
            n = int(k)
            if n <= len(self.results) and self.results[n - 1][0] is not None:
                self.picked = n
                self.message = f'Picked {n}.   F makes it again at {FINAL_SIZE}   L sends it to the lettering'
            else:
                self.message = f'There is no preview {n}'
        elif k == 'f':
            self.start_final()
        elif k == 'l':
            if self.chosen() is None:
                self.message = 'Pick a preview first (1-4)'
            else:
                return 'letter'
        return None

    def may_spend(self, cost, question):
        # every check before sending photos and spending money; True to go ahead
        if not has_current_consent(self.info):
            self.message = (f'{self.info["name"]} hasn\'t agreed to their photos going to the image AI: '
                            'desktop\\scan.py --reconfirm first')
            return False
        try:
            self.spending.check(cost)
        except OverLimit as error:
            self.message = str(error)
            return False
        spent = self.spending.spent_today()
        return self.confirm(f'{question} for about ${cost:.2f}?\n\n'
                            f'Today so far: ${spent:.2f} of your ${self.spending.limit:.2f} daily limit.')

    def run(self, what, work):
        # do paid work in the background; poll() picks up what it leaves in self._done
        self.busy = (what, time.time())
        def wrapped():
            try:
                if self.generator is None:
                    self.generator = self.make_generator()
                self._done = work(self.generator)
            except Exception as error:                # over the limit meanwhile, no key...
                self._done = ('error', f'{type(error).__name__}: {error}')
        self.background(wrapped)

    def start_previews(self):
        scene = STYLES[self.request.style].scenes[self.request.scene][0]
        if not self.may_spend(preview_cost(), f'Make {PREVIEW_COUNT} previews of {self.info["name"]} ({scene})'):
            return
        request, refs = self.request, len(reference_photos(self.pictures))
        def work(generator):
            results = make_previews(self.pictures, request, generator, self.spending)
            return ('previews', results, save_previews(self.folder, request, results, refs))
        self.run(f'Making {PREVIEW_COUNT} previews', work)

    def start_final(self):
        if self.picked is None:
            self.message = 'Pick a preview first (1-4)'
            return
        if self.picked in self.finals:
            self.message = f'Preview {self.picked} already has a final'
            return
        if not self.may_spend(final_cost(FINAL_SIZE), f'Make preview {self.picked} again at {FINAL_SIZE}'):
            return
        number, preview = self.picked, self.results[self.picked - 1][0]
        def work(generator):
            image, error = make_final(self.pictures, preview, generator, self.spending, FINAL_SIZE)
            if image is not None:
                save_final(self.set_folder, number, FINAL_SIZE, image)
            return ('final', number, image, error)
        self.run(f'Making the {FINAL_SIZE} final', work)

    def poll(self):
        # apply finished background work, if any
        done, self._done = self._done, None
        if done is None:
            return
        self.busy = None
        if done[0] == 'previews':
            _, self.results, self.set_folder = done
            self.picked, self.finals = None, {}
            made = sum(1 for image, _ in self.results if image is not None)
            errors = [error for _, error in self.results if error]
            self.message = f'{made} of {len(self.results)} previews made. Pick one with 1-4' + \
                           (f'   (failed: {errors[0][:60]})' if errors else '')
        elif done[0] == 'final':
            _, number, image, error = done
            if image is not None:
                self.finals[number] = image
                self.message = f'The {FINAL_SIZE} final is ready.   L sends it to the lettering'
            else:
                self.message = f'The final failed: {error[:80]}'
        else:
            self.message = done[1][:110]

    def screen(self, now=None):
        # the whole window: settings on the left, the four previews, keys along the bottom
        now = now or time.time()
        grid_w = 2 * TILE + 3 * GAP
        h = 2 * TILE + 3 * GAP
        panel = np.full((h, PANEL_W, 3), 34, np.uint8)
        front = self.pictures.get('front')
        if front is not None:
            scale = min((PANEL_W - 2 * GAP) / front.shape[1], 200 / front.shape[0])
            small = cv2.resize(front, (int(front.shape[1] * scale), int(front.shape[0] * scale)), interpolation=cv2.INTER_AREA)
            panel[GAP:GAP + small.shape[0], GAP:GAP + small.shape[1]] = small
        style = STYLES[self.request.style]
        lines = [(self.info['name'], WHITE, 0.8, 2),
                 (f'Style: {style.name}', GREY, 0.5, 1),
                 (f'S  Scene: {style.scenes[self.request.scene][0]}', WHITE, 0.55, 1),
                 (f'C  Clothes: {label(self.request.clothing)}', WHITE, 0.55, 1),
                 (f'J  Jewellery: {", ".join(map(label, self.request.jewellery)) or "none"}', WHITE, 0.55, 1),
                 (f'   Extras: {", ".join(map(label, self.request.accessories)) or "none"}', WHITE, 0.55, 1),
                 (f'Spent today: ${self.spending.spent_today():.2f} of ${self.spending.limit:.2f}', GREY, 0.5, 1)]
        y = 250
        for text, colour, scale, weight in lines:
            cv2.putText(panel, text[:40], (GAP, y), cv2.FONT_HERSHEY_SIMPLEX, scale, colour, weight, cv2.LINE_AA)
            y += 34 if scale > 0.6 else 28
        grid = np.full((h, grid_w, 3), 22, np.uint8)
        for i in range(PREVIEW_COUNT):
            x, y = GAP + (i % 2) * (TILE + GAP), GAP + (i // 2) * (TILE + GAP)
            image, error = self.results[i] if i < len(self.results) else (None, None)
            image = self.finals.get(i + 1, image)
            if image is not None:
                grid[y:y + TILE, x:x + TILE] = cv2.resize(image, (TILE, TILE), interpolation=cv2.INTER_AREA)
            elif error:
                cv2.putText(grid, 'failed', (x + 14, y + TILE // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, RED, 2, cv2.LINE_AA)
            cv2.rectangle(grid, (x, y), (x + TILE - 1, y + TILE - 1), GOLD if self.picked == i + 1 else (70, 70, 70),
                          4 if self.picked == i + 1 else 1)
            cv2.putText(grid, str(i + 1) + (f'  final {FINAL_SIZE}' if i + 1 in self.finals else ''), (x + 8, y + 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, WHITE, 2, cv2.LINE_AA)
        if self.busy:
            what, started = self.busy
            text = f'{what}... {now - started:.0f} s'
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
            cv2.rectangle(grid, ((grid_w - tw) // 2 - 14, h // 2 - th - 14), ((grid_w + tw) // 2 + 14, h // 2 + 14), (0, 0, 0), -1)
            cv2.putText(grid, text, ((grid_w - tw) // 2, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, GOLD, 2, cv2.LINE_AA)
        bar = np.full((BAR_H, PANEL_W + grid_w, 3), 40, np.uint8)
        cv2.putText(bar, self.message[:120], (GAP, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, GOLD, 1, cv2.LINE_AA)
        cv2.putText(bar, f'G make {PREVIEW_COUNT} previews (${preview_cost():.2f})   1-4 pick   '
                         f'F final {FINAL_SIZE} (${final_cost(FINAL_SIZE):.2f})   L letter it   Q quit',
                    (GAP, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREY, 1, cv2.LINE_AA)
        return np.vstack([np.hstack([panel, grid]), bar])


def main():
    # Windows display scaling would blur the window; this keeps it sharp
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            pass
    load_env(SERVICE_DIR / '.env')
    folders = list_subjects()
    if not folders:
        root = hidden_root()
        messagebox.showinfo('Cover Studio', 'No one has been scanned yet: run desktop\\scan.py first.', parent=root)
        root.destroy()
        return
    folder = choose_subject(folders)
    if folder is None:
        return
    screen = ArtworkScreen(folder, GeminiGenerator, Spending())
    cv2.namedWindow(WINDOW)
    cv2.moveWindow(WINDOW, 30, 20)
    action = None
    try:
        while True:
            screen.poll()
            cv2.imshow(WINDOW, screen.screen())
            key = cv2.waitKey(30)
            closed = window_closed(WINDOW)
            action = 'quit' if closed else screen.handle_key(key)
            if action == 'quit' and screen.busy and not closed and \
                    not confirm('The AI is still working, and may still charge for it. Quit anyway?'):
                action = None
            if action in ('quit', 'letter'):
                break
    finally:
        cv2.destroyAllWindows()
    if action == 'letter':
        from desktop.studio import main as lettering
        lettering(picture=screen.chosen(), name=screen.info['name'].upper())


if __name__ == '__main__':
    main()
