# props: scene props - plain transparent PNGs (signs, a trophy, Cody poses...) that are
# placed in a photo and moved by hand in the editor. Unlike face stickers they don't
# follow anyone; each slot's look keeps a list of where its props are.
from dataclasses import dataclass, replace

import cv2

from overlays import paste_centered


MIN_SIZE, MAX_SIZE = 0.08, 1.5      # prop height, as a fraction of the photo's height


@dataclass(frozen=True)
class PlacedProp:
    prop: int            # index into art.props
    x: float             # centre, as a fraction of the photo's width (0 = left, 1 = right)
    y: float             # centre, as a fraction of the photo's height (0 = top, 1 = bottom)
    size: float = 0.5    # height, as a fraction of the photo's height

    # fractions (not pixels) keep a prop in the same place at any photo or preview size


def prop_box(placed, prop_img, w, h):
    # where a placed prop sits in a w x h photo: (centre x, centre y, width, height) in pixels
    ph = max(int(placed.size * h), 1)
    pw = max(int(prop_img.shape[1] * ph / prop_img.shape[0]), 1)
    return placed.x * w, placed.y * h, pw, ph

def draw_props(img, placed_props, prop_images):
    # props are drawn in list order, so the last one is on top
    h, w = img.shape[:2]
    for placed in placed_props:
        prop_img = prop_images[placed.prop]
        cx, cy, pw, ph = prop_box(placed, prop_img, w, h)
        paste_centered(img, cv2.resize(prop_img, (pw, ph), interpolation=cv2.INTER_AREA), cx, cy)
    return img

def prop_at(placed_props, prop_images, u, v, w, h):
    # index of the top prop under the point (u, v) (fractions of the photo), or None.
    # See-through parts of a prop don't count, so you can click "through" its corners
    for i in range(len(placed_props) - 1, -1, -1):
        placed = placed_props[i]
        prop_img = prop_images[placed.prop]
        cx, cy, pw, ph = prop_box(placed, prop_img, w, h)
        px, py = u * w - (cx - pw / 2), v * h - (cy - ph / 2)      # point inside the prop's box
        if 0 <= px < pw and 0 <= py < ph:
            ix = min(int(px * prop_img.shape[1] / pw), prop_img.shape[1] - 1)
            iy = min(int(py * prop_img.shape[0] / ph), prop_img.shape[0] - 1)
            if prop_img[iy, ix, 3] > 32:
                return i
    return None


# props lists are tuples (so a look can be copied and compared safely); these helpers
# return a new tuple instead of changing the old one

def add_prop(placed_props, prop, size=0.5):
    return placed_props + (PlacedProp(prop, 0.5, 0.5, size),)

def bring_to_front(placed_props, i):
    return placed_props[:i] + placed_props[i + 1:] + (placed_props[i],)

def move_prop(placed_props, i, x, y):
    x, y = min(max(x, 0.0), 1.0), min(max(y, 0.0), 1.0)          # keep the centre on the photo
    return placed_props[:i] + (replace(placed_props[i], x=x, y=y),) + placed_props[i + 1:]

def resize_prop(placed_props, i, factor):
    size = min(max(placed_props[i].size * factor, MIN_SIZE), MAX_SIZE)
    return placed_props[:i] + (replace(placed_props[i], size=size),) + placed_props[i + 1:]

def remove_prop(placed_props, i):
    return placed_props[:i] + placed_props[i + 1:]
