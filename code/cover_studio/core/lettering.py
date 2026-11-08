# lettering: the words on a cover (names, titles, lists) drawn with real fonts and graphic
# effects, never by the AI. Each treatment turns words into a BGRA image (the 4th channel
# is transparency) to lay over the artwork. Effects are built in layers, the way a
# designer stacks layer styles: shadow, glow, outline, the filled letters with a bevel,
# then sparkles on top. Random touches (gems, burn marks, chips) come from a seed, so the
# same words always look the same.
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import ASSETS_DIR

FONTS_DIR = ASSETS_DIR / 'fonts'
FONTS = {                       # all licensed for commercial use (licences beside them)
    'slab': 'AlfaSlabOne-Regular.ttf',        # heavy slab letters: gold, chrome, ice
    'stencil': 'BlackOpsOne-Regular.ttf',     # military stencil: scorched metal
    'block': 'Bungee-Regular.ttf',            # blocky letters: stone
    'brush': 'PermanentMarker-Regular.ttf',   # rough brush script
    'narrow': 'Anton-Regular.ttf',            # narrow heavy sans: featuring lists
    'serif': 'AbrilFatface-Regular.ttf',      # heavy serif: presents lines, titles
}


def hex_bgr(code):
    # '#ffd84a' -> (74, 216, 255), OpenCV's blue-green-red order
    code = code.lstrip('#')
    return (int(code[4:6], 16), int(code[2:4], 16), int(code[0:2], 16))

BLACK = hex_bgr('#000000')
WHITE = hex_bgr('#ffffff')
GLOW_YELLOW = hex_bgr('#ffe14d')
GLOW_ORANGE = hex_bgr('#ffb020')

# metal fills: (fraction of the letter height from the top, colour)
GOLD = [(0.0, '#7a4a00'), (0.18, '#c98a00'), (0.38, '#ffd84a'), (0.47, '#fff6c2'),
        (0.55, '#f2b81c'), (0.8, '#a86a00'), (1.0, '#5e3600')]
# chrome reflects a horizon: bright sky, a dark band, a hard bright line, then brown ground
CHROME = [(0.0, '#ffffff'), (0.25, '#cfe3ff'), (0.48, '#5d7fb3'), (0.5, '#1b2338'),
          (0.53, '#f4f4f4'), (0.62, '#a57a52'), (0.82, '#5a3a22'), (1.0, '#e7d3b9')]
SILVER = [(0.0, '#e8eef5'), (0.5, '#8e98a6'), (1.0, '#d6dde6')]
SCORCH = [(0.0, '#ffb02e'), (0.35, '#ff5a1a'), (0.7, '#c81e14'), (1.0, '#6e0b08')]
CHAR = hex_bgr('#1a0905')        # burnt patches on scorched metal
STONE = hex_bgr('#a39a86')
ICE_TINTS = [hex_bgr('#f4faff'), hex_bgr('#e1f0ff'), hex_bgr('#eee8ff'), hex_bgr('#fffdf2')]   # gems: white, icy blue, violet, warm


# --- the words as a mask -------------------------------------------------------------

def load_font(name, size):
    return ImageFont.truetype(str(FONTS_DIR / FONTS[name]), size)

def text_mask(text, font_name, size, pad):
    # the words as a soft mask (1 = ink, 0 = empty), `size` px font, with `pad` empty
    # pixels all round so glows and shadows have room
    font = load_font(font_name, size)
    left, top, right, bottom = font.getbbox(text)
    img = Image.new('L', (right - left + 2 * pad, bottom - top + 2 * pad), 0)
    ImageDraw.Draw(img).text((pad - left, pad - top), text, font=font, fill=255)
    return np.asarray(img, np.float32) / 255.0


# --- building blocks -----------------------------------------------------------------

def grow(mask, px):
    # the mask made `px` pixels fatter all round (for outlines and glows)
    px = int(round(px))
    if px <= 0:
        return mask
    return cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)))

def soften(mask, sigma):
    return cv2.GaussianBlur(mask, (0, 0), max(sigma, 0.5))

def shifted(mask, dx, dy):
    h, w = mask.shape
    return cv2.warpAffine(mask, np.float32([[1, 0, dx], [0, 1, dy]]), (w, h))

def glow(mask, spread, blur, strength=1.0):
    # a soft halo around the letters
    return np.clip(soften(grow(mask, spread), blur) * strength, 0, 1)

def smoothstep(low, high, x):
    t = np.clip((x - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)

def noise(shape, scale, rng, octaves=3):
    # smooth random texture in 0..1, with blobs about `scale` pixels across
    total = np.zeros(shape, np.float32)
    for i in range(octaves):
        step = max(scale / 2 ** i, 1)
        small = rng.random((int(shape[0] / step) + 2, int(shape[1] / step) + 2)).astype(np.float32)
        total += cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC) / 2 ** i
    total -= total.min()
    return total / max(float(total.max()), 1e-6)

def vertical_gradient(mask, stops):
    # a colour fill that runs from the top of the letters (0) to their bottom (1)
    rows = np.where(mask.max(axis=1) > 0.5)[0]
    top, bottom = (rows[0], rows[-1]) if len(rows) else (0, mask.shape[0] - 1)
    t = np.clip((np.arange(mask.shape[0]) - top) / max(bottom - top, 1), 0, 1)
    positions = [p for p, _ in stops]
    colours = [hex_bgr(c) for _, c in stops]
    column = np.stack([np.interp(t, positions, [c[i] for c in colours]) for i in range(3)], axis=1)
    return np.repeat(column[:, None, :], mask.shape[1], axis=1).astype(np.float32)

def bevel(mask, width, light=(-1.0, -1.0, 1.2)):
    # how much each pixel faces the light, from -1 (away) through 0 (flat) to 1 (towards).
    # The letters are treated as a surface that rises from their edge to `width` pixels
    # inside, lit from the top left
    inside = (mask > 0.5).astype(np.uint8)
    height = np.clip(cv2.distanceTransform(inside, cv2.DIST_L2, 5) / max(width, 1), 0, 1)
    height = cv2.GaussianBlur(height, (0, 0), max(width / 6, 0.8))
    steep = max(width, 1) / 4
    nx = -cv2.Sobel(height, cv2.CV_32F, 1, 0, ksize=3) * steep
    ny = -cv2.Sobel(height, cv2.CV_32F, 0, 1, ksize=3) * steep
    lx, ly, lz = np.array(light) / np.linalg.norm(light)
    facing = (nx * lx + ny * ly + lz) / np.sqrt(nx * nx + ny * ny + 1)
    return np.where(facing >= lz, (facing - lz) / (1 - lz), (facing - lz) / (1 + lz))

def shade(colour, facing, dark=0.6, light=0.9):
    # darken what faces away from the light, brighten towards white what faces it
    f = facing[..., None]
    return np.where(f < 0, colour * (1 + dark * f), colour + (255 - colour) * light * f)

def over(bgr, alpha, colour, a):
    # paint `colour` (a BGR triple or an image) with opacity `a` on top of bgr/alpha
    a3 = a[..., None]
    out_a = a3 + alpha[..., None] * (1 - a3)
    out = (np.asarray(colour, np.float32) * a3 + bgr * alpha[..., None] * (1 - a3)) / np.maximum(out_a, 1e-6)
    return out, out_a[..., 0]

def blank(mask):
    return np.zeros(mask.shape + (3,), np.float32), np.zeros(mask.shape, np.float32)

def finish(bgr, alpha):
    return np.dstack([np.clip(bgr, 0, 255), np.clip(alpha * 255, 0, 255)]).astype(np.uint8)

def sparkles(bgr, alpha, mask, count, size, rng):
    # star-shaped glints on the letters' corners, like light catching polished metal
    corners = cv2.goodFeaturesToTrack((mask > 0.5).astype(np.uint8) * 255, count * 4, 0.1, size * 0.3)
    if corners is None or count <= 0:
        return bgr, alpha
    points = corners.reshape(-1, 2)
    rng.shuffle(points)
    stars = np.zeros(mask.shape, np.float32)
    for x, y in points[:count]:
        length = size * rng.uniform(0.18, 0.4)
        for dx, dy, part in [(1, 0, 1.0), (0, 1, 1.0), (0.7, 0.7, 0.4), (0.7, -0.7, 0.4)]:
            # each ray is a thin diamond, so it tapers to a point at both ends
            reach, half = length * part, length * part * 0.07
            ray = np.array([(x - dx * reach, y - dy * reach), (x - dy * half, y + dx * half),
                            (x + dx * reach, y + dy * reach), (x + dy * half, y - dx * half)])
            cv2.fillPoly(stars, [np.round(ray).astype(np.int32)], 1.0, cv2.LINE_AA)
        cv2.circle(stars, (int(x), int(y)), max(2, int(size * 0.035)), 1.0, -1, cv2.LINE_AA)
    stars = np.clip(np.maximum(stars, soften(stars, size * 0.025) * 1.6), 0, 1)
    return over(bgr, alpha, WHITE, stars)

def gems(mask, size, rng):
    # rows of small round diamonds packed inside the letters: (colours, coverage)
    h, w = mask.shape
    gap = max(5.0, size * 0.11)
    r = gap * 0.47
    bgr, cover = np.zeros((h, w, 3), np.float32), np.zeros((h, w), np.float32)
    point = lambda px, py: (int(round(px)), int(round(py)))
    for row, y in enumerate(np.arange(gap / 2, h, gap * 0.866)):
        for x in np.arange(gap / 2 + (gap / 2 if row % 2 else 0), w, gap):
            if mask[int(y), int(x)] < 0.5:
                continue
            tint = ICE_TINTS[rng.integers(len(ICE_TINTS))]
            bright = rng.uniform(0.82, 1.0)
            colour = tuple(c * bright for c in tint)
            # a darker stone, then a bright one nudged up-left over it: the dark crescent
            # left at the bottom right reads as a cut facet
            cv2.circle(bgr, point(x, y), int(r), tuple(c * 0.55 for c in colour), -1, cv2.LINE_AA)
            cv2.circle(bgr, point(x - r * 0.12, y - r * 0.12), int(r * 0.84), colour, -1, cv2.LINE_AA)
            cv2.circle(cover, point(x, y), int(r), 1.0, -1, cv2.LINE_AA)
            cv2.circle(bgr, point(x, y), int(r), (70, 66, 66), max(1, int(r * 0.12)), cv2.LINE_AA)  # setting
            cv2.circle(bgr, point(x - r * 0.32, y - r * 0.32), max(1, int(r * 0.26)), WHITE, -1, cv2.LINE_AA)
    return bgr, cover


# --- the treatments ------------------------------------------------------------------
# each takes the words, the font size in pixels and a seed, and returns a BGRA image

def gold(text, size, seed=0):
    # thick gold letters with a bevel, a black outline and a yellow glow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'slab', size, int(size * 0.4))
    edge = max(2, size * 0.05)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(grow(mask, edge), size * 0.04, size * 0.05), size * 0.03) * 0.7)
    bgr, alpha = over(bgr, alpha, GLOW_YELLOW, glow(mask, edge * 2, size * 0.1))
    bgr, alpha = over(bgr, alpha, BLACK, grow(mask, edge))
    fill = shade(vertical_gradient(mask, GOLD), bevel(mask, size * 0.09))
    bgr, alpha = over(bgr, alpha, fill, mask)
    bgr, alpha = sparkles(bgr, alpha, mask, max(3, len(text) // 2), size, rng)
    return finish(bgr, alpha)

def chrome(text, size, seed=0):
    # polished metal reflecting a horizon, with a strong bevel and a cool white glow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'slab', size, int(size * 0.4))
    edge = max(2, size * 0.045)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(grow(mask, edge), size * 0.04, size * 0.05), size * 0.03) * 0.7)
    bgr, alpha = over(bgr, alpha, WHITE, glow(mask, edge, size * 0.08, 0.6))
    bgr, alpha = over(bgr, alpha, hex_bgr('#10131c'), grow(mask, edge))
    fill = shade(vertical_gradient(mask, CHROME), bevel(mask, size * 0.1), 0.7, 0.95)
    bgr, alpha = over(bgr, alpha, fill, mask)
    bgr, alpha = sparkles(bgr, alpha, mask, max(3, len(text) // 2), size, rng)
    return finish(bgr, alpha)

def ice(text, size, seed=0):
    # letters packed with diamonds on a silver setting, with a white glow and many glints
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'slab', size, int(size * 0.4))
    edge = max(2, size * 0.045)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(grow(mask, edge), size * 0.04, size * 0.05), size * 0.03) * 0.6)
    bgr, alpha = over(bgr, alpha, WHITE, glow(mask, edge * 1.5, size * 0.1, 0.9))
    bgr, alpha = over(bgr, alpha, BLACK, grow(mask, edge))
    setting = shade(vertical_gradient(mask, SILVER), bevel(mask, size * 0.06), 0.5, 0.6)
    stones, cover = gems(mask, size, rng)
    fill = setting * (1 - cover[..., None]) + stones * cover[..., None]
    bgr, alpha = over(bgr, alpha, fill, mask)
    bgr, alpha = sparkles(bgr, alpha, mask, max(6, len(text) * 3 // 2), size, rng)
    return finish(bgr, alpha)

def scorched(text, size, seed=0):
    # red-hot stencil letters with black burn marks and a yellow-orange glow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'stencil', size, int(size * 0.4))
    edge = max(2, size * 0.035)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, GLOW_ORANGE, glow(mask, edge * 2, size * 0.14, 1.2))
    bgr, alpha = over(bgr, alpha, BLACK, grow(mask, edge))
    fill = vertical_gradient(mask, SCORCH)
    burnt = smoothstep(0.55, 0.78, noise(mask.shape, size * 0.25, rng))[..., None] * 0.85
    fill = fill * (1 - burnt) + np.array(CHAR, np.float32) * burnt
    fill = shade(fill, bevel(mask, size * 0.05), 0.5, 0.5)
    bgr, alpha = over(bgr, alpha, fill, mask)
    return finish(bgr, alpha)

def stone(text, size, seed=0):
    # rough, chiselled rock letters with chipped edges and a white glow behind
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'block', size, int(size * 0.4))
    near_edge = cv2.distanceTransform((mask > 0.5).astype(np.uint8), cv2.DIST_L2, 5) < size * 0.04
    chips = noise(mask.shape, size * 0.05, rng) < 0.35
    mask = soften(np.where(near_edge & chips, 0, mask).astype(np.float32), 0.7)
    edge = max(1, size * 0.02)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, WHITE, glow(mask, edge * 4, size * 0.12, 1.1))
    bgr, alpha = over(bgr, alpha, hex_bgr('#2a2622'), grow(mask, edge))
    grain = noise(mask.shape, size * 0.15, rng) * 0.6 + noise(mask.shape, size * 0.02, rng) * 0.4
    fill = np.array(STONE, np.float32) * (0.65 + 0.55 * grain[..., None])
    fill = shade(fill, bevel(mask, size * 0.1), 0.7, 0.6)
    bgr, alpha = over(bgr, alpha, fill, mask)
    return finish(bgr, alpha)

def brush(text, size, seed=0):
    # one word in rough white brush strokes with a soft dark shadow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'brush', size, int(size * 0.3))
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(mask, size * 0.03, size * 0.04), size * 0.04) * 0.75)
    dry = noise(mask.shape, size * 0.03, rng)
    fill = np.array(WHITE, np.float32) * (0.86 + 0.14 * dry[..., None])
    bgr, alpha = over(bgr, alpha, fill, mask)
    return finish(bgr, alpha)


TREATMENTS = {'ice': ice, 'gold': gold, 'chrome': chrome, 'scorched': scorched, 'stone': stone, 'brush': brush}

def draw_words(text, treatment, size, seed=0):
    # the words in one treatment, as a BGRA image `size` px tall per line of capitals or so
    text = text.strip()
    if not text:
        raise ValueError('nothing to write: the text is empty')
    if treatment not in TREATMENTS:
        raise ValueError(f'unknown treatment "{treatment}"; use one of {list(TREATMENTS)}')
    return TREATMENTS[treatment](text, int(size), seed)
