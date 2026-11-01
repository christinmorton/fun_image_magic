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
        mascot=cv2.getTrackbarPos('Cody', 'controls') == 1,
        frame=cv2.getTrackbarPos('Frame', 'controls') - 1,              # -1 = off
    )

def outlined_text(img, text, org, scale, thickness, outline):
    # white text with a dark outline, readable on any background
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), outline)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thickness)

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
help_panel = np.full((214, 460, 3), 40, np.uint8)
for i, line in enumerate(['Click the video, then press:',
                          '1-9, 0 preset   [ ] previous/next preset',
                          'F sticker   B background   O frame',
                          'M Cody   S save   Q quit',
                          'SPACE photo strip (3-2-1 countdown)',
                          'U upload an image   W webcam']):
    cv2.putText(help_panel, line, (12, 30 + i * 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imshow('controls', help_panel)

# put the two windows side by side in the top-left of the screen
cv2.moveWindow('app', 10, 10)
cv2.moveWindow('controls', source.width() + 40, 10)

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler
cv2.createTrackbar('Contrast', 'controls', 10, 30, dummy)   # trackbars only do whole numbers, so 0-30 means 0.0-3.0
cv2.createTrackbar('Brightness', 'controls', 50, 100, dummy)
cv2.createTrackbar('Filter', 'controls', 0, len(KERNELS) - 1, dummy)
cv2.createTrackbar('Greyscale', 'controls', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type

# feature sliders (the keyboard shortcuts move these same sliders)
cv2.createTrackbar('Preset', 'controls', 0, len(PRESETS) - 1, dummy)
cv2.createTrackbar('Sticker', 'controls', 0, len(art.stickers), dummy)         # 0 = off
cv2.createTrackbar('Background', 'controls', 0, len(art.backgrounds), dummy)   # 0 = off
cv2.createTrackbar('Cody', 'controls', 0, 1, dummy)
cv2.createTrackbar('Frame', 'controls', 1 if art.frames else 0, len(art.frames), dummy)   # 0 = off

print('Keys (click the video first): 1-9, 0 presets | [ ] prev/next preset | f face sticker | b background | m Cody | o frame')
print('      space photo strip | s save | u upload an image | w webcam | q quit')


photo_strip = PhotoStrip()


# Main UI loop
while True:
    img = source.read()
    if img is None:
        break

    # read the settings, find faces / people if needed, and make the finished picture
    look = read_look()
    faces, person_mask = tracker.analyse(img, find_faces=look.sticker >= 0, find_person=look.background >= 0)
    picture = render(img, look, art, faces, person_mask)

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
        # save image
        save_picture('output', picture)
    elif key == ord(' '):
        # start a photo strip
        photo_strip.start(time.time())
    elif key == ord('u'):
        # upload: pick an image file to edit instead of the webcam
        path = choose_image_file()
        image = load_image(path) if path else None
        if image is not None:
            source.use_image(image)
            cv2.moveWindow('controls', source.width() + 40, 10)
        elif path:
            print('Could not open image:', path)
    elif key == ord('w') and source.cap is None:
        # back to the webcam (the uploaded image stays on screen if there is none)
        if source.open_webcam():
            cv2.moveWindow('controls', source.width() + 40, 10)
        else:
            print('No webcam found')
    elif key == ord('f'):
        # cycle face stickers: off -> each sticker -> off
        cv2.setTrackbarPos('Sticker', 'controls', (look.sticker + 2) % (len(art.stickers) + 1))
    elif key == ord('b'):
        # cycle backgrounds: off -> each background -> off
        cv2.setTrackbarPos('Background', 'controls', (look.background + 2) % (len(art.backgrounds) + 1))
    elif key == ord('m'):
        cv2.setTrackbarPos('Cody', 'controls', 0 if look.mascot else 1)
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
    shown = picture.copy()
    outlined_text(shown, PRESETS[look.preset][0], (20, 40), 1.2, 2, 6)
    outlined_text(shown, 'SPACE photo strip   S save   U upload   W webcam   Q quit', (20, 70), 0.55, 1, 4)

    # photo strip: count down, take a shot, repeat, then save the strip
    seconds_left, strip = photo_strip.update(picture, time.time())
    if strip is not None:
        save_picture('strip', strip)
        cv2.imshow('strip', cv2.resize(strip, None, fx=700 / strip.shape[0], fy=700 / strip.shape[0]))
    if seconds_left is not None:
        outlined_text(shown, str(seconds_left), (shown.shape[1] // 2 - 30, 120), 4, 8, 16)
    if photo_strip.flashing(time.time()):
        shown[:] = 255      # white flash when a shot is taken

    # Show the image
    cv2.imshow('app', shown)


# window cleanup
source.release()
tracker.close()
cv2.destroyAllWindows()
