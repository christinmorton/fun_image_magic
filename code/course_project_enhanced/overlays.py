# overlays: things laid over or behind the photo - branded frames, face stickers,
# Cody the mascot, and the background swap. Frames, stickers and Cody are BGRA images
# (the 4th channel is transparency).
import cv2
import numpy as np


def apply_overlay(img, overlay):
    # a full-size transparent PNG (a frame) laid on top of the photo
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
