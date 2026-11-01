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
    mascots: list = field(default_factory=list)       # Cody poses, BGRA images trimmed to Cody
    frames: list = field(default_factory=list)        # BGRA images
    backgrounds: list = field(default_factory=list)   # BGR images
    stickers: list = field(default_factory=list)      # (BGRA image, width_factor, lift_factor)
    props: list = field(default_factory=list)         # scene props, BGRA images trimmed to the art
    prop_names: list = field(default_factory=list)    # a short name for each prop, for the screen


def trim_transparent(img):
    # crop away see-through padding, so sizing and placing go by the visible art
    # (pixels that are almost invisible, like faint specks left by a cut-out, don't count)
    x, y, w, h = cv2.boundingRect((img[..., 3] >= 16).astype('uint8'))
    return img[y:y + h, x:x + w] if w and h else img

def load_art(assets_dir):
    art = Art()
    art.mascots = [trim_transparent(cv2.imread(str(p), cv2.IMREAD_UNCHANGED))
                   for p in sorted((assets_dir / 'mascot').glob('*.png'))]
    art.frames = [cv2.imread(str(p), cv2.IMREAD_UNCHANGED) for p in sorted((assets_dir / 'frames').glob('*.png'))]
    art.backgrounds = [cv2.imread(str(p)) for p in sorted((assets_dir / 'backgrounds').glob('*.jpg'))]
    for name, width_factor, lift_factor in STICKERS:
        png = cv2.imread(str(assets_dir / 'stickers' / name), cv2.IMREAD_UNCHANGED)
        if png is not None:
            art.stickers.append((png, width_factor, lift_factor))
    # scene props: everything in assets/props/, then the Cody poses (so Cody can be placed
    # anywhere too); names drop the "1_" ordering prefix, e.g. "1_go_csn_sign" -> "go csn sign"
    for path in sorted((assets_dir / 'props').glob('*.png')):
        art.props.append(trim_transparent(cv2.imread(str(path), cv2.IMREAD_UNCHANGED)))
        art.prop_names.append(path.stem.split('_', 1)[-1].replace('_', ' '))
    for path, pose in zip(sorted((assets_dir / 'mascot').glob('*.png')), art.mascots):
        art.props.append(pose)
        art.prop_names.append('Cody ' + path.stem.split('_', 1)[-1].replace('_', ' '))
    return art
