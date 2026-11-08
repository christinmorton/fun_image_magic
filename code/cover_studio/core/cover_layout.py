# cover_layout: where the words go on a square cover. A layout puts each text piece (the
# presents line, name, featuring list, sticker and title) in a box measured in fractions of
# the cover, so one layout works at preview size and at print size. Words are drawn at
# their final size to fit their box (never stretched), into a transparent layer the size
# of the cover that is laid over the artwork. Layouts follow docs/merch-styles/new-orleans.md
# and keep the top and bottom fifths for the name and title, where the artwork is plain.
from dataclasses import dataclass, field

import cv2
import numpy as np

from .finish import age
from .lettering import (FONT_OF, PAD, draw_words, featuring_list, finish, load_font, paste, plain, sticker,
                        text_mask)

PIECES = ['sticker', 'featuring', 'presents', 'title', 'name']     # drawing order: the name ends on top

# ready-made stickers: (name, lines, style). The wording can be changed; never the real
# Parental Advisory mark, which is a trademark
STICKERS = [
    ('No sticker', (), 'badge'),
    ('Hood Classic', ('CERTIFIED', 'HOOD CLASSIC'), 'badge'),
    ('Street Certified', ('STREET', 'CERTIFIED'), 'stamp'),
    ('Warning', ('WARNING', 'TOO HOT FOR RADIO'), 'hazard'),
]


@dataclass(frozen=True)
class Spot:
    x: float                # the box's left edge, top edge, width and height, as fractions
    y: float                # of the cover's size (0 = left/top, 1 = right/bottom)
    w: float
    h: float
    align: str = 'center'   # 'left', 'center' or 'right' inside the box
    bend: float = 0.0       # arch the words: + bows them up, - sags them (fraction of their height)
    recede: float = 0.0     # perspective: the top is this much narrower than the bottom (0-1)


@dataclass(frozen=True)
class CoverLayout:
    key: str
    name: str
    spots: dict                         # piece -> Spot (pieces without a spot aren't shown)
    styles: dict                        # 'name' / 'title' -> a lettering treatment
    heading: str = 'Featuring:'         # the featuring list's label ('' for none)
    heading_inline: bool = False        # the label to the left of the names, not above them


@dataclass
class CoverWords:
    # everything written on one cover; empty pieces are simply left out
    name: str
    title: str = ''
    presents: str = ''
    featuring: tuple = ()
    sticker: tuple = ('CERTIFIED', 'HOOD CLASSIC')


LAYOUTS = {layout.key: layout for layout in [
    CoverLayout('hero', 'Hero', {
        'presents': Spot(0.2, 0.012, 0.6, 0.04),
        'name': Spot(0.04, 0.07, 0.92, 0.14),
        'featuring': Spot(0.70, 0.27, 0.28, 0.40),
        'sticker': Spot(0.03, 0.65, 0.22, 0.10, align='left'),
        'title': Spot(0.06, 0.81, 0.88, 0.16, bend=0.25),
    }, {'name': 'gold', 'title': 'ice'}),
    CoverLayout('head_in_the_sky', 'Head in the sky', {
        'name': Spot(0.04, 0.025, 0.92, 0.16),
        'featuring': Spot(0.02, 0.48, 0.27, 0.32),
        'sticker': Spot(0.75, 0.65, 0.22, 0.10, align='right'),
        'title': Spot(0.06, 0.82, 0.88, 0.15, bend=-0.3),
    }, {'name': 'ice', 'title': 'gold'}),
    CoverLayout('boss_desk', 'Boss desk', {
        'name': Spot(0.03, 0.02, 0.5, 0.2, align='left'),
        'presents': Spot(0.55, 0.025, 0.42, 0.045),
        'featuring': Spot(0.55, 0.08, 0.42, 0.22),
        'sticker': Spot(0.03, 0.62, 0.22, 0.10, align='left'),
        'title': Spot(0.03, 0.84, 0.94, 0.13),
    }, {'name': 'brush', 'title': 'serif'}),
    CoverLayout('crew_row', 'Crew row', {
        'name': Spot(0.06, 0.025, 0.88, 0.16, bend=0.2),
        'sticker': Spot(0.03, 0.21, 0.2, 0.09, align='left'),
        'featuring': Spot(0.12, 0.735, 0.76, 0.065),
        'title': Spot(0.04, 0.80, 0.92, 0.17, recede=0.25),
    }, {'name': 'gold', 'title': 'chrome'}, heading='Feat.', heading_inline=True),
]}


def fit_size(text, font_name, width, height, stretch=1.0):
    # the biggest font size (px) at which the words' ink fits width x height, allowing for
    # a bend or other change that makes them `stretch` times taller
    left, top, right, bottom = load_font(font_name, 100).getbbox(text)
    return max(8, int(min(width * 100 / max(right - left, 1), height * 100 / max((bottom - top) * stretch, 1))))

def arch(img, bend, pad=0):
    # bow the words up (bend > 0) or sag them (bend < 0) by about |bend| times their height.
    # The curve spans the ink (inside `pad` empty pixels at each side), and is gentler for
    # short words, which a full arch would squash
    h, w = img.shape[:2]
    ink_w, ink_h = max(w - 2 * pad, 1), max(h - 2 * pad, 1)
    amount = abs(bend) * ink_h * min(1.0, ink_w / (4 * ink_h))
    u = np.clip((np.arange(w, dtype=np.float32) - w / 2) / (ink_w / 2), -1, 1)
    lift = amount * (1 - u * u) if bend > 0 else amount * u * u
    out_h = h + int(np.ceil(amount))
    map_x = np.tile(np.arange(w, dtype=np.float32), (out_h, 1))
    map_y = (np.arange(out_h, dtype=np.float32)[:, None] - amount + lift[None, :]).astype(np.float32)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)

def recede(img, amount):
    # perspective, like words lying on the ground: the top is `amount` narrower than the bottom
    h, w = img.shape[:2]
    inset = w * amount / 2
    corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    moved = np.float32([[inset, 0], [w - inset, 0], [w, h], [0, h]])
    return cv2.warpPerspective(img, cv2.getPerspectiveTransform(corners, moved), (w, h))

def ink_box(mask):
    # where the letters actually are in a mask: (x, y, width, height)
    ys, xs = np.where(mask > 0.5)
    if not len(xs):
        return 0, 0, mask.shape[1], mask.shape[0]
    return int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)

def shaped(img, spot, pad):
    # the spot's arch and perspective, applied the same way to a picture or a mask
    if spot.bend:
        img = arch(img, spot.bend, pad)
    if spot.recede:
        img = recede(img, spot.recede)
    return img

def fitted_words(text, treatment, spot, bw, bh, seed):
    # the words drawn as big as they can be while their letters, once arched or tilted,
    # still fit inside bw x bh: (BGRA image, where the letters are in it)
    font = FONT_OF[treatment]
    size = fit_size(text, font, bw, bh, 1 + abs(spot.bend) / 2)
    for _ in range(4):
        box = ink_box(shaped(text_mask(text, font, size, int(size * PAD)), spot, int(size * PAD)))
        fit = min(bw / box[2], bh / box[3])
        if 0.96 <= fit <= 1.0:
            break
        size = max(8, int(size * fit * 0.99))
    pad = int(size * PAD)
    box = ink_box(shaped(text_mask(text, font, size, pad), spot, pad))
    return shaped(draw_words(text, treatment, size, seed), spot, pad), box

def piece_image(piece, words, layout, styles, bw, bh, seed):
    # one text piece drawn to fit a bw x bh box: (BGRA image, where its letters are in it
    # as (x, y, width, height)), or None if the piece is empty. Pieces are placed by their
    # letters, not by the empty space kept around them for glows
    if piece in ('name', 'title'):
        text = getattr(words, piece).strip()
        if not text:
            return None
        return fitted_words(text, styles[piece], layout.spots[piece], bw, bh, seed)
    if piece == 'presents':
        text = words.presents.strip().upper()
        if not text:
            return None
        size = fit_size(text, 'serif', bw, bh)
        img, pad = plain(text, 'serif', size), int(size * PAD)
        return img, (pad, pad, img.shape[1] - 2 * pad, img.shape[0] - 2 * pad)
    if piece == 'featuring':
        if not any(n.strip() for n in words.featuring):
            return None
        img = featuring_list(words.featuring, int(bw), int(bh), layout.heading, inline=layout.heading_inline)
        return img, (0, 0, img.shape[1], img.shape[0])
    if not any(line.strip() for line in words.sticker):
        return None
    style = styles.get('sticker', 'badge')
    img = sticker(words.sticker, int(bh), style, seed)
    fit = min(bw / img.shape[1], bh / img.shape[0])
    if fit < 1:                                             # long wording or a tilt: a smaller sticker
        img = sticker(words.sticker, max(int(bh * fit), 20), style, seed)
    return img, (0, 0, img.shape[1], img.shape[0])

def draw_cover_lettering(words, layout, size, styles=None, seed=0, finishes=None, strength=1.0):
    # every piece of `words` placed by `layout` on a size x size cover, as a BGRA layer.
    # styles can swap the treatment of the name or title, e.g. {'name': 'chrome'}, and
    # choose the sticker's look, e.g. {'sticker': 'stamp'}. finishes ages each piece on
    # its own, e.g. {'name': 'vhs', 'title': 'print'} (pieces left out stay clean)
    if isinstance(layout, str):
        layout = LAYOUTS[layout]
    styles = {**layout.styles, **(styles or {})}
    finishes = finishes or {}
    bgr, alpha = np.zeros((size, size, 3), np.float32), np.zeros((size, size), np.float32)
    for piece in PIECES:
        spot = layout.spots.get(piece)
        if spot is None:
            continue
        bx, by, bw, bh = spot.x * size, spot.y * size, spot.w * size, spot.h * size
        drawn = piece_image(piece, words, layout, styles, bw, bh, seed)
        if drawn is None:
            continue
        img, (ix, iy, iw, ih) = drawn
        if finishes.get(piece, 'clean') != 'clean':
            img = age(img, finishes[piece], strength, seed + PIECES.index(piece), unit_size=size)
        x = {'left': bx - ix, 'right': bx + bw - ix - iw}.get(spot.align, bx + (bw - iw) / 2 - ix)
        bgr, alpha = paste(bgr, alpha, img, x, by + (bh - ih) / 2 - iy)
    return finish(bgr, alpha)

def apply_lettering(picture, lettering):
    # lay the lettering layer over a BGR picture of the same size
    if picture.shape[:2] != lettering.shape[:2]:
        picture = cv2.resize(picture, (lettering.shape[1], lettering.shape[0]), interpolation=cv2.INTER_AREA)
    a = lettering[..., 3:] / 255.0
    return (lettering[..., :3] * a + picture * (1 - a)).astype(np.uint8)

def square_crop(img):
    # the biggest square from the middle of a picture (covers are square)
    h, w = img.shape[:2]
    side = min(h, w)
    y, x = (h - side) // 2, (w - side) // 2
    return img[y:y + side, x:x + side]

def placeholder(size, people=1):
    # a stand-in picture until there's real artwork: a dark-red-to-orange background with
    # grey silhouettes where the people would stand
    t = np.linspace(0, 1, size)[:, None, None]
    img = np.repeat((np.array([20, 30, 110]) * (1 - t) + np.array([30, 140, 255]) * t).astype(np.uint8), size, axis=1)
    scale = 1.0 if people == 1 else 0.6
    for i in range(people):
        cx = int(size * (i + 1) / (people + 1))
        cv2.ellipse(img, (cx, int(size * 0.62)), (int(size * 0.2 * scale), int(size * 0.28 * scale)), 0, 180, 360,
                    (70, 70, 70), -1, cv2.LINE_AA)
        cv2.circle(img, (cx, int(size * (0.4 if people == 1 else 0.48))), int(size * 0.11 * scale), (90, 90, 90),
                   -1, cv2.LINE_AA)
    return img
