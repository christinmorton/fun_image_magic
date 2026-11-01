#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import ctypes
import sys
import time
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision

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

#dummy function that does nothing
def dummy(value):
    pass


# define convolution kernels
identity_kernel = np.array([[0,0,0], [0,1,0], [0,0,0]])
sharpen_kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
gaussian_kernel1 = cv2.getGaussianKernel(3, 0)
gaussian_kernel2 = cv2.getGaussianKernel(5, 0)
box_kernel = np.array([[1,1,1], [1,1,1], [1,1,1]], np.float32) / 9.0
# (1 + 2 + 3 + 4 + 5) / 5 = 1 * 1/5 + 2 * 1/5 + 3 * 1/5 + 4 * 1/5 + 5 * 1/5
emboss_kernel = np.array([[-2,-1,0], [-1,1,1], [0,1,2]])
edge_kernel = np.array([[-1,-1,-1], [-1,8,-1], [-1,-1,-1]])

kernels = [identity_kernel, sharpen_kernel, gaussian_kernel1, gaussian_kernel2, box_kernel, emboss_kernel, edge_kernel]


# school colours in BGR order (placeholder: CSN blue #004990 and gold #FFCF01)
SCHOOL_DARK = (144, 73, 0)
SCHOOL_LIGHT = (1, 207, 255)

# sepia colour matrix, written for OpenCV's BGR channel order
SEPIA = np.array([[0.131, 0.534, 0.272],
                  [0.168, 0.686, 0.349],
                  [0.189, 0.769, 0.393]])


# preset effects: each one takes an image and returns a new one
def sepia(img):
    return cv2.transform(img, SEPIA)

def vignette(img, strength=1.5):
    # darkens the edges, using two 1D Gaussians multiplied into a 2D mask
    h, w = img.shape[:2]
    mask = cv2.getGaussianKernel(h, h / strength) @ cv2.getGaussianKernel(w, w / strength).T
    mask = mask / mask.max()
    return (img * mask[..., None]).astype(np.uint8)

def sketch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(255 - gray, (21, 21), 0)
    out = cv2.divide(gray, 255 - blur, scale=256)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)

def cartoon(img):
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 7)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
    color = cv2.bilateralFilter(img, 9, 250, 250)   # smooths colours, keeps edges
    return cv2.bitwise_and(color, color, mask=edges)

def pop_art(img):
    # four tinted copies, Warhol style, resized back to the original size
    h, w = img.shape[:2]
    small = cv2.resize(img, None, fx=0.5, fy=0.5)
    tints = [(1.0, 0.3, 0.3), (0.3, 1.0, 0.3), (0.3, 0.3, 1.0), (1.0, 1.0, 0.2)]  # BGR
    tiles = [(small * np.array(t)).astype(np.uint8) for t in tints]
    grid = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
    return cv2.resize(grid, (w, h))

def noir(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.addWeighted(gray, 1.6, gray, 0, -60)   # high contrast
    return vignette(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), 1.2)

def duotone(img, dark, light):
    # dark areas become the dark colour, light areas the light one
    t = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)[..., None] / 255.0
    return (np.array(dark) * (1 - t) + np.array(light) * t).astype(np.uint8)

def school_colors(img):
    return duotone(img, SCHOOL_DARK, SCHOOL_LIGHT)

def neon(img):
    # glowing edges on black, coloured by a rainbow colour map
    gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    edges = cv2.dilate(cv2.Canny(gray, 50, 150), np.ones((3, 3), np.uint8))
    glow = cv2.max(edges, cv2.GaussianBlur(edges, (15, 15), 0))
    colors = cv2.applyColorMap(gray, cv2.COLORMAP_HSV)
    return (colors * (glow[..., None] / 255.0)).astype(np.uint8)

def heat_vision(img):
    # like a thermal camera: bright areas hot (red), dark areas cold (blue)
    return cv2.applyColorMap(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLORMAP_JET)

def x_ray(img):
    gray = cv2.equalizeHist(255 - cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    return cv2.merge([gray, (gray * 0.85).astype(np.uint8), (gray * 0.6).astype(np.uint8)])   # blue-white

def pixel_art(img, block=12):
    # shrink, round each colour to 4 levels per channel, then blow up with hard edges
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(w // block, 1), max(h // block, 1)), interpolation=cv2.INTER_AREA)
    small = (small // 64) * 64 + 32
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

def comic_dots(img, cell=8):
    # halftone: a coloured dot per cell, bigger where the photo is darker
    h, w = img.shape[:2]
    small = cv2.resize(img, (w // cell, h // cell), interpolation=cv2.INTER_AREA)
    dark = 1 - cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) / 255.0
    out = np.full_like(img, 255)
    for y in range(small.shape[0]):
        for x in range(small.shape[1]):
            r = int(cell * (0.25 + 0.5 * dark[y, x]))
            color = tuple(int(c) for c in small[y, x])
            cv2.circle(out, (x * cell + cell // 2, y * cell + cell // 2), r, color, -1, cv2.LINE_AA)
    return out

def night_vision(img):
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    gray = cv2.add(gray, np.random.randint(0, 40, gray.shape, np.uint8))   # grainy noise
    out = cv2.merge([gray // 4, gray, gray // 4])                           # green
    out[::3] = (out[::3] * 0.6).astype(np.uint8)                            # scan lines
    return vignette(out, 1.0)

def vhs(img):
    # old camcorder tape: colour channels drift apart, scan lines, a REC light
    b, g, r = cv2.split(img)
    out = cv2.merge([np.roll(b, -6, axis=1), g, np.roll(r, 6, axis=1)])
    out = cv2.GaussianBlur(out, (3, 3), 0)
    out[::2] = (out[::2] * 0.75).astype(np.uint8)
    w = out.shape[1]
    cv2.circle(out, (w - 110, 62), 9, (0, 0, 255), -1, cv2.LINE_AA)
    cv2.putText(out, 'REC', (w - 95, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    return out

def watercolor(img):
    # OpenCV's painting effect is slow, so it runs on a half-size copy
    h, w = img.shape[:2]
    small = cv2.resize(img, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
    return cv2.resize(cv2.stylization(small, sigma_s=30, sigma_r=0.45), (w, h))

def mirror(img):
    # the left half reflected onto the right half
    w = img.shape[1]
    out = img.copy()
    out[:, w - w // 2:] = cv2.flip(img[:, :w // 2], 1)
    return out

def desert_sunset(img):
    return duotone(img, (138, 47, 49), (60, 160, 255))   # CSN purple #312F8A to sunset orange

PRESETS = [
    ('Original', lambda img: img),
    ('Vintage', lambda img: vignette(sepia(img))),
    ('Sketch', sketch),
    ('Cartoon', cartoon),
    ('Pop Art', pop_art),
    ('Noir', noir),
    ('School Colors', school_colors),
    ('Neon', neon),
    ('Heat Vision', heat_vision),
    ('X-Ray', x_ray),
    ('Pixel Art', pixel_art),
    ('Comic Dots', comic_dots),
    ('Night Vision', night_vision),
    ('VHS', vhs),
    ('Watercolor', watercolor),
    ('Mirror', mirror),
    ('Desert Sunset', desert_sunset),
]
# number keys pick the first ten presets (1-9, then 0); [ and ] step through all of them
PRESET_KEYS = '1234567890'


# overlays: transparent PNGs (BGRA) laid on top of the photo
def apply_overlay(img, overlay):
    overlay = cv2.resize(overlay, (img.shape[1], img.shape[0]))
    alpha = overlay[..., 3:] / 255.0        # 0 = transparent, 1 = solid
    return (overlay[..., :3] * alpha + img * (1 - alpha)).astype(np.uint8)

def paste_centered(img, sticker, cx, cy):
    # paste a BGRA sticker centred on (cx, cy), clipped at the image edges
    h, w = sticker.shape[:2]
    H, W = img.shape[:2]
    x, y = int(cx - w / 2), int(cy - h / 2)
    x0, y0 = max(x, 0), max(y, 0)
    x1, y1 = min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return img
    part = sticker[y0 - y:y1 - y, x0 - x:x1 - x]
    alpha = part[..., 3:] / 255.0
    img[y0:y1, x0:x1] = (part[..., :3] * alpha + img[y0:y1, x0:x1] * (1 - alpha)).astype(np.uint8)
    return img

def add_mascot(img, mascot):
    # mascot stands on the right side of the photo, 3/4 of its height
    H, W = img.shape[:2]
    mh = int(H * 0.75)
    mw = int(mascot.shape[1] * mh / mascot.shape[0])
    resized = cv2.resize(mascot, (mw, mh))
    return paste_centered(img, resized, W - mw / 2 - 10, H - mh / 2)

def add_face_sticker(img, faces, sticker, width_factor, lift_factor):
    # place a sticker on every face, sized and tilted from the outer eye corners
    H, W = img.shape[:2]
    for face in faces:
        lx, ly = face[33].x * W, face[33].y * H       # outer corner of one eye
        rx, ry = face[263].x * W, face[263].y * H     # outer corner of the other eye
        eye_dist = np.hypot(rx - lx, ry - ly)
        angle = np.degrees(np.arctan2(ry - ly, rx - lx))
        sw = int(eye_dist * width_factor)
        sh = int(sticker.shape[0] * sw / sticker.shape[1])
        if sw < 10:
            continue
        resized = cv2.resize(sticker, (sw, sh))
        M = cv2.getRotationMatrix2D((sw / 2, sh / 2), -angle, 1.0)
        rotated = cv2.warpAffine(resized, M, (sw, sh), borderValue=(0, 0, 0, 0))
        # move up from between the eyes, tilted along with the head
        a = np.radians(angle)
        cx = (lx + rx) / 2 + np.sin(a) * lift_factor * eye_dist
        cy = (ly + ry) / 2 - np.cos(a) * lift_factor * eye_dist
        paste_centered(img, rotated, cx, cy)
    return img

def swap_background(img, person_mask, background):
    bg = cv2.resize(background, (img.shape[1], img.shape[0]))
    m = person_mask.reshape(img.shape[0], img.shape[1], 1)   # 1 = person, 0 = background
    return (img * m + bg * (1 - m)).astype(np.uint8)


# load the art from the assets folder (anything missing is skipped)
mascot_png = cv2.imread(str(ASSETS_DIR / 'mascot.png'), cv2.IMREAD_UNCHANGED)
frames = [cv2.imread(str(p), cv2.IMREAD_UNCHANGED) for p in sorted((ASSETS_DIR / 'frames').glob('*.png'))]
backgrounds = [cv2.imread(str(p)) for p in sorted((ASSETS_DIR / 'backgrounds').glob('*.jpg'))]

# stickers: (file, width compared to the eye distance, how far above the eyes)
# a negative lift moves the sticker below the eyes
STICKERS = [
    ('sunglasses.png', 1.9, 0.0),
    ('star_glasses.png', 1.9, 0.0),
    ('party_hat.png', 1.7, 1.65),
    ('coyote_ears.png', 2.2, 1.65),
    ('crown.png', 1.6, 1.45),
    ('grad_cap.png', 1.9, 1.1),
    ('mustache.png', 1.1, -0.62),
]
stickers = []
for name, width_factor, lift_factor in STICKERS:
    png = cv2.imread(str(ASSETS_DIR / 'stickers' / name), cv2.IMREAD_UNCHANGED)
    if png is not None:
        stickers.append((png, width_factor, lift_factor))


# MediaPipe models: face landmarks (478 points per face) and a person mask
face_landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=str(MODELS_DIR / 'face_landmarker.task')),
    running_mode=vision.RunningMode.VIDEO, num_faces=4))
segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=str(MODELS_DIR / 'selfie_segmenter.tflite')),
    running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True))


# uploaded images: big photos are shrunk to fit on screen (never enlarged)
MAX_IMAGE_W, MAX_IMAGE_H = 960, 720

def choose_image_file():
    # opens the normal Windows "Open" dialog; returns '' if cancelled
    root = Tk()
    root.withdraw()                      # hide the empty Tk window behind the dialog
    root.attributes('-topmost', True)    # keep the dialog in front of the video
    path = filedialog.askopenfilename(title='Choose an image to edit', filetypes=[
        ('Images', '*.jpg *.jpeg *.png *.bmp *.webp'), ('All files', '*.*')])
    root.destroy()
    return path

def load_image(path):
    # np.fromfile + imdecode also works for paths with non-English characters
    try:
        img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    except OSError:
        return None
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = min(MAX_IMAGE_W / w, MAX_IMAGE_H / h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


# the picture source: an uploaded image (still_image) or the webcam (cap)
# start with an image if one is given (python app.py photo.jpg), otherwise the webcam
still_image = None
cap = None
if len(sys.argv) > 1:
    still_image = load_image(sys.argv[1])
    if still_image is None:
        raise SystemExit(f'Could not load image: {sys.argv[1]}')
else:
    cap = cv2.VideoCapture(0)    # 0 = the default webcam
    if not cap.isOpened():
        cap.release()
        cap = None
        print('No webcam found, choose an image instead')
        path = choose_image_file()
        still_image = load_image(path) if path else None
        if still_image is None:
            raise SystemExit('No webcam found and no image chosen')


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
frame_w = still_image.shape[1] if still_image is not None else int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
cv2.moveWindow('app', 10, 10)
cv2.moveWindow('controls', frame_w + 40, 10)

# arguments: TrackbarName, WindowName, value (initial value), count (max value), contrast, onChange event handler
cv2.createTrackbar('Contrast', 'controls', 1, 100, dummy)
cv2.createTrackbar('Brightness', 'controls', 50, 100, dummy)
cv2.createTrackbar('Filter', 'controls', 0, len(kernels) - 1, dummy)
cv2.createTrackbar('Greyscale', 'controls', 0, 1, dummy) # this becomes a switch because of 0 and 1. Boolean type

# feature sliders (the keyboard shortcuts move these same sliders)
cv2.createTrackbar('Preset', 'controls', 0, len(PRESETS) - 1, dummy)
cv2.createTrackbar('Sticker', 'controls', 0, len(stickers), dummy)         # 0 = off
cv2.createTrackbar('Background', 'controls', 0, len(backgrounds), dummy)   # 0 = off
cv2.createTrackbar('Cody', 'controls', 0, 1, dummy)
cv2.createTrackbar('Frame', 'controls', 1 if frames else 0, len(frames), dummy)   # 0 = off

print('Keys (click the video first): 1-9, 0 presets | [ ] prev/next preset | f face sticker | b background | m Cody | o frame')
print('      space photo strip | s save | u upload an image | w webcam | q quit')


timestamp_ms = 0           # MediaPipe video mode needs increasing timestamps

# photo strip state
SHOTS_PER_STRIP = 4
SECONDS_PER_SHOT = 3
shooting, shots, next_shot_at = False, [], 0
flash_until = 0


# Main UI loop
while True:
    if still_image is not None:
        # a fresh copy of the uploaded image every frame, so edits never build up
        color_original = still_image.copy()
    else:
        # read a frame from the webcam, mirrored like a selfie camera
        ok, color_original = cap.read()
        if not ok:
            break
        color_original = cv2.flip(color_original, 1)
    timestamp_ms += 33

    # read all of the trackbar values
    grayscale = cv2.getTrackbarPos('Greyscale', 'controls')
    contrast = cv2.getTrackbarPos('Contrast', 'controls')
    brightness = cv2.getTrackbarPos('Brightness', 'controls')
    kernel_idx = cv2.getTrackbarPos('Filter', 'controls')
    preset_idx = cv2.getTrackbarPos('Preset', 'controls')
    sticker_idx = cv2.getTrackbarPos('Sticker', 'controls') - 1          # -1 = off
    background_idx = cv2.getTrackbarPos('Background', 'controls') - 1    # -1 = off
    show_mascot = cv2.getTrackbarPos('Cody', 'controls') == 1
    frame_idx = cv2.getTrackbarPos('Frame', 'controls') - 1              # -1 = off

    # run MediaPipe on the raw camera frame, only when its feature is on
    if background_idx >= 0 or sticker_idx >= 0:
        rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(color_original, cv2.COLOR_BGR2RGB))
    if background_idx >= 0:
        person_mask = segmenter.segment_for_video(rgb, timestamp_ms).confidence_masks[0].numpy_view()
        color_original = swap_background(color_original, person_mask, backgrounds[background_idx])
    faces = []
    if sticker_idx >= 0:
        faces = face_landmarker.detect_for_video(rgb, timestamp_ms).face_landmarks

    gray_original = cv2.cvtColor(color_original, cv2.COLOR_BGR2GRAY)


    # apply the filters
    color_modified = cv2.filter2D(color_original, -1, kernels[kernel_idx])
    grey_modified = cv2.filter2D(gray_original, -1, kernels[kernel_idx])


    # apply the brightness and contrast
    color_modified = cv2.addWeighted(color_modified, contrast, np.zeros_like(color_original), 0, brightness - 50)
    grey_modified = cv2.addWeighted(grey_modified, contrast, np.zeros_like(gray_original), 0, brightness - 50)

    # pick colour or grey, then apply the preset, stickers, mascot and frame (in that order)
    if grayscale == 0:
        display = color_modified
    else:
        display = cv2.cvtColor(grey_modified, cv2.COLOR_GRAY2BGR)

    name, effect = PRESETS[preset_idx]
    display = effect(display)
    if sticker_idx >= 0:
        display = add_face_sticker(display, faces, *stickers[sticker_idx])
    if show_mascot and mascot_png is not None:
        display = add_mascot(display, mascot_png)
    if frame_idx >= 0:
        display = apply_overlay(display, frames[frame_idx])

    # wait for key press (1 millisecond, so the video stays smooth)
    key = cv2.waitKey(1)

    # if key equals 'q' would be ideal but instead I need integer
    if key == ord('q'):
        break
    elif key == ord('s'):
        # save image
        cv2.imwrite(str(OUTPUT_DIR / f'output-{datetime.now():%Y%m%d-%H%M%S}.png'), display)
    elif key == ord(' ') and not shooting:
        # start a photo strip
        shooting, shots, next_shot_at = True, [], time.time() + SECONDS_PER_SHOT
    elif key == ord('u'):
        # upload: pick an image file to edit instead of the webcam
        path = choose_image_file()
        image = load_image(path) if path else None
        if image is not None:
            still_image = image
            if cap is not None:
                cap.release()            # turn the webcam off while editing a photo
                cap = None
            cv2.moveWindow('controls', still_image.shape[1] + 40, 10)
        elif path:
            print('Could not open image:', path)
    elif key == ord('w') and cap is None:
        # back to the webcam (the uploaded image stays on screen if there is none)
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            still_image = None
            cv2.moveWindow('controls', int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) + 40, 10)
        else:
            cap.release()
            cap = None
            print('No webcam found')
    elif key == ord('f'):
        # cycle face stickers: off -> each sticker -> off
        cv2.setTrackbarPos('Sticker', 'controls', (sticker_idx + 2) % (len(stickers) + 1))
    elif key == ord('b'):
        # cycle backgrounds: off -> each background -> off
        cv2.setTrackbarPos('Background', 'controls', (background_idx + 2) % (len(backgrounds) + 1))
    elif key == ord('m'):
        cv2.setTrackbarPos('Cody', 'controls', 0 if show_mascot else 1)
    elif key == ord('o'):
        # cycle branded frames: each frame -> off -> first frame
        cv2.setTrackbarPos('Frame', 'controls', (frame_idx + 2) % (len(frames) + 1))
    elif key == ord('['):
        cv2.setTrackbarPos('Preset', 'controls', (preset_idx - 1) % len(PRESETS))
    elif key == ord(']'):
        cv2.setTrackbarPos('Preset', 'controls', (preset_idx + 1) % len(PRESETS))
    elif key != -1 and chr(key & 0xFF) in PRESET_KEYS:
        cv2.setTrackbarPos('Preset', 'controls', min(PRESET_KEYS.index(chr(key & 0xFF)), len(PRESETS) - 1))

    # anything drawn on `shown` is only on screen, never in saved photos
    shown = display.copy()
    cv2.putText(shown, name, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 6)        # dark outline
    cv2.putText(shown, name, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
    hint = 'SPACE photo strip   S save   U upload   W webcam   Q quit'
    cv2.putText(shown, hint, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
    cv2.putText(shown, hint, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

    # photo strip: count down, take a shot, repeat, then save the strip
    if shooting:
        now = time.time()
        if now >= next_shot_at:
            shots.append(cv2.copyMakeBorder(display, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
            next_shot_at = now + SECONDS_PER_SHOT
            flash_until = now + 0.15
            if len(shots) == SHOTS_PER_STRIP:
                strip = np.vstack(shots)
                cv2.imwrite(str(OUTPUT_DIR / f'strip-{datetime.now():%Y%m%d-%H%M%S}.png'), strip)
                cv2.imshow('strip', cv2.resize(strip, None, fx=700 / strip.shape[0], fy=700 / strip.shape[0]))
                shooting = False
        else:
            seconds_left = int(next_shot_at - now) + 1
            cv2.putText(shown, str(seconds_left), (shown.shape[1] // 2 - 30, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 0), 16)
            cv2.putText(shown, str(seconds_left), (shown.shape[1] // 2 - 30, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 8)
    if time.time() < flash_until:
        shown[:] = 255      # white flash when a shot is taken

    # Show the image
    cv2.imshow('app', shown)


# window cleanup
if cap is not None:
    cap.release()
face_landmarker.close()
segmenter.close()
cv2.destroyAllWindows()
