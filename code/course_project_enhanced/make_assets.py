#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Makes the placeholder art in assets/: branded frames, face stickers, backgrounds and the
# Cody cut-out. Run it again after changing colours or text:   python make_assets.py
# Replace any file in assets/ with real art (same name) and app.py will use it instead.
from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / 'assets'
MASCOT_PHOTO = BASE_DIR.parent.parent / 'resources' / 'csn_assets' / 'mascot-2025.jpg'
SEGMENTER_MODEL = BASE_DIR / 'models' / 'selfie_segmenter.tflite'

# CSN brand colours in BGR order (from resources/csn_assets/brandingcolors_02.png)
GOLD = (1, 207, 255)          # #FFCF01
BLUE = (144, 73, 0)           # #004990
LIGHT_BLUE = (233, 170, 0)    # #00AAE9
GREEN = (76, 187, 94)         # #5EBB4C
PURPLE = (138, 47, 49)        # #312F8A
NAVY = (79, 34, 14)           # #0E224F
CHARCOAL = (62, 44, 39)       # #272C3E
OFF_WHITE = (241, 241, 241)   # #F1F1F1
WHITE = (255, 255, 255)

FONT = cv2.FONT_HERSHEY_DUPLEX
rng = np.random.default_rng(7)   # fixed seed, so the art is the same every run


def bgra(color, alpha=255):
    return (*color, alpha)

def text_at(img, text, cx, cy, scale, color, thickness, font=FONT):
    # draws text centred on (cx, cy)
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

# 1: classic blue border with a gold caption
f = blank_frame()
cv2.rectangle(f, (0, 0), (639, 479), bgra(BLUE), 32)
cv2.rectangle(f, (0, 420), (639, 479), bgra(BLUE), -1)
cv2.rectangle(f, (16, 16), (623, 420), bgra(GOLD), 3)
text_at(f, 'CSN PHOTO BOOTH', 320, 450, 1.2, bgra(GOLD), 2)
save(f, 'frames', '1_classic.png')

# 2: thick gold border, team cheer
f = blank_frame()
cv2.rectangle(f, (0, 0), (639, 479), bgra(GOLD), 48)
cv2.rectangle(f, (0, 400), (639, 479), bgra(GOLD), -1)
cv2.rectangle(f, (24, 24), (615, 400), bgra(BLUE), 4)
text_at(f, 'GO COYOTES!', 320, 440, 1.4, bgra(BLUE), 3)
save(f, 'frames', '2_go_coyotes.png')

# 3: instant-photo style, wide bottom edge with a handwritten caption
f = blank_frame()
f[:22], f[:, :22], f[:, -22:], f[-100:] = bgra(OFF_WHITE), bgra(OFF_WHITE), bgra(OFF_WHITE), bgra(OFF_WHITE)
cv2.rectangle(f, (22, 22), (617, 379), bgra((200, 200, 200)), 1)
text_at(f, 'CSN Memories', 320, 428, 1.6, bgra(CHARCOAL), 2, cv2.FONT_HERSHEY_SCRIPT_SIMPLEX)
save(f, 'frames', '3_polaroid.png')

# 4: film strip with sprocket holes and edge markings
f = blank_frame()
f[:, :56], f[:, -56:] = bgra((20, 20, 20)), bgra((20, 20, 20))
f[:26], f[-26:] = bgra((20, 20, 20)), bgra((20, 20, 20))
for y in range(40, 460, 44):
    for x in (16, 600):
        cv2.rectangle(f, (x, y), (x + 24, y + 26), bgra(OFF_WHITE), -1)
cv2.putText(f, 'CSN 400      24      24A      25      25A', (80, 18), FONT, 0.45, bgra(GOLD), 1, cv2.LINE_AA)
cv2.putText(f, 'COLLEGE OF SOUTHERN NEVADA', (80, 472), FONT, 0.45, bgra(GOLD), 1, cv2.LINE_AA)
save(f, 'frames', '4_film_strip.png')

# 5: stripes in every brand colour, with a round CSN badge
f = blank_frame()
for i, color in enumerate([NAVY, BLUE, LIGHT_BLUE, GREEN, GOLD, PURPLE]):
    cv2.rectangle(f, (i * 7 + 3, i * 7 + 3), (636 - i * 7, 476 - i * 7), bgra(color), 7)
cv2.circle(f, (572, 410), 44, bgra(NAVY), -1, cv2.LINE_AA)
cv2.circle(f, (572, 410), 44, bgra(GOLD), 4, cv2.LINE_AA)
text_at(f, 'CSN', 572, 410, 1.0, bgra(GOLD), 2)
save(f, 'frames', '5_brand_stripes.png')

# 6: minimal gold corners and a see-through caption bar
f = blank_frame()
for (x, y, dx, dy) in [(20, 20, 1, 1), (619, 20, -1, 1), (20, 459, 1, -1), (619, 459, -1, -1)]:
    cv2.line(f, (x, y), (x + 70 * dx, y), bgra(GOLD), 8, cv2.LINE_AA)
    cv2.line(f, (x, y), (x, y + 70 * dy), bgra(GOLD), 8, cv2.LINE_AA)
f[400:440, 120:520] = bgra(NAVY, 170)
text_at(f, 'College of Southern Nevada', 320, 420, 0.8, bgra(WHITE), 1)
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
cv2.fillPoly(s, [pts], bgra(BLUE), cv2.LINE_AA)
stripes, inside = np.zeros((300, 300), np.uint8), np.zeros((300, 300), np.uint8)
for y in range(60, 280, 45):
    cv2.line(stripes, (0, y + 40), (300, y - 40), 255, 12)
cv2.fillPoly(inside, [pts], 255)
s[(stripes > 0) & (inside > 0)] = bgra(GOLD)
cv2.ellipse(s, (150, 270), (95, 14), 0, 0, 360, bgra(GOLD), -1, cv2.LINE_AA)
cv2.circle(s, (150, 28), 20, bgra(WHITE), -1, cv2.LINE_AA)
save(s, 'stickers', 'party_hat.png')

# coyote ears (Cody grey with cream insides): ear bases near the bottom of the canvas
s = np.zeros((300, 300, 4), np.uint8)
for side in (1, -1):
    def mx(x):
        return x if side == 1 else 300 - x
    outer = np.array([[mx(35), 250], [mx(72), 35], [mx(145), 215]], np.int32)
    inner = np.array([[mx(60), 228], [mx(78), 85], [mx(124), 205]], np.int32)
    cv2.fillPoly(s, [outer], (125, 120, 118, 255), cv2.LINE_AA)
    cv2.polylines(s, [outer], True, (70, 65, 62, 255), 4, cv2.LINE_AA)
    cv2.fillPoly(s, [inner], (205, 228, 240, 255), cv2.LINE_AA)
save(s, 'stickers', 'coyote_ears.png')

# graduation cap in CSN blue with a gold tassel
s = np.zeros((300, 300, 4), np.uint8)
cv2.fillPoly(s, [np.array([[75, 130], [225, 130], [220, 215], [80, 215]], np.int32)], bgra(NAVY), cv2.LINE_AA)
cv2.ellipse(s, (150, 215), (70, 14), 0, 0, 180, bgra(NAVY), -1, cv2.LINE_AA)
board = np.array([[150, 70], [292, 120], [150, 170], [8, 120]], np.int32)
cv2.fillPoly(s, [board], bgra(BLUE), cv2.LINE_AA)
cv2.polylines(s, [board], True, bgra(NAVY), 3, cv2.LINE_AA)
cv2.line(s, (150, 120), (262, 138), bgra(GOLD), 4, cv2.LINE_AA)
cv2.line(s, (262, 138), (262, 205), bgra(GOLD), 4, cv2.LINE_AA)
cv2.rectangle(s, (254, 200), (270, 245), bgra(GOLD), -1)
cv2.circle(s, (150, 120), 8, bgra(GOLD), -1, cv2.LINE_AA)
save(s, 'stickers', 'grad_cap.png')

# gold crown with jewels (300x200)
s = np.zeros((200, 300, 4), np.uint8)
crown = np.array([[30, 180], [30, 60], [90, 120], [150, 30], [210, 120], [270, 60], [270, 180]], np.int32)
cv2.fillPoly(s, [crown], bgra(GOLD), cv2.LINE_AA)
cv2.polylines(s, [crown], True, bgra((0, 150, 210)), 4, cv2.LINE_AA)
cv2.rectangle(s, (30, 150), (270, 182), bgra((0, 170, 230)), -1)
for x, color in [(90, GREEN), (150, BLUE), (210, PURPLE)]:
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

# star-shaped glasses, gold with blue rims
s = np.zeros((300, 300, 4), np.uint8)
for cx in (92, 208):
    star = star_points(cx, 150, 62)
    cv2.fillPoly(s, [star], bgra(GOLD, 225), cv2.LINE_AA)
    cv2.polylines(s, [star], True, bgra(BLUE), 6, cv2.LINE_AA)
cv2.line(s, (140, 145), (160, 145), bgra(BLUE), 7, cv2.LINE_AA)
save(s, 'stickers', 'star_glasses.png')


# ---------------------------------------------------------------- backgrounds (1280x720)
H, W = 720, 1280

# celebration: brand-colour confetti on navy
bg = gradient(H, W, [(0, NAVY), (1, BLUE)])
for _ in range(450):
    x, y = rng.integers(0, W), rng.integers(0, H)
    color = [GOLD, LIGHT_BLUE, GREEN, WHITE, PURPLE][rng.integers(0, 5)]
    box = cv2.boxPoints(((float(x), float(y)), (14.0, 7.0), float(rng.integers(0, 180))))
    cv2.fillPoly(bg, [box.astype(np.int32)], color, cv2.LINE_AA)
text_at(bg, 'CONGRATS!', W // 2, 150, 3.5, GOLD, 9)
save(bg, 'backgrounds', 'celebration.jpg')

# basketball court: blue wall with the team name, wood floor with court lines
bg = gradient(H, W, [(0, NAVY), (0.6, BLUE)])
text_at(bg, 'CSN COYOTES', W // 2, 140, 3.0, GOLD, 8)
bg[400:430] = GOLD
floor = gradient(H - 430, W, [(0, (60, 120, 180)), (1, (90, 160, 215))])
for x in range(-1600, 2900, 70):     # planks that meet far away, for depth
    cv2.line(floor, (640 + (x - 640) // 4, 0), (x, H - 430), (55, 105, 160), 2, cv2.LINE_AA)
bg[430:] = floor
cv2.ellipse(bg, (640, 720), (560, 200), 0, 180, 360, WHITE, 6, cv2.LINE_AA)
save(bg, 'backgrounds', 'court.jpg')

# desert sunset: purple-to-orange sky, big sun, red rock ridges
bg = gradient(H, W, [(0, PURPLE), (0.45, (150, 80, 230)), (0.75, (40, 140, 255))])
cv2.circle(bg, (640, 470), 170, (80, 210, 255), -1, cv2.LINE_AA)
for y in range(430, 640, 22):        # sliced sun lines
    cv2.line(bg, (400, y), (880, y), (60, 130, 245), 5)
ridge(bg, 520, 140, (70, 75, 185))
ridge(bg, 590, 110, (50, 50, 130))
ridge(bg, 660, 80, (40, 30, 70))
save(bg, 'backgrounds', 'desert_sunset.jpg')

# go CSN: navy-to-blue with gold text and stage lights
t = np.linspace(0, 1, W)[None, :, None]
bg = (np.array(NAVY) * (1 - t) + np.array(BLUE) * t)
bg = np.repeat(bg, H, axis=0).astype(np.float32)
for cx in (250, 640, 1030):
    light = np.zeros((H, W), np.float32)
    cv2.ellipse(light, (cx, 600), (200, 70), 0, 0, 360, 1.0, -1)
    light = cv2.GaussianBlur(light, (0, 0), 40)[..., None]
    bg = bg * (1 - 0.6 * light) + 255 * 0.6 * light
bg = np.clip(bg, 0, 255).astype(np.uint8)
text_at(bg, 'GO CSN!', W // 2, 170, 3.0, GOLD, 6)
save(bg, 'backgrounds', 'go_csn.jpg')

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
bg = gradient(H, W, [(0, (40, 15, 10)), (0.45, PURPLE), (0.8, (150, 40, 200))])
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


# ---------------------------------------------------------------- Cody: cut out of his photo
# the selfie (person) segmenter also works on the costume, which is person-shaped
photo = cv2.imread(str(MASCOT_PHOTO))
if photo is None:
    print('Mascot photo not found, skipping mascot.png:', MASCOT_PHOTO)
else:
    segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=str(SEGMENTER_MODEL)), output_confidence_masks=True))
    rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(photo, cv2.COLOR_BGR2RGB))
    person = np.squeeze(segmenter.segment(rgb).confidence_masks[0].numpy_view())
    alpha = (np.clip((person - 0.3) / 0.4, 0, 1) * 255).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 0).astype(np.uint8))
    alpha[labels != 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])] = 0   # keep only the largest shape
    mascot = cv2.cvtColor(photo, cv2.COLOR_BGR2BGRA)
    mascot[..., 3] = alpha
    x, y, w, h = cv2.boundingRect((alpha > 0).astype(np.uint8))
    save(mascot[y:y + h, x:x + w], 'mascot.png')
    segmenter.close()

print('Placeholder art written to', ASSETS_DIR)
