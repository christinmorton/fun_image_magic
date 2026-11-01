# asset_library: loads the art in the assets/ folder (anything missing is skipped).
# Frames and backgrounds are loaded in file-name order, so new files appear automatically.
from dataclasses import dataclass, field

import cv2


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


@dataclass
class Art:
    mascot: object = None                             # BGRA image, or None if missing
    frames: list = field(default_factory=list)        # BGRA images
    backgrounds: list = field(default_factory=list)   # BGR images
    stickers: list = field(default_factory=list)      # (BGRA image, width_factor, lift_factor)


def load_art(assets_dir):
    art = Art()
    art.mascot = cv2.imread(str(assets_dir / 'mascot.png'), cv2.IMREAD_UNCHANGED)
    art.frames = [cv2.imread(str(p), cv2.IMREAD_UNCHANGED) for p in sorted((assets_dir / 'frames').glob('*.png'))]
    art.backgrounds = [cv2.imread(str(p)) for p in sorted((assets_dir / 'backgrounds').glob('*.jpg'))]
    for name, width_factor, lift_factor in STICKERS:
        png = cv2.imread(str(assets_dir / 'stickers' / name), cv2.IMREAD_UNCHANGED)
        if png is not None:
            art.stickers.append((png, width_factor, lift_factor))
    return art
