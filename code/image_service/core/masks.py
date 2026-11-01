# masks: cleaning up the person mask (1 = person, 0 = background) from MediaPipe, and
# the "Focus" effects that use it: color pop, portrait blur and a mask preview.
import cv2
import numpy as np


FOCUS_MODES = ['Off', 'Color Pop', 'Portrait Blur', 'Mask Preview']


def refine_mask(person_mask, img):
    # the raw mask has a wide, blotchy soft edge, which shows as a halo of the old
    # background. Make it firm where the model is fairly sure, remove stray specks and
    # pinholes, pull the edge in by a pixel (so the old background's edge colour doesn't
    # show), then soften it very slightly so it isn't jagged.
    # (A guided filter was tried and made the halo wider on plain backdrops.)
    h, w = img.shape[:2]
    mask = np.clip((person_mask.reshape(h, w).astype(np.float32) - 0.3) / 0.4, 0, 1)   # <0.3 -> 0, >0.7 -> 1
    size = max(3, (min(h, w) // 160) | 1)                                             # odd, grows with the photo
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)     # remove specks
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)    # fill pinholes
    mask = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    mask = cv2.GaussianBlur(mask, (0, 0), max(0.8, min(h, w) / 600))
    return np.clip(mask, 0, 1)

def blend(person, background, mask):
    # person where the mask is 1, background where it is 0, a soft mix along the edge
    m = mask[..., None]
    return (person * m + background * (1 - m)).astype(np.uint8)

def color_pop(img, mask):
    # the person stays in colour, the background turns grey
    gray = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return blend(img, gray, mask)

def portrait_blur(img, mask):
    # like a phone's portrait mode: the background is blurred, the person stays sharp
    blurred = cv2.GaussianBlur(img, (0, 0), max(img.shape[:2]) / 80)
    return blend(img, blurred, mask)

def mask_preview(img, mask):
    # shows what counts as the person: the background becomes a dark checkerboard,
    # like see-through areas in a photo editor (handy before AI background edits)
    h, w = img.shape[:2]
    square = max(8, min(h, w) // 24)
    yy, xx = np.indices((h, w))
    checker = np.where(((yy // square + xx // square) % 2)[..., None] == 0, 40, 70).astype(np.uint8)
    return blend(img, np.repeat(checker, 3, axis=2), mask)

def apply_focus(img, mode, mask):
    # mode is an index into FOCUS_MODES (0 = off)
    effects = [None, color_pop, portrait_blur, mask_preview]
    return effects[mode](img, mask) if mode else img
