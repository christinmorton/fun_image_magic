#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CSN photo booth: the windows, sliders, keys and main loop.
# The picture work lives in the other modules:
#   sources.py        webcam / uploaded image
#   tracking.py       MediaPipe face and person detection
#   look.py           the settings for a picture, and render() which applies them
#   filters.py        kernels and presets
#   overlays.py       frames, stickers, Cody, background swap
#   booth.py          photo strip countdown
#   slots.py          the four-slot editor (four photos, each with its own look)
#   asset_library.py  loads the art in assets/
import ctypes
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from asset_library import load_art
from booth import PhotoStrip
from filters import KERNELS, PRESETS
from look import Look, render
from slots import LAYOUTS, SLOT_COUNT, Slots
from sources import PictureSource, choose_image_file, load_image
from tracking import Tracker

# Windows display scaling (e.g. 125%) stretches OpenCV windows and makes them blurry;
# this tells Windows the app handles scaling itself, so the video stays sharp
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

# folders are found from this file's location, so the app runs from any folder
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / 'assets'
MODELS_DIR = BASE_DIR / 'models'
OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

# number keys pick the first ten presets (1-9, then 0); [ and ] step through all of them
PRESET_KEYS = '1234567890'
TAB_KEY = 9

# the editor screen: the strip/grid preview is shrunk to fit, under a title bar
EDITOR_MAX_W, EDITOR_MAX_H, EDITOR_BAR_H = 1200, 860, 80

#dummy function that does nothing
def dummy(value):
    pass

def read_look():
    # the current settings, read from the trackbars
    return Look(
        contrast=cv2.getTrackbarPos('Contrast', 'controls') / 10,        # 10 = 1.0, no change
        brightness=cv2.getTrackbarPos('Brightness', 'controls'),
        kernel=cv2.getTrackbarPos('Filter', 'controls'),
        grayscale=cv2.getTrackbarPos('Greyscale', 'controls'),
        preset=cv2.getTrackbarPos('Preset', 'controls'),
        sticker=cv2.getTrackbarPos('Sticker', 'controls') - 1,          # -1 = off
        background=cv2.getTrackbarPos('Background', 'controls') - 1,    # -1 = off
        mascot=cv2.getTrackbarPos('Cody', 'controls') - 1,              # -1 = off
        frame=cv2.getTrackbarPos('Frame', 'controls') - 1,              # -1 = off
    )

def show_look(look):
    # move the trackbars to match a look (when switching between the camera and slots)
    cv2.setTrackbarPos('Contrast', 'controls', round(look.contrast * 10))
    cv2.setTrackbarPos('Brightness', 'controls', look.brightness)
    cv2.setTrackbarPos('Filter', 'controls', look.kernel)
    cv2.setTrackbarPos('Greyscale', 'controls', look.grayscale)
    cv2.setTrackbarPos('Preset', 'controls', look.preset)
    cv2.setTrackbarPos('Sticker', 'controls', look.sticker + 1)
    cv2.setTrackbarPos('Background', 'controls', look.background + 1)
    cv2.setTrackbarPos('Cody', 'controls', look.mascot + 1)
    cv2.setTrackbarPos('Frame', 'controls', look.frame + 1)

def outlined_text(img, text, org, scale, thickness, outline):
    # white text with a dark outline, readable on any background
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), outline)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thickness)

def editor_screen(layout_img, selected_rect, title, hint):
    # the strip/grid shrunk to fit the screen, the selected slot outlined in gold,
    # under a dark bar with the title and key hints
    scale = min(1.0, EDITOR_MAX_W / layout_img.shape[1], EDITOR_MAX_H / layout_img.shape[0])
    preview = cv2.resize(layout_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    x, y, w, h = [round(v * scale) for v in selected_rect]
    cv2.rectangle(preview, (x + 2, y + 2), (x + w - 3, y + h - 3), (1, 207, 255), 4)
    width = max(preview.shape[1], 680)
    screen = np.full((preview.shape[0] + EDITOR_BAR_H, width, 3), 40, np.uint8)
    left = (width - preview.shape[1]) // 2
    screen[EDITOR_BAR_H:, left:left + preview.shape[1]] = preview
    cv2.putText(screen, title, (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(screen, hint, (16, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    return screen

def window_closed(name):
    # True once the window's X button has been clicked
    try:
        return cv2.getWindowProperty(name, cv2.WND_PROP_VISIBLE) < 1
    except cv2.error:
        return True

def save_picture(kind, img):
    cv2.imwrite(str(OUTPUT_DIR / f'{kind}-{datetime.now():%Y%m%d-%H%M%S}.png'), img)


art = load_art(ASSETS_DIR)
tracker = Tracker(MODELS_DIR)


# the picture source: start with an image if one is given (python app.py photo.jpg),
# otherwise the webcam
source = PictureSource()
if len(sys.argv) > 1:
    still_image = load_image(sys.argv[1])
    if still_image is None:
        raise SystemExit(f'Could not load image: {sys.argv[1]}')
    source.use_image(still_image)
elif not source.open_webcam():
    print('No webcam found, choose an image instead')
    path = choose_image_file()
    still_image = load_image(path) if path else None
    if still_image is None:
        raise SystemExit('No webcam found and no image chosen')
    source.use_image(still_image)


# create teh UI windows: 'app' shows only the video, 'controls' holds the trackbars
cv2.namedWindow('app')
cv2.namedWindow('controls')

# key help shown under the trackbars in the controls window
help_lines = ['Click the video, then press:',
              '1-9, 0 preset   [ ] previous/next preset',
              'F sticker   B background   O frame',
              'M Cody (poses)   S save   Q quit',
              'SPACE photo strip (3-2-1 countdown)',
              'U upload an image   W webcam',
              '- four-slot editor -',
              'A add picture to slot   E editor on/off',
              'TAB next slot   L strip/grid   X clear slot']
help_panel = np.full((22 + 32 * len(help_lines), 460, 3), 40, np.uint8)
for i, line in enumerate(help_lines):
    cv2.putText(help_panel, line, (12, 30 + i * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imshow('controls', help_panel)

# put the two windows side by side in the top-left of the screen
window_w = source.width()
cv2.moveWindow('app', 10, 10)
cv2.moveWindow('controls', window_w + 40, 10)

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler
cv2.createTrackbar('Contrast', 'controls', 10, 30, dummy)   # trackbars only do whole numbers, so 0-30 means 0.0-3.0
cv2.createTrackbar('Brightness', 'controls', 50, 100, dummy)
cv2.createTrackbar('Filter', 'controls', 0, len(KERNELS) - 1, dummy)
cv2.createTrackbar('Greyscale', 'controls', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type

# feature sliders (the keyboard shortcuts move these same sliders)
cv2.createTrackbar('Preset', 'controls', 0, len(PRESETS) - 1, dummy)
cv2.createTrackbar('Sticker', 'controls', 0, len(art.stickers), dummy)         # 0 = off
cv2.createTrackbar('Background', 'controls', 0, len(art.backgrounds), dummy)   # 0 = off
cv2.createTrackbar('Cody', 'controls', 0, len(art.mascots), dummy)            # 0 = off, then each pose
cv2.createTrackbar('Frame', 'controls', 1 if art.frames else 0, len(art.frames), dummy)   # 0 = off

# four-slot editor sliders
cv2.createTrackbar('Slot', 'controls', 1, SLOT_COUNT, dummy)                   # which slot (1-4)
cv2.setTrackbarMin('Slot', 'controls', 1)
cv2.createTrackbar('Layout', 'controls', 0, len(LAYOUTS) - 1, dummy)          # 0 = strip, 1 = grid

print('Keys (click the video first): 1-9, 0 presets | [ ] prev/next preset | f face sticker | b background | m Cody poses | o frame')
print('      space photo strip | s save | u upload an image | w webcam | q quit')
print('      four-slot editor: a add picture to slot | e editor on/off | tab next slot | l strip/grid | x clear slot')


photo_strip = PhotoStrip()
slots = Slots()
editing = False            # False = camera, True = four-slot editor
camera_look = None         # the camera's settings, kept while the sliders edit a slot
message, message_until = '', 0


# Main UI loop
while True:
    # read the settings (the sliders edit the camera, or the selected slot in the editor)
    look = read_look()
    slot_idx = cv2.getTrackbarPos('Slot', 'controls') - 1
    layout = LAYOUTS[cv2.getTrackbarPos('Layout', 'controls')]

    if editing:
        # the sliders belong to the selected slot; picking another slot shows its settings
        slots.current().look = look
        if slot_idx != slots.selected:
            slots.selected = slot_idx
            show_look(slots.current().look)
            look = slots.current().look
        picture, rects = slots.compose(art, layout)
    else:
        slots.selected = slot_idx
        img = source.read()
        if img is None:
            break
        # find faces / people if needed, and make the finished picture
        faces, person_mask = tracker.analyse(img, find_faces=look.sticker >= 0, find_person=look.background >= 0)
        picture = render(img, look, art, faces, person_mask)
    # what this frame shows (a key below may switch modes, but that shows from the next frame)
    showing_editor = editing

    # wait for key press (1 millisecond, so the video stays smooth)
    key = cv2.waitKey(1)

    # closing either window with its X button quits, like Q (checked right after waitKey,
    # because imshow would quietly open the window again)
    if window_closed('app') or window_closed('controls'):
        break

    # if key equals 'q' would be ideal but instead I need integer
    if key == ord('q'):
        break
    elif key == ord('s'):
        # save image (in the editor: the whole strip or grid)
        if not editing:
            save_picture('output', picture)
            message = 'Saved'
        elif slots.any_filled():
            save_picture(f'edited-{layout.lower()}', slots.compose(art, layout, for_saving=True)[0])
            message = f'Saved the {layout.lower()}'
        else:
            message = 'Nothing to save: all slots are empty'
        message_until = time.time() + 2
    elif key == ord('e'):
        # switch between the camera and the editor; each keeps its own slider settings
        if editing:
            editing = False
            show_look(camera_look)
        else:
            editing, camera_look = True, look
            show_look(slots.current().look)
    elif key == ord('a') and not editing:
        # add the camera picture (unedited, with the current settings) to the selected slot
        slots.put(slots.selected, img, look, tracker)
        message, message_until = f'Added to slot {slots.selected + 1}', time.time() + 2
        cv2.setTrackbarPos('Slot', 'controls', (slots.selected + 1) % SLOT_COUNT + 1)   # next slot
    elif key == TAB_KEY:
        cv2.setTrackbarPos('Slot', 'controls', (slots.selected + 1) % SLOT_COUNT + 1)
    elif key == ord('l'):
        cv2.setTrackbarPos('Layout', 'controls', (LAYOUTS.index(layout) + 1) % len(LAYOUTS))
    elif key == ord('x') and editing:
        slots.clear(slots.selected)
        show_look(slots.current().look)
    elif key == ord(' ') and not editing:
        # start a photo strip
        photo_strip.start(time.time())
    elif key == ord('u'):
        # upload: in the editor, into the selected slot; otherwise instead of the webcam
        path = choose_image_file()
        image = load_image(path) if path else None
        if image is not None and editing:
            slots.put(slots.selected, image, slots.current().look, tracker)
        elif image is not None:
            source.use_image(image)
        elif path:
            print('Could not open image:', path)
    elif key == ord('w') and not editing and source.cap is None:
        # back to the webcam (the uploaded image stays on screen if there is none)
        if not source.open_webcam():
            print('No webcam found')
    elif key == ord('f'):
        # cycle face stickers: off -> each sticker -> off
        cv2.setTrackbarPos('Sticker', 'controls', (look.sticker + 2) % (len(art.stickers) + 1))
    elif key == ord('b'):
        # cycle backgrounds: off -> each background -> off
        cv2.setTrackbarPos('Background', 'controls', (look.background + 2) % (len(art.backgrounds) + 1))
    elif key == ord('m'):
        # cycle Cody poses: off -> each pose -> off
        cv2.setTrackbarPos('Cody', 'controls', (look.mascot + 2) % (len(art.mascots) + 1))
    elif key == ord('o'):
        # cycle branded frames: each frame -> off -> first frame
        cv2.setTrackbarPos('Frame', 'controls', (look.frame + 2) % (len(art.frames) + 1))
    elif key == ord('['):
        cv2.setTrackbarPos('Preset', 'controls', (look.preset - 1) % len(PRESETS))
    elif key == ord(']'):
        cv2.setTrackbarPos('Preset', 'controls', (look.preset + 1) % len(PRESETS))
    elif key != -1 and chr(key & 0xFF) in PRESET_KEYS:
        cv2.setTrackbarPos('Preset', 'controls', min(PRESET_KEYS.index(chr(key & 0xFF)), len(PRESETS) - 1))

    # anything drawn on `shown` is only on screen, never in saved photos
    if showing_editor:
        # messages show in the editor's title bar, in place of the key hints
        title = f'Editing slot {slots.selected + 1} of {SLOT_COUNT} ({layout}): {PRESETS[look.preset][0]}'
        hint = 'TAB next slot  L strip/grid  U upload  X clear  S save  E camera'
        shown = editor_screen(picture, rects[slots.selected], title,
                              message if time.time() < message_until else hint)
    else:
        shown = picture.copy()
        outlined_text(shown, PRESETS[look.preset][0], (20, 40), 1.2, 2, 6)
        outlined_text(shown, 'SPACE strip  A add to slot  E editor  S save  U upload  W webcam  Q quit', (20, 70), 0.5, 1, 4)

        # photo strip: count down, take a shot, repeat, then save the strip and open
        # it in the editor, so each photo can be edited on its own
        seconds_left, strip = photo_strip.update(picture, time.time(), original=(img, look))
        if strip is not None:
            save_picture('strip', strip)
            for i, (shot, shot_look) in enumerate(photo_strip.originals[:SLOT_COUNT]):
                slots.put(i, shot, shot_look, tracker)
            editing, camera_look = True, look
            cv2.setTrackbarPos('Slot', 'controls', 1)
            slots.selected = 0
            show_look(slots.current().look)
            message, message_until = 'Strip saved - now edit each photo, then S to save', time.time() + 4
        if seconds_left is not None:
            outlined_text(shown, str(seconds_left), (shown.shape[1] // 2 - 30, 120), 4, 8, 16)
        if photo_strip.flashing(time.time()):
            shown[:] = 255      # white flash when a shot is taken
        if time.time() < message_until:
            outlined_text(shown, message, (20, 105), 0.8, 2, 5)   # under the key hint, clear of frame captions

    # keep the controls window just right of the picture when the picture's width changes
    if shown.shape[1] != window_w:
        window_w = shown.shape[1]
        cv2.moveWindow('controls', window_w + 40, 10)

    # Show the image
    cv2.imshow('app', shown)


# window cleanup
source.release()
tracker.close()
cv2.destroyAllWindows()
