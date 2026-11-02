# look: all the settings that decide how a picture is edited (a "look"), and render(),
# which turns an unedited picture plus a look into the finished picture.
from dataclasses import dataclass

import cv2

from .filters import KERNELS, MOVES_PIXELS, PRESETS
from .masks import apply_focus, refine_mask
from .overlays import add_face_sticker, add_mascot, apply_overlay, swap_background
from .props import draw_props


@dataclass
class Look:
    contrast: float = 1.0      # the course sliders; 1.0 = no change
    brightness: int = 50       # 50 = no change
    kernel: int = 0            # index into KERNELS
    grayscale: int = 0         # 0 = colour, 1 = grey
    preset: int = 0            # index into PRESETS
    sticker: int = -1          # index into the stickers, -1 = off
    background: int = -1       # index into the backgrounds, -1 = off
    mascot: int = -1           # index into the mascot poses, -1 = off
    frame: int = -1            # index into the frames, -1 = off
    focus: int = 0             # index into masks.FOCUS_MODES, 0 = off
    props: tuple = ()          # scene props placed in this photo (props.PlacedProp), last on top

    def needs_person_mask(self):
        return self.background >= 0 or self.focus > 0


def render(img, look, art, faces=(), person_mask=None):
    # img is the unedited picture; faces and person_mask come from Tracker.analyse()
    color_original = img

    # the person mask is cleaned up once, then used by the background swap and focus effects
    mask = refine_mask(person_mask, img) if look.needs_person_mask() and person_mask is not None else None
    if look.background >= 0 and mask is not None:
        color_original = swap_background(color_original, mask, art.backgrounds[look.background])
    if look.focus > 0 and mask is not None:
        color_original = apply_focus(color_original, look.focus, mask)

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

    # stickers go on top of the preset, except for presets that move pixels around
    name, effect = PRESETS[look.preset]
    stickers_first = name in MOVES_PIXELS
    if look.sticker >= 0 and stickers_first:
        picture = add_face_sticker(picture, faces, *art.stickers[look.sticker])
    picture = effect(picture)
    if look.sticker >= 0 and not stickers_first:
        picture = add_face_sticker(picture, faces, *art.stickers[look.sticker])
    if look.mascot >= 0:
        picture = add_mascot(picture, art.mascots[look.mascot])
    if look.props:
        picture = draw_props(picture, look.props, art.props)
    if look.frame >= 0:
        picture = apply_overlay(picture, art.frames[look.frame])
    return picture
