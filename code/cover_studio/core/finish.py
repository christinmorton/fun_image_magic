# finish: making clean digital lettering (and later whole covers) look like it came off a
# late-90s CD booklet or a VHS tape, instead of a modern screen.
#   print: an early-Photoshop file saved as a small JPEG, printed and scanned: soft, with
#          compression blocks, colour fringes, faded warm blacks, grain and dust specks
#   vhs:   the same, plus colour smeared sideways, scan lines, a slight wobble and a band
#          of tracking noise
# Works on a BGR picture or a BGRA layer, at any size: every effect is measured against
# the picture, so a preview and a print file age the same way. A seed keeps it repeatable.
import cv2
import numpy as np

FINISHES = ['clean', 'print', 'vhs']


def shift_x(channel, dx):
    # one channel slid sideways by dx pixels (the edge colour fills the gap)
    h, w = channel.shape
    return cv2.warpAffine(channel, np.float32([[1, 0, dx], [0, 1, 0]]), (w, h), borderMode=cv2.BORDER_REPLICATE)

def fill_clear(bgr, alpha):
    # the colours bled out into the see-through parts of a layer, so blurs and the JPEG
    # don't pull a dark halo in from the empty (black) pixels around the letters
    sigma = max(bgr.shape[:2]) / 100
    weight = cv2.GaussianBlur(alpha, (0, 0), sigma)[..., None]
    spread = cv2.GaussianBlur(bgr * alpha[..., None], (0, 0), sigma) / np.maximum(weight, 1e-3)
    return bgr * alpha[..., None] + spread * (1 - alpha[..., None])

def low_quality(bgr, scale, quality):
    # the picture as a smaller, low-quality JPEG, blown back up: soft, with faint blocks
    h, w = bgr.shape[:2]
    small = np.clip(bgr, 0, 255).astype(np.uint8)
    if scale < 1:
        small = cv2.resize(small, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    ok, data = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    return cv2.resize(cv2.imdecode(data, cv2.IMREAD_COLOR), (w, h), interpolation=cv2.INTER_CUBIC).astype(np.float32)

def age(img, finish='print', strength=1.0, seed=0):
    # img aged with one of FINISHES; strength 0 (none) to about 2 (heavy), 1 = the usual
    if finish not in FINISHES:
        raise ValueError(f'unknown finish "{finish}"; use one of {FINISHES}')
    if finish == 'clean' or strength <= 0:
        return img.copy()
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    unit = max(h, w) / 1000.0                   # 1 for a 1000 px picture
    vhs = finish == 'vhs'
    layer = img.shape[2] == 4
    bgr = img[..., :3].astype(np.float32)
    alpha = img[..., 3].astype(np.float32) / 255.0 if layer else None
    if layer:
        bgr = fill_clear(bgr, alpha)

    # early digital: a smaller, low-quality JPEG, blown back up
    bgr = low_quality(bgr, 1 / (1 + (1.6 if vhs else 0.8) * strength), np.clip(80 - 35 * strength, 20, 95))

    if vhs:
        # tape smears the colour sideways and lets it lag behind the brightness
        ycc = cv2.cvtColor(np.clip(bgr, 0, 255).astype(np.uint8), cv2.COLOR_BGR2YCrCb).astype(np.float32)
        width = max(3, int(9 * unit * strength) | 1)
        for c in (1, 2):
            ycc[..., c] = shift_x(cv2.blur(ycc[..., c], (width, 1)), 3 * unit * strength)
        bgr = cv2.cvtColor(np.clip(ycc, 0, 255).astype(np.uint8), cv2.COLOR_YCrCb2BGR).astype(np.float32)

    # colour fringes: the red and blue layers drift apart a little, like a loose print
    drift = (2.0 if vhs else 1.2) * unit * strength
    b, g, r = cv2.split(bgr)
    bgr = cv2.merge([shift_x(b, -drift), g, shift_x(r, drift)])

    # faded blacks and softer whites, warmer in the shadows, like old ink on paper
    lift = np.array([16, 20, 28], np.float32) * strength
    dim = (lift + np.array([10, 4, 0], np.float32) * strength) / 255
    bgr = lift + bgr * (1 - dim)

    # grain, about 1.4 px across at 1000 px
    step = max(1.0, 1.4 * unit)
    grain = rng.normal(0, 1, (max(1, int(h / step)), max(1, int(w / step)))).astype(np.float32)
    bgr += cv2.resize(grain, (w, h), interpolation=cv2.INTER_LINEAR)[..., None] * (7 * strength)

    if vhs:
        # scan lines, a slow sideways wobble, and a band of tracking noise near the bottom
        band = max(1, int(round(unit)))
        bgr[(np.arange(h) // band) % 2 == 1] *= 0.84
        wobble = np.sin(np.arange(h) / h * 2 * np.pi * 3 + rng.uniform(0, 2 * np.pi)) * 1.2 * unit * strength
        top, tall = int(h * rng.uniform(0.78, 0.9)), max(2, int(h * 0.02))
        wobble[top:top + tall] += rng.normal(0, 6 * unit * strength, len(wobble[top:top + tall]))
        map_x = (np.arange(w, dtype=np.float32)[None, :] - wobble[:, None]).astype(np.float32)
        map_y = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, axis=1)
        bgr = cv2.remap(bgr, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if layer:
            alpha = cv2.remap(alpha, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
        streaks = np.clip(rng.normal(0, 45, (len(bgr[top:top + tall]), w)), 0, None) * strength
        bgr[top:top + tall] += cv2.blur(streaks.astype(np.float32), (max(3, int(15 * unit)), 1))[..., None]

    # dust and specks, as on a scanned print
    for _ in range(int(25 * strength * h * w / 1e6)):
        x, y = int(rng.integers(w)), int(rng.integers(h))
        colour = (235, 235, 230) if rng.random() < 0.6 else (25, 22, 20)
        cv2.circle(bgr, (x, y), max(1, int(unit * rng.uniform(0.4, 1.4))), colour, -1, cv2.LINE_AA)

    bgr = np.clip(bgr, 0, 255)
    if not layer:
        return bgr.astype(np.uint8)
    alpha = cv2.GaussianBlur(alpha, (0, 0), max(0.5, 0.6 * unit * strength))     # edges soften too
    return np.dstack([bgr, np.clip(alpha * 255, 0, 255)]).astype(np.uint8)
