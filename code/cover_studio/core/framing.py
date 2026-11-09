# framing: where the artwork sits under the lettering. The AI doesn't always leave room
# for the name and title, so the artwork can be moved and zoomed (a Framing), and
# auto_framing() finds the face and moves the artwork so the name and title don't cover
# it. Any part of the cover the moved artwork no longer reaches is filled with a blurred,
# darkened stretch of the artwork itself.
from dataclasses import dataclass

import cv2
import numpy as np

from .cover_layout import LAYOUTS, square_crop
from .scan import face_box
from .upscale import upscale

MARGIN = 0.03           # space kept between the face and the name or title (glows reach out a bit)


@dataclass(frozen=True)
class Framing:
    zoom: float = 1.0   # the artwork's size compared with the cover (below 1 shows all of it, smaller)
    dx: float = 0.0     # how far it's moved right, as a fraction of the cover's width
    dy: float = 0.0     # how far it's moved down, as a fraction of the cover's height


def blurred_fill(img, width, height, darken=0.55):
    # img zoomed to cover width x height, heavily blurred and darkened: a background that
    # carries the artwork's colours out to the edges
    scale = max(width / img.shape[1], height / img.shape[0])
    big = cv2.resize(img, (int(img.shape[1] * scale) + 1, int(img.shape[0] * scale) + 1), interpolation=cv2.INTER_AREA)
    y, x = (big.shape[0] - height) // 2, (big.shape[1] - width) // 2
    small = cv2.resize(big[y:y + height, x:x + width], (max(1, width // 8), max(1, height // 8)), interpolation=cv2.INTER_AREA)
    soft = cv2.GaussianBlur(small, (0, 0), max(width, height) / 160)
    return (cv2.resize(soft, (width, height), interpolation=cv2.INTER_CUBIC) * darken).astype(np.uint8)

def frame_artwork(art, side, framing=Framing(), quality='fast'):
    # the artwork as a side x side cover picture, moved and zoomed by `framing`
    art = square_crop(art)
    size = max(1, round(side * framing.zoom))
    if size > art.shape[0]:
        scaled = upscale(art, size, size, quality)
    else:
        scaled = cv2.resize(art, (size, size), interpolation=cv2.INTER_AREA)
    if framing == Framing():
        return scaled
    canvas = blurred_fill(scaled, side, side)
    x = round((side - size) / 2 + framing.dx * side)
    y = round((side - size) / 2 + framing.dy * side)
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + size, side), min(y + size, side)
    if x0 < x1 and y0 < y1:
        canvas[y0:y1, x0:x1] = scaled[y0 - y:y1 - y, x0 - x:x1 - x]
    return canvas

def face_span(art, detect):
    # the top and bottom of all the faces in the artwork, as fractions of its height, or None
    art = square_crop(art)
    faces = detect(art)
    if not faces:
        return None
    side = art.shape[0]
    boxes = [face_box(face.landmarks, side, side) for face in faces]
    return min(b[1] for b in boxes) / side, max(b[3] for b in boxes) / side

def auto_framing(art, layout, detect):
    # a Framing that keeps the faces clear of the layout's name and title: moved down
    # (or up) just enough, and zoomed out a little if they can't fit between the two.
    # No faces found: no change
    if isinstance(layout, str):
        layout = LAYOUTS[layout]
    span = face_span(art, detect)
    if span is None:
        return Framing()
    top, bottom = span
    name, title = layout.spots.get('name'), layout.spots.get('title')
    clear_top = name.y + name.h + MARGIN if name else 0.0
    clear_bottom = title.y - MARGIN if title else 1.0
    if top >= clear_top and bottom <= clear_bottom:
        return Framing()
    if bottom - top <= clear_bottom - clear_top:
        dy = clear_top - top if top < clear_top else clear_bottom - bottom
        return Framing(1.0, 0.0, round(dy, 3))
    # too tall to fit: zoom out around the middle, then move the faces' top just below the name
    zoom = (clear_bottom - clear_top) / (bottom - top)
    return Framing(round(zoom, 3), 0.0, round(clear_top - (0.5 + (top - 0.5) * zoom), 3))
