# slots: the four-slot editor. Each slot holds an unedited photo and its own look, so the
# four photos can be edited differently, then shown and saved together as a vertical
# strip or a 2x2 grid.
from dataclasses import astuple, dataclass, field, replace

import cv2
import numpy as np

from look import Look, render


SLOT_COUNT = 4
LAYOUTS = ['Strip', 'Grid']
BORDER = 12               # white border around each photo, like the photo strip


@dataclass
class Slot:
    image: object = None                          # the unedited photo (BGR), or None if empty
    look: Look = field(default_factory=Look)
    faces: list = field(default_factory=list)     # from Tracker.analyse_still()
    person_mask: object = None
    rendered: tuple = None                        # (look values, finished picture), so a slot
                                                  # is only re-rendered when its look changes

    def picture(self, art):
        key = astuple(self.look)
        if self.rendered is None or self.rendered[0] != key:
            self.rendered = (key, render(self.image.copy(), self.look, art, self.faces, self.person_mask))
        return self.rendered[1]


def fit_into(img, w, h, fill=255):
    # shrink or grow img to fit inside w x h without changing its shape, centred on a plain background
    scale = min(w / img.shape[1], h / img.shape[0])
    iw, ih = max(round(img.shape[1] * scale), 1), max(round(img.shape[0] * scale), 1)
    out = np.full((h, w, 3), fill, np.uint8)
    x, y = (w - iw) // 2, (h - ih) // 2
    out[y:y + ih, x:x + iw] = cv2.resize(img, (iw, ih), interpolation=cv2.INTER_AREA)
    return out

def empty_cell(w, h, number):
    # what an empty slot looks like on screen
    cell = np.full((h, w, 3), 70, np.uint8)
    for text, y, scale in [(f'Slot {number}', h // 2 - 10, 1.4), ('empty', h // 2 + 40, 1.0)]:
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        cv2.putText(cell, text, ((w - tw) // 2, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (200, 200, 200), 2, cv2.LINE_AA)
    return cell


class Slots:
    def __init__(self):
        self.slots = [Slot() for _ in range(SLOT_COUNT)]
        self.selected = 0

    def current(self):
        return self.slots[self.selected]

    def put(self, index, image, look, tracker):
        # fill a slot with a photo and a copy of a look (faces / person found once, here)
        faces, person_mask = tracker.analyse_still(image)
        self.slots[index] = Slot(image.copy(), replace(look), faces, person_mask)

    def clear(self, index):
        self.slots[index] = Slot()

    def any_filled(self):
        return any(slot.image is not None for slot in self.slots)

    def cell_size(self):
        # every cell is the size of the first photo (others are fitted inside it)
        for slot in self.slots:
            if slot.image is not None:
                return slot.image.shape[1], slot.image.shape[0]
        return 640, 480

    def compose(self, art, layout, for_saving=False):
        # the finished strip or grid, and each slot's rectangle (x, y, w, h) in it
        # on screen, empty slots show as grey placeholders; when saving, a strip leaves
        # them out and a grid shows them as plain white
        cw, ch = self.cell_size()
        cells = []
        for i, slot in enumerate(self.slots):
            if slot.image is not None:
                cell = fit_into(slot.picture(art), cw, ch)
            elif not for_saving:
                cell = empty_cell(cw, ch, i + 1)
            elif layout == 'Grid':
                cell = np.full((ch, cw, 3), 255, np.uint8)
            else:
                continue
            cells.append((i, cv2.copyMakeBorder(cell, BORDER, BORDER, BORDER, BORDER,
                                                cv2.BORDER_CONSTANT, value=(255, 255, 255))))
        if not cells:
            return None, {}
        bw, bh = cw + 2 * BORDER, ch + 2 * BORDER
        if layout == 'Strip':
            img = np.vstack([cell for _, cell in cells])
            rects = {i: (0, k * bh, bw, bh) for k, (i, _) in enumerate(cells)}
        else:
            img = np.vstack([np.hstack([cells[0][1], cells[1][1]]), np.hstack([cells[2][1], cells[3][1]])])
            rects = {i: ((k % 2) * bw, (k // 2) * bh, bw, bh) for k, (i, _) in enumerate(cells)}
        return img, rects
