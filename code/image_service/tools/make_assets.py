#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Makes the placeholder art in core/assets/: frames, face stickers, backgrounds, scene props
# and mascot poses, using the name, cheer and colours in core/brand.py.
# Run it again after changing the brand:   python tools/make_assets.py
# Replace any file in core/assets/ with real art (same name) and the app will use it.
# The mascot poses are only drawn when core/assets/mascot/ has no art, so a real mascot
# (e.g. Photoshop cut-outs) is never overwritten. Delete them to draw the placeholders again.
import sys
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core import ASSETS_DIR                                                    # noqa: E402
from core.brand import (ACCENT, CHEER, DARK, EXTRAS, FULL_NAME, NAME, PRIMARY,  # noqa: E402
                        SHORT_NAME, bgr)

# colours that aren't the brand's, in BGR order
WHITE = (255, 255, 255)
OFF_WHITE = (241, 241, 241)
GOLD = bgr('#FFC21A')                 # the crown and the trophy
SKY_PURPLE = (138, 47, 49)            # #312F8A, the desert-sunset and Las Vegas skies
PALETTE = [DARK, PRIMARY, *EXTRAS, ACCENT]   # every brand colour (stripes, confetti)

FONT = cv2.FONT_HERSHEY_DUPLEX
rng = np.random.default_rng(7)   # fixed seed, so the art is the same every run


def bgra(color, alpha=255):
    return (*color, alpha)

def shade(color, factor):
    # a darker (factor < 1) or lighter (factor > 1) version of a colour
    return tuple(min(255, int(c * factor)) for c in color)

def text_at(img, text, cx, cy, scale, color, thickness, font=FONT, max_width=None):
    # draws text centred on (cx, cy); text wider than max_width is made smaller to fit,
    # so any brand name or cheer fits its space
    (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    if max_width and tw > max_width:
        shrink = max_width / tw
        scale, thickness = scale * shrink, max(1, round(thickness * shrink))
        (tw, th), _ = cv2.getTextSize(text, font, scale, thickness)
    cv2.putText(img, text, (int(cx - tw / 2), int(cy + th / 2)), font, scale, color, thickness, cv2.LINE_AA)

def star_points(cx, cy, r, inner=0.45):
    # the 10 corners of a 5-pointed star, starting at the top
    angles = np.radians(np.arange(10) * 36 - 90)
    radii = np.where(np.arange(10) % 2 == 0, r, r * inner)
    return np.stack([cx + radii * np.cos(angles), cy + radii * np.sin(angles)], axis=1).astype(np.int32)

def gradient(h, w, stops):
    # vertical gradient through a list of (position 0-1, BGR colour) stops
    ys = np.linspace(0, 1, h)
    cols = [np.interp(ys, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)]
    return np.repeat(np.stack(cols, axis=1)[:, None, :], w, axis=1).astype(np.uint8)

def ridge(img, base_y, height, color, points=12):
    # a filled mountain ridge across the image
    h, w = img.shape[:2]
    xs = np.linspace(0, w, points)
    ys = base_y - rng.integers(0, height, points)
    line = np.stack([np.arange(w), np.interp(np.arange(w), xs, ys)], axis=1)
    poly = np.vstack([line, [[w, h], [0, h]]]).astype(np.int32)
    cv2.fillPoly(img, [poly], color, cv2.LINE_AA)

def save(img, *parts):
    path = ASSETS_DIR.joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), img)


# ---------------------------------------------------------------- frames (640x480, transparent middle)
def blank_frame():
    return np.zeros((480, 640, 4), np.uint8)

# 1: classic border in the main colour, with the name as the caption
f = blank_frame()
cv2.rectangle(f, (0, 0), (639, 479), bgra(PRIMARY), 32)
cv2.rectangle(f, (0, 420), (639, 479), bgra(PRIMARY), -1)
cv2.rectangle(f, (16, 16), (623, 420), bgra(ACCENT), 3)
text_at(f, NAME, 320, 450, 1.2, bgra(ACCENT), 2, max_width=560)
save(f, 'frames', '1_classic.png')

# 2: thick accent border with the cheer
f = blank_frame()
cv2.rectangle(f, (0, 0), (639, 479), bgra(ACCENT), 48)
cv2.rectangle(f, (0, 400), (639, 479), bgra(ACCENT), -1)
cv2.rectangle(f, (24, 24), (615, 400), bgra(PRIMARY), 4)
text_at(f, CHEER, 320, 440, 1.4, bgra(PRIMARY), 3, max_width=560)
save(f, 'frames', '2_cheer.png')

# 3: instant-photo style, wide bottom edge with a handwritten caption
f = blank_frame()
f[:22], f[:, :22], f[:, -22:], f[-100:] = bgra(OFF_WHITE), bgra(OFF_WHITE), bgra(OFF_WHITE), bgra(OFF_WHITE)
cv2.rectangle(f, (22, 22), (617, 379), bgra((200, 200, 200)), 1)
text_at(f, FULL_NAME, 320, 428, 1.6, bgra(DARK), 2, cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, max_width=560)
save(f, 'frames', '3_polaroid.png')

# 4: film strip with sprocket holes and edge markings
f = blank_frame()
f[:, :56], f[:, -56:] = bgra((20, 20, 20)), bgra((20, 20, 20))
f[:26], f[-26:] = bgra((20, 20, 20)), bgra((20, 20, 20))
for y in range(40, 460, 44):
    for x in (16, 600):
        cv2.rectangle(f, (x, y), (x + 24, y + 26), bgra(OFF_WHITE), -1)
cv2.putText(f, f'{SHORT_NAME} 400      24      24A      25      25A', (80, 18), FONT, 0.45, bgra(ACCENT), 1, cv2.LINE_AA)
cv2.putText(f, FULL_NAME.upper(), (80, 472), FONT, 0.45, bgra(ACCENT), 1, cv2.LINE_AA)
save(f, 'frames', '4_film_strip.png')

# 5: stripes in every brand colour, with a round badge
f = blank_frame()
for i, color in enumerate(PALETTE):
    cv2.rectangle(f, (i * 7 + 3, i * 7 + 3), (636 - i * 7, 476 - i * 7), bgra(color), 7)
cv2.circle(f, (572, 410), 44, bgra(DARK), -1, cv2.LINE_AA)
cv2.circle(f, (572, 410), 44, bgra(ACCENT), 4, cv2.LINE_AA)
text_at(f, SHORT_NAME, 572, 410, 1.0, bgra(ACCENT), 2, max_width=70)
save(f, 'frames', '5_brand_stripes.png')

# 6: minimal accent corners and a see-through caption bar
f = blank_frame()
for (x, y, dx, dy) in [(20, 20, 1, 1), (619, 20, -1, 1), (20, 459, 1, -1), (619, 459, -1, -1)]:
    cv2.line(f, (x, y), (x + 70 * dx, y), bgra(ACCENT), 8, cv2.LINE_AA)
    cv2.line(f, (x, y), (x, y + 70 * dy), bgra(ACCENT), 8, cv2.LINE_AA)
f[400:440, 120:520] = bgra(DARK, 170)
text_at(f, FULL_NAME, 320, 420, 0.8, bgra(WHITE), 1, max_width=380)
save(f, 'frames', '6_corners.png')


# ---------------------------------------------------------------- face stickers (transparent)
# app.py places each sticker's centre between the eyes, then moves it up (or down) by the
# "lift" in its STICKERS list. Canvases have spare room so the sticker can tilt.

# sunglasses: lens centres on the canvas centre line
s = np.zeros((300, 300, 4), np.uint8)
for cx in (95, 205):
    cv2.ellipse(s, (cx, 150), (52, 38), 0, 0, 360, (30, 20, 20, 225), -1, cv2.LINE_AA)
    cv2.ellipse(s, (cx, 150), (52, 38), 0, 0, 360, (10, 10, 10, 255), 7, cv2.LINE_AA)
    cv2.ellipse(s, (cx - 18, 138), (14, 7), -20, 0, 360, (200, 200, 200, 120), -1, cv2.LINE_AA)
cv2.line(s, (143, 142), (157, 142), (10, 10, 10, 255), 7, cv2.LINE_AA)
cv2.line(s, (43, 140), (8, 130), (10, 10, 10, 255), 7, cv2.LINE_AA)
cv2.line(s, (257, 140), (292, 130), (10, 10, 10, 255), 7, cv2.LINE_AA)
save(s, 'stickers', 'sunglasses.png')

# party hat: brim near the bottom of the canvas
s = np.zeros((300, 300, 4), np.uint8)
pts = np.array([[150, 30], [62, 270], [238, 270]], np.int32)
cv2.fillPoly(s, [pts], bgra(PRIMARY), cv2.LINE_AA)
stripes, inside = np.zeros((300, 300), np.uint8), np.zeros((300, 300), np.uint8)
for y in range(60, 280, 45):
    cv2.line(stripes, (0, y + 40), (300, y - 40), 255, 12)
cv2.fillPoly(inside, [pts], 255)
s[(stripes > 0) & (inside > 0)] = bgra(ACCENT)
cv2.ellipse(s, (150, 270), (95, 14), 0, 0, 360, bgra(ACCENT), -1, cv2.LINE_AA)
cv2.circle(s, (150, 28), 20, bgra(WHITE), -1, cv2.LINE_AA)
save(s, 'stickers', 'party_hat.png')

# cat ears (black with pink insides): ear bases near the bottom of the canvas
s = np.zeros((300, 300, 4), np.uint8)
for side in (1, -1):
    def mx(x):
        return x if side == 1 else 300 - x
    outer = np.array([[mx(35), 250], [mx(72), 35], [mx(145), 215]], np.int32)
    inner = np.array([[mx(60), 228], [mx(78), 85], [mx(124), 205]], np.int32)
    cv2.fillPoly(s, [outer], (45, 40, 40, 255), cv2.LINE_AA)
    cv2.polylines(s, [outer], True, (20, 18, 18, 255), 4, cv2.LINE_AA)
    cv2.fillPoly(s, [inner], bgra(bgr('#F4A6B8')), cv2.LINE_AA)
save(s, 'stickers', 'cat_ears.png')

# graduation cap in the brand colours with an accent tassel
s = np.zeros((300, 300, 4), np.uint8)
cv2.fillPoly(s, [np.array([[75, 130], [225, 130], [220, 215], [80, 215]], np.int32)], bgra(DARK), cv2.LINE_AA)
cv2.ellipse(s, (150, 215), (70, 14), 0, 0, 180, bgra(DARK), -1, cv2.LINE_AA)
board = np.array([[150, 70], [292, 120], [150, 170], [8, 120]], np.int32)
cv2.fillPoly(s, [board], bgra(PRIMARY), cv2.LINE_AA)
cv2.polylines(s, [board], True, bgra(DARK), 3, cv2.LINE_AA)
cv2.line(s, (150, 120), (262, 138), bgra(ACCENT), 4, cv2.LINE_AA)
cv2.line(s, (262, 138), (262, 205), bgra(ACCENT), 4, cv2.LINE_AA)
cv2.rectangle(s, (254, 200), (270, 245), bgra(ACCENT), -1)
cv2.circle(s, (150, 120), 8, bgra(ACCENT), -1, cv2.LINE_AA)
save(s, 'stickers', 'grad_cap.png')

# gold crown with jewels (300x200)
s = np.zeros((200, 300, 4), np.uint8)
crown = np.array([[30, 180], [30, 60], [90, 120], [150, 30], [210, 120], [270, 60], [270, 180]], np.int32)
cv2.fillPoly(s, [crown], bgra(GOLD), cv2.LINE_AA)
cv2.polylines(s, [crown], True, bgra((0, 150, 210)), 4, cv2.LINE_AA)
cv2.rectangle(s, (30, 150), (270, 182), bgra((0, 170, 230)), -1)
for x, color in [(90, bgr('#2ECC71')), (150, bgr('#3498DB')), (210, bgr('#9B59B6'))]:   # emerald, sapphire, amethyst
    cv2.circle(s, (x, 166), 11, bgra(color), -1, cv2.LINE_AA)
for x, y in [(30, 60), (150, 30), (270, 60)]:
    cv2.circle(s, (x, y), 11, bgra(WHITE), -1, cv2.LINE_AA)
save(s, 'stickers', 'crown.png')

# handlebar mustache (300x120): goes BELOW the eyes (negative lift)
s = np.zeros((120, 300, 4), np.uint8)
brown = (25, 40, 70, 255)
cv2.ellipse(s, (108, 62), (58, 26), 12, 0, 360, brown, -1, cv2.LINE_AA)
cv2.ellipse(s, (192, 62), (58, 26), -12, 0, 360, brown, -1, cv2.LINE_AA)
cv2.ellipse(s, (45, 52), (20, 18), 0, 90, 360, brown, 10, cv2.LINE_AA)
cv2.ellipse(s, (255, 52), (20, 18), 0, -180, 90, brown, 10, cv2.LINE_AA)
save(s, 'stickers', 'mustache.png')

# star-shaped glasses in the accent colour with main-colour rims
s = np.zeros((300, 300, 4), np.uint8)
for cx in (92, 208):
    star = star_points(cx, 150, 62)
    cv2.fillPoly(s, [star], bgra(ACCENT, 225), cv2.LINE_AA)
    cv2.polylines(s, [star], True, bgra(PRIMARY), 6, cv2.LINE_AA)
cv2.line(s, (140, 145), (160, 145), bgra(PRIMARY), 7, cv2.LINE_AA)
save(s, 'stickers', 'star_glasses.png')


# ---------------------------------------------------------------- backgrounds (1280x720)
H, W = 720, 1280

# celebration: brand-colour confetti
bg = gradient(H, W, [(0, DARK), (1, PRIMARY)])
confetti = [ACCENT, *EXTRAS, WHITE]
for _ in range(450):
    x, y = rng.integers(0, W), rng.integers(0, H)
    color = confetti[rng.integers(0, len(confetti))]
    box = cv2.boxPoints(((float(x), float(y)), (14.0, 7.0), float(rng.integers(0, 180))))
    cv2.fillPoly(bg, [box.astype(np.int32)], color, cv2.LINE_AA)
text_at(bg, 'CONGRATS!', W // 2, 150, 3.5, ACCENT, 9)
save(bg, 'backgrounds', 'celebration.jpg')

# basketball court: a wall in the brand colours with the name, wood floor with court lines
bg = gradient(H, W, [(0, DARK), (0.6, PRIMARY)])
text_at(bg, NAME, W // 2, 140, 3.0, ACCENT, 8, max_width=W - 160)
bg[400:430] = ACCENT
floor = gradient(H - 430, W, [(0, (60, 120, 180)), (1, (90, 160, 215))])
for x in range(-1600, 2900, 70):     # planks that meet far away, for depth
    cv2.line(floor, (640 + (x - 640) // 4, 0), (x, H - 430), (55, 105, 160), 2, cv2.LINE_AA)
bg[430:] = floor
cv2.ellipse(bg, (640, 720), (560, 200), 0, 180, 360, WHITE, 6, cv2.LINE_AA)
save(bg, 'backgrounds', 'court.jpg')

# desert sunset: purple-to-orange sky, big sun, red rock ridges
bg = gradient(H, W, [(0, SKY_PURPLE), (0.45, (150, 80, 230)), (0.75, (40, 140, 255))])
cv2.circle(bg, (640, 470), 170, (80, 210, 255), -1, cv2.LINE_AA)
for y in range(430, 640, 22):        # sliced sun lines
    cv2.line(bg, (400, y), (880, y), (60, 130, 245), 5)
ridge(bg, 520, 140, (70, 75, 185))
ridge(bg, 590, 110, (50, 50, 130))
ridge(bg, 660, 80, (40, 30, 70))
save(bg, 'backgrounds', 'desert_sunset.jpg')

# spotlights: the brand colours across a stage, with the cheer
t = np.linspace(0, 1, W)[None, :, None]
bg = (np.array(DARK) * (1 - t) + np.array(PRIMARY) * t)
bg = np.repeat(bg, H, axis=0).astype(np.float32)
for cx in (250, 640, 1030):
    light = np.zeros((H, W), np.float32)
    cv2.ellipse(light, (cx, 600), (200, 70), 0, 0, 360, 1.0, -1)
    light = cv2.GaussianBlur(light, (0, 0), 40)[..., None]
    bg = bg * (1 - 0.6 * light) + 255 * 0.6 * light
bg = np.clip(bg, 0, 255).astype(np.uint8)
text_at(bg, CHEER, W // 2, 170, 3.0, ACCENT, 6, max_width=W - 160)
save(bg, 'backgrounds', 'spotlights.jpg')

# space: stars and a ringed planet
bg = np.zeros((H, W, 3), np.float32)
bg[:] = np.linspace(40, 5, H)[:, None, None] * np.array([1.0, 0.4, 0.5])
for _ in range(500):
    x, y = rng.integers(0, W), rng.integers(0, H)
    b = int(rng.integers(120, 256))
    cv2.circle(bg, (int(x), int(y)), int(rng.integers(1, 3)), (b, b, b), -1, cv2.LINE_AA)
cv2.circle(bg, (1050, 170), 110, (60, 110, 200), -1, cv2.LINE_AA)
cv2.ellipse(bg, (1050, 170), (190, 30), -15, 0, 360, (150, 200, 230), 6, cv2.LINE_AA)
save(bg.astype(np.uint8), 'backgrounds', 'space.jpg')

# Vegas at night: skyline with lit windows, a needle tower and a neon sign
bg = gradient(H, W, [(0, (40, 15, 10)), (0.45, SKY_PURPLE), (0.8, (150, 40, 200))])
for _ in range(150):
    cv2.circle(bg, (int(rng.integers(0, W)), int(rng.integers(0, 300))), 1, (230, 230, 230), -1)
cv2.rectangle(bg, (1010, 140), (1030, 600), (35, 20, 30), -1)          # tower
cv2.ellipse(bg, (1020, 150), (55, 22), 0, 0, 360, (35, 20, 30), -1, cv2.LINE_AA)
cv2.line(bg, (1020, 128), (1020, 40), (35, 20, 30), 4)
x = 0
while x < W:
    bw, bh = int(rng.integers(50, 120)), int(rng.integers(120, 360))
    cv2.rectangle(bg, (x, 600 - bh), (x + bw, 600), (35, 20, 30), -1)
    for wy in range(600 - bh + 12, 590, 18):
        for wx in range(x + 8, x + bw - 8, 14):
            if rng.random() < 0.45:
                cv2.rectangle(bg, (wx, wy), (wx + 6, wy + 8), (110, 210, 255), -1)
    x += bw + int(rng.integers(4, 20))
bg[600:] = (30, 15, 25)
glow = np.zeros_like(bg)
text_at(glow, 'LAS VEGAS', W // 2 - 180, 110, 2.6, (200, 80, 255), 5)
cv2.line(glow, (0, 640), (W, 640), (255, 200, 0), 3)
cv2.line(glow, (0, 680), (W, 680), (200, 80, 255), 3)
bg = cv2.add(bg, cv2.add(glow, cv2.GaussianBlur(glow, (0, 0), 9)))
save(bg, 'backgrounds', 'vegas_night.jpg')

# ---------------------------------------------------------------- scene props (transparent)
# props are placed and moved by hand in the editor; the app trims see-through padding,
# so canvas sizes only need to be roomy enough
DARK_A, ACCENT_A, PRIMARY_A, WHITE_A = bgra(DARK), bgra(ACCENT), bgra(PRIMARY), bgra(WHITE)
STICK = (40, 90, 140, 255)          # wooden stick

# a hand-held sign with the cheer (its first word on top, the rest underneath)
p = np.zeros((520, 360, 4), np.uint8)
cv2.rectangle(p, (165, 290), (195, 519), STICK, -1)
cv2.rectangle(p, (20, 20), (340, 300), ACCENT_A, -1)
cv2.rectangle(p, (20, 20), (340, 300), PRIMARY_A, 10)
first, _, rest = CHEER.partition(' ')
if rest:
    text_at(p, first, 180, 105, 3.0, PRIMARY_A, 8, max_width=280)
    text_at(p, rest, 180, 215, 2.6, PRIMARY_A, 8, max_width=280)
else:
    text_at(p, first, 180, 160, 3.0, PRIMARY_A, 8, max_width=280)
save(p, 'props', '1_cheer_sign.png')

# a foam finger in the main colour with an accent "#1"
p = np.zeros((520, 300, 4), np.uint8)
cv2.rectangle(p, (110, 40), (190, 270), PRIMARY_A, -1)                     # finger
cv2.circle(p, (150, 42), 40, PRIMARY_A, -1, cv2.LINE_AA)                   # fingertip
cv2.rectangle(p, (40, 240), (260, 470), PRIMARY_A, -1)                     # hand
for x in (85, 140, 195):                                                   # folded fingers
    cv2.line(p, (x - 20, 250), (x + 20, 250), DARK_A, 4, cv2.LINE_AA)
cv2.rectangle(p, (60, 455), (240, 519), ACCENT_A, -1)                      # cuff
text_at(p, '#1', 150, 360, 2.4, ACCENT_A, 7)
save(p, 'props', '2_foam_finger.png')

# a gold trophy on a base in the main colour
p = np.zeros((460, 360, 4), np.uint8)
GOLD_A = bgra(GOLD)
for cx in (55, 305):                                                       # handles
    cv2.ellipse(p, (cx, 150), (45, 60), 0, 0, 360, GOLD_A, 16, cv2.LINE_AA)
cv2.ellipse(p, (180, 80), (130, 180), 0, 0, 180, GOLD_A, -1, cv2.LINE_AA)  # cup
cv2.ellipse(p, (180, 80), (130, 26), 0, 0, 360, (0, 170, 230, 255), -1, cv2.LINE_AA)   # rim
cv2.rectangle(p, (160, 250), (200, 340), GOLD_A, -1)                       # stem
cv2.rectangle(p, (110, 335), (250, 375), GOLD_A, -1)
cv2.rectangle(p, (80, 375), (280, 450), PRIMARY_A, -1)                     # base
text_at(p, SHORT_NAME, 180, 412, 1.4, GOLD_A, 3, max_width=180)
save(p, 'props', '3_trophy.png')

# a speech bubble with the cheer
p = np.zeros((330, 480, 4), np.uint8)
tail = np.array([[150, 225], [100, 320], [230, 245]], np.int32)
cv2.fillPoly(p, [tail], DARK_A, cv2.LINE_AA)
cv2.ellipse(p, (240, 140), (226, 126), 0, 0, 360, DARK_A, -1, cv2.LINE_AA)  # outline
cv2.fillPoly(p, [tail + np.array([[4, -8], [8, -22], [-8, -8]])], WHITE_A, cv2.LINE_AA)
cv2.ellipse(p, (240, 140), (219, 119), 0, 0, 360, WHITE_A, -1, cv2.LINE_AA)
text_at(p, CHEER, 240, 140, 1.5, PRIMARY_A, 4, max_width=360)
save(p, 'props', '4_speech_bubble.png')

# a pennant flag on a stick, with the short name
p = np.zeros((280, 520, 4), np.uint8)
cv2.rectangle(p, (20, 0), (40, 279), STICK, -1)
cv2.fillPoly(p, [np.array([[40, 20], [510, 120], [40, 220]], np.int32)], PRIMARY_A, cv2.LINE_AA)
cv2.rectangle(p, (40, 20), (80, 220), ACCENT_A, -1)
text_at(p, SHORT_NAME, 230, 120, 2.4, ACCENT_A, 7, max_width=220)
save(p, 'props', '5_pennant.png')


# ---------------------------------------------------------------- mascot poses (transparent)
# a round placeholder character in the brand colours, until an app adds its own mascot.
# The app trims see-through padding and stands the mascot in the bottom-right corner.
def mascot(pose):
    m = np.zeros((900, 700, 4), np.uint8)
    cx, cy = 350, 470                                        # the middle of the body
    limb = bgra(shade(PRIMARY, 0.8))
    # arms first, so the body covers the shoulders: (shoulder, hand) for each arm
    if pose == 'waving':
        arms = [((cx - 170, cy + 20), (cx - 255, cy + 170)), ((cx + 170, cy - 20), (cx + 285, cy - 250))]
    elif pose == 'cheering':
        arms = [((cx - 170, cy - 20), (cx - 285, cy - 250)), ((cx + 170, cy - 20), (cx + 285, cy - 250))]
    else:                                                    # peekaboo: hands up beside the face
        arms = [((cx - 170, cy + 40), (cx - 245, cy - 150)), ((cx + 170, cy + 40), (cx + 245, cy - 150))]
    for shoulder, hand in arms:
        cv2.line(m, shoulder, hand, limb, 46, cv2.LINE_AA)
        cv2.circle(m, hand, 46, limb, -1, cv2.LINE_AA)
    for fx in (cx - 95, cx + 95):                            # feet
        cv2.ellipse(m, (fx, cy + 245), (85, 38), 0, 0, 360, bgra(DARK), -1, cv2.LINE_AA)
    cv2.line(m, (cx, cy - 230), (cx + 25, cy - 320), bgra(DARK), 10, cv2.LINE_AA)   # antenna
    cv2.circle(m, (cx + 25, cy - 320), 26, bgra(ACCENT), -1, cv2.LINE_AA)
    cv2.ellipse(m, (cx, cy), (215, 250), 0, 0, 360, bgra(PRIMARY), -1, cv2.LINE_AA)   # body
    cv2.ellipse(m, (cx, cy + 130), (125, 105), 0, 0, 360, bgra(OFF_WHITE), -1, cv2.LINE_AA)   # tummy
    # face: big shiny eyes, rosy cheeks and a smile
    for ex in (cx - 78, cx + 78):
        cv2.ellipse(m, (ex, cy - 95), (46, 56), 0, 0, 360, bgra(WHITE), -1, cv2.LINE_AA)
        cv2.circle(m, (ex + 8, cy - 85), 25, bgra(DARK), -1, cv2.LINE_AA)
        cv2.circle(m, (ex + 17, cy - 96), 9, bgra(WHITE), -1, cv2.LINE_AA)
    for chx in (cx - 140, cx + 140):
        cv2.ellipse(m, (chx, cy - 30), (30, 19), 0, 0, 360, bgra(bgr('#FF8FA3')), -1, cv2.LINE_AA)
    cv2.ellipse(m, (cx, cy - 45), (62, 46), 0, 15, 165, bgra(DARK), 11, cv2.LINE_AA)
    if pose == 'peekaboo':
        m = m[:cy + 110]                                     # half body, cut off at the bottom
    return m

mascot_dir = ASSETS_DIR / 'mascot'
if any(mascot_dir.glob('*.png')):
    print('Kept the mascot art already in', mascot_dir, '(delete it to draw the placeholders again)')
else:
    for i, pose in enumerate(['waving', 'cheering', 'peekaboo'], start=1):
        save(mascot(pose), 'mascot', f'{i}_{pose}.png')

print('Placeholder art written to', ASSETS_DIR)
