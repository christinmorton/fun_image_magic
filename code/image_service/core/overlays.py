# overlays: things laid over or behind the photo - branded frames, face stickers,
# the mascot, and the background swap. Frames, stickers and the mascot are BGRA images
# (the 4th channel is transparency).
import cv2
import numpy as np


_fitted_frames = {}   # (frame, width, height) -> fitted frame, so each size is only worked out once
MAX_FITTED_FRAMES = 32  # the oldest are forgotten beyond this, so many photo sizes can't fill the memory

def fit_frame(frame, w, h):
    # resize a frame to w x h without squashing its corners, captions or badges:
    # scale it evenly until it fits the tighter direction, then lengthen the other
    # direction by repeating only plain rows/columns (ones that match their neighbour)
    key = (id(frame), w, h)
    if key not in _fitted_frames:
        while len(_fitted_frames) >= MAX_FITTED_FRAMES:
            _fitted_frames.pop(next(iter(_fitted_frames)))       # forget the oldest
        fh, fw = frame.shape[:2]
        scale = min(w / fw, h / fh)
        fitted = cv2.resize(frame, (max(round(fw * scale), 1), max(round(fh * scale), 1)), interpolation=cv2.INTER_AREA)
        fitted = _lengthen(fitted, w, axis=1)
        fitted = _lengthen(fitted, h, axis=0)
        _fitted_frames[key] = fitted
    return _fitted_frames[key]

def _lengthen(img, length, axis):
    # make img `length` long along axis (1 = width, 0 = height) by repeating plain lines
    n = img.shape[axis]
    if n == length:
        return img
    lines = img.astype(np.int16)
    if axis == 1:
        change = np.abs(lines[:, 1:] - lines[:, :-1]).max(axis=(0, 2))
    else:
        change = np.abs(lines[1:] - lines[:-1]).max(axis=(1, 2))
    same = change <= 2                           # line i looks the same as line i + 1
    # only repeat lines inside long plain stretches (plain border, see-through middle);
    # short ones are the flat tops of round badges or gaps between letters, and
    # repeating those would visibly stretch them
    min_run = max(3, round(n * 0.06))
    plain, start = [], None
    for i, is_same in enumerate(np.append(same, False)):
        if is_same and start is None:
            start = i
        elif not is_same and start is not None:
            if i - start >= min_run:
                plain.extend(range(start, i))
            start = None
    plain = np.array(plain, int)
    if n > length or len(plain) == 0:
        # nothing plain to repeat (or rounding made it 1 px too long): plain resize
        size = (length, img.shape[0]) if axis == 1 else (img.shape[1], length)
        return cv2.resize(img, size)
    # spread the extra lines evenly over the plain ones
    extra = length - n
    counts = np.ones(n, int)
    counts[plain] += extra // len(plain)
    leftover = extra % len(plain)
    counts[plain[(np.arange(leftover) * len(plain)) // leftover]] += 1
    return np.take(img, np.repeat(np.arange(n), counts), axis=axis)

def apply_overlay(img, overlay):
    # a full-size transparent PNG (a frame) laid on top of the photo
    overlay = fit_frame(overlay, img.shape[1], img.shape[0])
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
    # mascot stands in the bottom-right corner, flush with the edges (some poses are cut
    # off at the bottom or right, so a gap would show). Up to 3/4 of the photo's height and
    # 45% of its width, so wide half-body poses don't cover the people in the photo
    H, W = img.shape[:2]
    scale = min(H * 0.75 / mascot.shape[0], W * 0.45 / mascot.shape[1])
    mh, mw = int(mascot.shape[0] * scale), int(mascot.shape[1] * scale)
    resized = cv2.resize(mascot, (mw, mh), interpolation=cv2.INTER_AREA)
    return paste_centered(img, resized, W - mw / 2, H - mh / 2)

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
