# look: all the settings that decide how a picture is edited (a "look"), and render(),
# which turns an unedited picture plus a look into the finished picture.
from dataclasses import dataclass

import cv2

from filters import KERNELS, PRESETS
from overlays import add_face_sticker, add_mascot, apply_overlay, swap_background


@dataclass
class Look:
    contrast: int = 1          # the course sliders
    brightness: int = 50       # 50 = no change
    kernel: int = 0            # index into KERNELS
    grayscale: int = 0         # 0 = colour, 1 = grey
    preset: int = 0            # index into PRESETS
    sticker: int = -1          # index into the stickers, -1 = off
    background: int = -1       # index into the backgrounds, -1 = off
    mascot: bool = False
    frame: int = -1            # index into the frames, -1 = off


def render(img, look, art, faces=(), person_mask=None):
    # img is the unedited picture; faces and person_mask come from Tracker.analyse()
    color_original = img
    if look.background >= 0:
        color_original = swap_background(color_original, person_mask, art.backgrounds[look.background])

    # pick colour or grey first, so only the version on screen gets processed
    if look.grayscale == 0:
        modified = color_original
    else:
        modified = cv2.cvtColor(color_original, cv2.COLOR_BGR2GRAY)

    # apply the filter
    modified = cv2.filter2D(modified, -1, KERNELS[look.kernel])

    # apply the brightness and contrast (the second image has weight 0, so it can be any
    # same-size image; reusing this one avoids building a new all-zero image every frame)
    modified = cv2.addWeighted(modified, look.contrast, modified, 0, look.brightness - 50)

    # then the preset, stickers, mascot and frame (in that order)
    picture = modified if look.grayscale == 0 else cv2.cvtColor(modified, cv2.COLOR_GRAY2BGR)

    picture = PRESETS[look.preset][1](picture)
    if look.sticker >= 0:
        picture = add_face_sticker(picture, faces, *art.stickers[look.sticker])
    if look.mascot and art.mascot is not None:
        picture = add_mascot(picture, art.mascot)
    if look.frame >= 0:
        picture = apply_overlay(picture, art.frames[look.frame])
    return picture
