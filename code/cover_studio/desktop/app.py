#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Photo booth (desktop version): the windows, sliders, keys and main loop.
# Run from the image_service folder:  .\.venv\Scripts\python.exe desktop\app.py
# The picture work lives in core/ (shared with the web API):
#   core/tracking.py       MediaPipe face and person detection
#   core/look.py           the settings for a picture, and render() which applies them
#   core/filters.py        kernels and presets
#   core/overlays.py       frames, stickers, mascot, background swap
#   core/slots.py          the four-slot editor (four photos, each with its own look)
#   core/asset_library.py  loads the art in core/assets/
# and the desktop-only parts live next to this file:
#   desktop/sources.py     webcam / uploaded image
#   desktop/booth.py       photo strip countdown
import ctypes
import sys
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# make `core` and `desktop` importable however this file is started
SERVICE_DIR = Path(__file__).resolve().parent.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from core import ASSETS_DIR, MODELS_DIR                                   # noqa: E402
from core.asset_library import MASCOT_PROP_PREFIX, load_art               # noqa: E402
from core.filters import KERNELS, PRESETS                                 # noqa: E402
from core.look import Look, render                                        # noqa: E402
from core.masks import FOCUS_MODES                                        # noqa: E402
from core.props import (add_prop, bring_to_front, move_prop, prop_at,    # noqa: E402
                        prop_box, remove_prop, resize_prop)
from core.slots import LAYOUTS, SLOT_COUNT, Slots                         # noqa: E402
from core.tracking import Tracker                                         # noqa: E402
from desktop.booth import PhotoStrip                                      # noqa: E402
from desktop.sources import PictureSource, choose_image_file, load_image  # noqa: E402

# Windows display scaling (e.g. 125%) stretches OpenCV windows and makes them blurry;
# this tells Windows the app handles scaling itself, so the video stays sharp
if sys.platform == 'win32':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

# folders are found from this file's location, so the app runs from any folder
# (art and models come from core/; saved photos go to desktop/output/)
OUTPUT_DIR = Path(__file__).resolve().parent / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

# number keys pick the first ten presets (1-9, then 0); [ and ] step through all of them
PRESET_KEYS = '1234567890'
TAB_KEY = 9

# the editor screen: the strip/grid preview is shrunk to fit, under a title bar
EDITOR_MAX_W, EDITOR_MAX_H, EDITOR_BAR_H = 1200, 840, 104

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
        mascot=cv2.getTrackbarPos('Mascot', 'controls') - 1,            # -1 = off
        frame=cv2.getTrackbarPos('Frame', 'controls') - 1,              # -1 = off
        focus=cv2.getTrackbarPos('Focus', 'controls'),                  # 0 = off
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
    cv2.setTrackbarPos('Mascot', 'controls', look.mascot + 1)
    cv2.setTrackbarPos('Frame', 'controls', look.frame + 1)
    cv2.setTrackbarPos('Focus', 'controls', look.focus)

def outlined_text(img, text, org, scale, thickness, outline):
    # white text with a dark outline, readable on any background
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), outline)
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), thickness)

def editor_screen(layout_img, selected_rect, title, hints, prop_rect=None, message=None):
    # the strip/grid shrunk to fit the screen, the selected slot outlined in gold (and the
    # selected prop in light blue), under a dark bar with the title and two lines of hints.
    # Also returns the view (scale, left, top), to turn mouse positions back into the layout
    scale = min(1.0, EDITOR_MAX_W / layout_img.shape[1], EDITOR_MAX_H / layout_img.shape[0])
    preview = cv2.resize(layout_img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    x, y, w, h = [round(v * scale) for v in selected_rect]
    cv2.rectangle(preview, (x + 2, y + 2), (x + w - 3, y + h - 3), (1, 207, 255), 4)
    if prop_rect is not None:
        x, y, w, h = [round(v * scale) for v in prop_rect]
        cv2.rectangle(preview, (x, y), (x + w, y + h), (255, 200, 0), 2)
    width = max(preview.shape[1], 680)
    screen = np.full((preview.shape[0] + EDITOR_BAR_H, width, 3), 40, np.uint8)
    left = (width - preview.shape[1]) // 2
    screen[EDITOR_BAR_H:, left:left + preview.shape[1]] = preview
    cv2.putText(screen, title, (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    for i, hint in enumerate(hints):
        cv2.putText(screen, hint, (16, 64 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
    if message:
        # a short message replaces the first hint line, in gold so it stands out
        screen[46:72] = 40
        cv2.putText(screen, message, (16, 66), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (1, 207, 255), 2, cv2.LINE_AA)
    return screen, (scale, left, EDITOR_BAR_H)

def screen_to_layout(sx, sy, view):
    # a mouse position on the editor screen -> a position in the full-size strip/grid
    scale, left, top = view
    return (sx - left) / scale, (sy - top) / scale

def on_mouse(event, x, y, flags, param):
    # OpenCV calls this during waitKey; the main loop handles the events afterwards
    mouse_events.append((event, x, y, flags))

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
mouse_events = []          # filled by on_mouse() (the editor uses the mouse for slots and props)
cv2.setMouseCallback('app', on_mouse)

# key help shown under the trackbars in the controls window
help_lines = ['Click the video, then press:',
              '1-9, 0 preset   [ ] previous/next preset',
              'F sticker   B background   O frame   P focus',
              'M mascot (poses)   S save   Q quit',
              'SPACE photo strip (3-2-1 countdown)',
              'U upload an image   W webcam',
              '- four-slot editor -',
              'A add picture to slot   E editor on/off',
              'TAB next slot   L strip/grid   X clear slot',
              'Click a slot to select it',
              'R twice: clear everything and start over',
              'Props: I add (Prop slider)   D delete',
              'drag to move   wheel or +/- to resize']
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
cv2.createTrackbar('Mascot', 'controls', 0, len(art.mascots), dummy)          # 0 = off, then each pose
cv2.createTrackbar('Frame', 'controls', 1 if art.frames else 0, len(art.frames), dummy)   # 0 = off
cv2.createTrackbar('Focus', 'controls', 0, len(FOCUS_MODES) - 1, dummy)   # 0 = off, color pop, portrait blur, mask preview

# four-slot editor sliders
cv2.createTrackbar('Slot', 'controls', 1, SLOT_COUNT, dummy)                   # which slot (1-4)
cv2.setTrackbarMin('Slot', 'controls', 1)
cv2.createTrackbar('Layout', 'controls', 0, len(LAYOUTS) - 1, dummy)          # 0 = strip, 1 = grid
cv2.createTrackbar('Prop', 'controls', 0, max(len(art.props) - 1, 0), dummy)  # which prop I adds

print('Keys (click the video first): 1-9, 0 presets | [ ] prev/next preset | f face sticker | b background | m mascot poses | o frame | p focus')
print('      space photo strip | s save | u upload an image | w webcam | q quit')
print('      four-slot editor: a add picture to slot | e editor on/off | tab next slot | l strip/grid | x clear slot')
print('      props (editor): i add | d delete | + / - resize | mouse: click to select, drag to move, wheel to resize')
print('      r twice: clear everything and start over')


photo_strip = PhotoStrip()
slots = Slots()
editing = False            # False = camera, True = four-slot editor
camera_look = None         # the camera's settings, kept while the sliders edit a slot
message, message_until = '', 0
last_filled = None         # the slot most recently given a photo (the editor opens there)
reset_armed_until = 0      # R must be pressed twice within a few seconds to start over
selected_prop = None       # index into the selected slot's props, or None
drag_offset = None         # while dragging a prop: (dx, dy) from the grab point to its centre
editor_view = None         # (scale, left, top) of the last editor screen, for the mouse


def set_props(new_props):
    # change the selected slot's props (they live on the slot, not on the sliders)
    slots.current().look = replace(slots.current().look, props=new_props)

def photo_point(slot_index, lx, ly):
    # a point in the strip/grid -> (u, v) as fractions of that slot's photo
    # (outside the photo gives values below 0 or above 1), or None if the slot is empty
    if slot_index not in slots.photo_rects:
        return None
    x, y, w, h = slots.photo_rects[slot_index]
    return (lx - x) / w, (ly - y) / h


# Main UI loop
while True:
    # read the settings (the sliders edit the camera, or the selected slot in the editor)
    look = read_look()
    slot_idx = cv2.getTrackbarPos('Slot', 'controls') - 1
    layout = LAYOUTS[cv2.getTrackbarPos('Layout', 'controls')]
    prop_choice = cv2.getTrackbarPos('Prop', 'controls')

    if editing:
        # the sliders belong to the selected slot; picking another slot shows its settings.
        # Props aren't on the sliders, so they come from the slot itself
        look = replace(look, props=slots.current().look.props)
        slots.current().look = look
        if slot_idx != slots.selected:
            slots.selected = slot_idx
            show_look(slots.current().look)
            look = slots.current().look
            selected_prop, drag_offset = None, None
        picture, rects = slots.compose(art, layout)
    else:
        slots.selected = slot_idx
        img = source.read()
        if img is None:
            break
        # find faces / people if needed, and make the finished picture
        faces, person_mask = tracker.analyse(img, find_faces=look.sticker >= 0, find_person=look.needs_person_mask())
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
    elif key == ord('r') and time.time() >= reset_armed_until:
        # start over, step 1: ask for a second press, so one stray key can't wipe everything
        reset_armed_until = time.time() + 3
        message, message_until = 'Press R again to clear everything and start over', reset_armed_until
    elif key == ord('r'):
        # start over, step 2: empty the slots, cancel any photo strip, put every slider back
        # to its starting value and go back to the camera (saved files in output/ are kept)
        slots = Slots()
        photo_strip = PhotoStrip()
        editing, camera_look, last_filled = False, None, None
        selected_prop, drag_offset = None, None
        show_look(Look(frame=0 if art.frames else -1))
        cv2.setTrackbarPos('Slot', 'controls', 1)
        cv2.setTrackbarPos('Layout', 'controls', 0)
        cv2.setTrackbarPos('Prop', 'controls', 0)
        if source.cap is None:
            source.open_webcam()     # back to the webcam if there is one (else the photo stays)
        reset_armed_until = 0
        message, message_until = 'Started over', time.time() + 2
    elif key == ord('e'):
        # switch between the camera and the editor; each keeps its own slider settings
        if editing:
            editing = False
            show_look(camera_look)
        else:
            editing, camera_look = True, look
            # A moves on to the next (empty) slot, so open on the slot that was filled last
            if slots.current().image is None and last_filled is not None and slots.slots[last_filled].image is not None:
                slots.selected = last_filled
                cv2.setTrackbarPos('Slot', 'controls', last_filled + 1)
            show_look(slots.current().look)
        selected_prop, drag_offset = None, None
    elif key == ord('a') and not editing:
        # add the camera picture (unedited, with the current settings) to the selected slot
        slots.put(slots.selected, img, look, tracker)
        last_filled = slots.selected
        message, message_until = f'Added to slot {slots.selected + 1}', time.time() + 2
        cv2.setTrackbarPos('Slot', 'controls', (slots.selected + 1) % SLOT_COUNT + 1)   # next slot
    elif key == TAB_KEY:
        cv2.setTrackbarPos('Slot', 'controls', (slots.selected + 1) % SLOT_COUNT + 1)
    elif key == ord('l'):
        cv2.setTrackbarPos('Layout', 'controls', (LAYOUTS.index(layout) + 1) % len(LAYOUTS))
    elif key == ord('x') and editing:
        slots.clear(slots.selected)
        show_look(slots.current().look)
        selected_prop, drag_offset = None, None
    elif key == ord('i') and not editing:
        message, message_until = 'Props are added in the editor: press E', time.time() + 3
    elif key == ord('i') and editing and art.props:
        # add the prop chosen on the Prop slider to the middle of the selected photo
        if slots.current().image is None:
            message, message_until = 'Add a photo to this slot first', time.time() + 2
        else:
            size = 0.6 if art.prop_names[prop_choice].startswith(MASCOT_PROP_PREFIX) else 0.35
            set_props(add_prop(slots.current().look.props, prop_choice, size))
            selected_prop = len(slots.current().look.props) - 1
    elif key == ord('d') and editing and selected_prop is not None:
        set_props(remove_prop(slots.current().look.props, selected_prop))
        selected_prop, drag_offset = None, None
    elif key in (ord('+'), ord('='), ord('-')) and editing and selected_prop is not None:
        factor = 1 / 1.1 if key == ord('-') else 1.1
        set_props(resize_prop(slots.current().look.props, selected_prop, factor))
    elif key == ord(' ') and not editing:
        # start a photo strip
        photo_strip.start(time.time())
    elif key == ord('u'):
        # upload: in the editor, into the selected slot; otherwise instead of the webcam
        path = choose_image_file()
        image = load_image(path) if path else None
        if image is not None and editing:
            slots.put(slots.selected, image, slots.current().look, tracker)
            last_filled = slots.selected
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
        # cycle mascot poses: off -> each pose -> off
        cv2.setTrackbarPos('Mascot', 'controls', (look.mascot + 2) % (len(art.mascots) + 1))
    elif key == ord('o'):
        # cycle branded frames: each frame -> off -> first frame
        cv2.setTrackbarPos('Frame', 'controls', (look.frame + 2) % (len(art.frames) + 1))
    elif key == ord('p'):
        # cycle person focus: off -> color pop -> portrait blur -> mask preview -> off
        cv2.setTrackbarPos('Focus', 'controls', (look.focus + 1) % len(FOCUS_MODES))
    elif key == ord('['):
        cv2.setTrackbarPos('Preset', 'controls', (look.preset - 1) % len(PRESETS))
    elif key == ord(']'):
        cv2.setTrackbarPos('Preset', 'controls', (look.preset + 1) % len(PRESETS))
    elif key != -1 and chr(key & 0xFF) in PRESET_KEYS:
        cv2.setTrackbarPos('Preset', 'controls', min(PRESET_KEYS.index(chr(key & 0xFF)), len(PRESETS) - 1))

    # mouse, in the editor: click a slot to select it; click a prop to select it (it comes
    # to the front), drag it to move it, and use the wheel to resize it
    events, mouse_events[:] = mouse_events[:], []
    for event, sx, sy, flags in events:
        if not (showing_editor and editing) or editor_view is None:
            continue
        lx, ly = screen_to_layout(sx, sy, editor_view)
        slot = slots.current()
        if event == cv2.EVENT_LBUTTONDOWN:
            clicked = slots.slot_at(lx, ly, rects)
            if clicked is not None and clicked != slots.selected:
                # select that slot (the switch happens next frame); click again for its props
                cv2.setTrackbarPos('Slot', 'controls', clicked + 1)
                selected_prop, drag_offset = None, None
                break
            point = photo_point(slots.selected, lx, ly)
            hit = None
            if point is not None and slot.image is not None:
                hit = prop_at(slot.look.props, art.props, *point, slot.image.shape[1], slot.image.shape[0])
            if hit is None:
                selected_prop, drag_offset = None, None
            else:
                set_props(bring_to_front(slot.look.props, hit))
                selected_prop = len(slots.current().look.props) - 1
                placed = slots.current().look.props[selected_prop]
                drag_offset = (placed.x - point[0], placed.y - point[1])
        elif event == cv2.EVENT_MOUSEMOVE and drag_offset is not None and flags & cv2.EVENT_FLAG_LBUTTON:
            point = photo_point(slots.selected, lx, ly)
            if point is not None and selected_prop is not None:
                set_props(move_prop(slot.look.props, selected_prop, point[0] + drag_offset[0], point[1] + drag_offset[1]))
        elif event == cv2.EVENT_LBUTTONUP:
            drag_offset = None
        elif event == cv2.EVENT_MOUSEWHEEL and selected_prop is not None:
            # the wheel's direction is in the top bits of flags: positive = up (bigger)
            factor = 1.1 if flags > 0 else 1 / 1.1
            set_props(resize_prop(slot.look.props, selected_prop, factor))

    # anything drawn on `shown` is only on screen, never in saved photos
    # the label is the preset's name, plus the focus mode when one is on
    label = PRESETS[look.preset][0] + (f' + {FOCUS_MODES[look.focus]}' if look.focus else '')
    if showing_editor:
        # messages show in the editor's title bar, in place of the first line of hints
        slot = slots.current()
        prop_rect = None
        if selected_prop is not None and selected_prop < len(slot.look.props) and slots.selected in slots.photo_rects:
            # outline the selected prop: its box in the photo, scaled into the layout
            placed = slot.look.props[selected_prop]
            x, y, w, h = slots.photo_rects[slots.selected]
            s = w / slot.image.shape[1]
            cx, cy, pw, ph = prop_box(placed, art.props[placed.prop], slot.image.shape[1], slot.image.shape[0])
            prop_rect = (x + (cx - pw / 2) * s, y + (cy - ph / 2) * s, pw * s, ph * s)
            label += f'  [{art.prop_names[placed.prop]}]'
        title = f'Editing slot {slots.selected + 1} of {SLOT_COUNT} ({layout}): {label}'
        hints = ['TAB next slot  L strip/grid  U upload  X clear  S save  E camera  R reset',
                 f'Props: I add "{art.prop_names[prop_choice]}"  drag to move  wheel or +/- size  D delete'
                 if art.props else '']
        shown, editor_view = editor_screen(picture, rects[slots.selected], title, hints, prop_rect,
                                           message if time.time() < message_until else None)
    else:
        shown = picture.copy()
        outlined_text(shown, label, (20, 40), 1.2, 2, 6)
        outlined_text(shown, 'SPACE strip  A add to slot  E editor  S save  U upload  W webcam  R reset  Q quit', (20, 70), 0.5, 1, 4)

        # photo strip: count down, take a shot, repeat, then save the strip and open
        # it in the editor, so each photo can be edited on its own
        seconds_left, strip = photo_strip.update(picture, time.time(), original=(img, look))
        if strip is not None:
            save_picture('strip', strip)
            for i, (shot, shot_look) in enumerate(photo_strip.originals[:SLOT_COUNT]):
                slots.put(i, shot, shot_look, tracker)
            last_filled = 0
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
