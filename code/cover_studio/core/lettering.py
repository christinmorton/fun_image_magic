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
PAD = 0.4           # empty space around drawn words, as a fraction of the font size (room for glows)


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
FIRE = [hex_bgr('#4fc3ff'), hex_bgr('#ff9a3c'), hex_bgr('#ff5fd2'), hex_bgr('#7dff8a')]   # rainbow flashes in cut stones


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

LIGHT_ANGLE = np.radians(-135)      # light from the top left (image y points down)

def cut_stone(bgr, cover, cx, cy, r, rng):
    # one brilliant-cut stone seen from above: an octagonal table (top face) ringed by eight
    # facets. Each facet is bright or dark depending on whether it faces the light, plus
    # some chance, which gives the hard black-and-white sparkle of real stones
    turn = rng.uniform(0, np.pi / 4)
    angles = turn + np.arange(9) * np.pi / 4
    girdle = np.stack([cx + r * np.cos(angles), cy + r * np.sin(angles)], axis=1)
    table = np.stack([cx + 0.5 * r * np.cos(angles), cy + 0.5 * r * np.sin(angles)], axis=1)
    to_int = lambda pts: np.round(pts * 16).astype(np.int32)          # 4 bits of sub-pixel precision
    tint = np.array(ICE_TINTS[rng.integers(len(ICE_TINTS))], np.float32)
    for k in range(8):
        facing = np.cos(turn + (k + 0.5) * np.pi / 4 - LIGHT_ANGLE)
        bright = float(np.clip(0.68 + 0.42 * facing + rng.normal(0, 0.25), 0.05, 1.0)) ** 1.15
        colour = tint * bright
        if rng.random() < 0.025:                                       # a rare flash of rainbow "fire"
            colour = (np.array(FIRE[rng.integers(len(FIRE))], np.float32) * 0.55 + tint * 0.45) * max(bright, 0.75)
        facet = np.array([table[k], table[k + 1], girdle[k + 1], girdle[k]])
        cv2.fillPoly(bgr, [to_int(facet)], colour.tolist(), cv2.LINE_AA, shift=4)
    cv2.fillPoly(bgr, [to_int(table[:8])], (tint * rng.uniform(0.55, 0.98)).tolist(), cv2.LINE_AA, shift=4)
    cv2.polylines(bgr, [to_int(girdle[:8])], True, (38, 36, 36), max(1, int(r * 0.07)), cv2.LINE_AA, shift=4)
    cv2.fillPoly(cover, [to_int(girdle[:8])], 1.0, cv2.LINE_AA, shift=4)

def gems(mask, size, rng):
    # cut stones packed into the letters like pavé jewellery, big ones with small ones in
    # the gaps between them: (colours, coverage, a few stone centres for glints)
    h, w = mask.shape
    gap = max(6.0, size * 0.105)
    r = gap * 0.5
    bgr, cover = np.zeros((h, w, 3), np.float32), np.zeros((h, w), np.float32)
    glints = []
    for row, y in enumerate(np.arange(gap / 2, h, gap * 0.866)):
        for x in np.arange(gap / 2 + (gap / 2 if row % 2 else 0), w, gap):
            if mask[int(y), int(x)] < 0.5:
                continue
            cut_stone(bgr, cover, x, y, r * rng.uniform(0.9, 1.0), rng)
            if rng.random() < 0.07:
                glints.append((x, y))
            # a small stone in the gap below and to the right of each big one
            sx, sy = x + gap / 2, y + gap * 0.289
            if 0 <= int(sy) < h and 0 <= int(sx) < w and mask[int(sy), int(sx)] > 0.5:
                cut_stone(bgr, cover, sx, sy, r * 0.27, rng)
    return bgr, cover, glints

def bloom(bgr, size):
    # the brightest spots glow a little into their surroundings, like light on a lens
    bright = np.clip((bgr.max(axis=2) - 215) / 40, 0, 1)
    halo = soften(bright, max(1.0, size * 0.025))
    return bgr + (255 - bgr) * (halo[..., None] * 0.55)


# --- the treatments ------------------------------------------------------------------
# each takes the words, the font size in pixels and a seed, and returns a BGRA image

def gold(text, size, seed=0):
    # thick gold letters with a bevel, a black outline and a yellow glow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'slab', size, int(size * PAD))
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
    mask = text_mask(text, 'slab', size, int(size * PAD))
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
    mask = text_mask(text, 'slab', size, int(size * PAD))
    edge = max(2, size * 0.045)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(grow(mask, edge), size * 0.04, size * 0.05), size * 0.03) * 0.6)
    bgr, alpha = over(bgr, alpha, WHITE, glow(mask, edge * 1.5, size * 0.1, 0.9))
    bgr, alpha = over(bgr, alpha, BLACK, grow(mask, edge))
    setting = shade(vertical_gradient(mask, SILVER), bevel(mask, size * 0.06), 0.5, 0.6) * 0.7
    stones, cover, glints = gems(mask, size, rng)
    fill = setting * (1 - cover[..., None]) + stones * cover[..., None]
    fill = shade(fill, bevel(mask, size * 0.05), 0.35, 0.25)        # the letters' edges still catch the light
    bgr, alpha = over(bgr, alpha, bloom(fill, size), mask)
    stars = np.zeros(mask.shape, np.float32)
    for x, y in glints:                                              # small glints on a few stones
        reach = size * rng.uniform(0.06, 0.12)
        cv2.line(stars, (int(x - reach), int(y)), (int(x + reach), int(y)), 1.0, 1, cv2.LINE_AA)
        cv2.line(stars, (int(x), int(y - reach)), (int(x), int(y + reach)), 1.0, 1, cv2.LINE_AA)
    bgr, alpha = over(bgr, alpha, WHITE, np.clip(np.maximum(stars, soften(stars, size * 0.01) * 2), 0, 1))
    bgr, alpha = sparkles(bgr, alpha, mask, max(4, len(text)), size, rng)
    return finish(bgr, alpha)

def scorched(text, size, seed=0):
    # red-hot stencil letters with black burn marks and a yellow-orange glow
    rng = np.random.default_rng(seed)
    mask = text_mask(text, 'stencil', size, int(size * PAD))
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
    mask = text_mask(text, 'block', size, int(size * PAD))
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
    mask = text_mask(text, 'brush', size, int(size * PAD))
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(mask, size * 0.03, size * 0.04), size * 0.04) * 0.75)
    dry = noise(mask.shape, size * 0.03, rng)
    fill = np.array(WHITE, np.float32) * (0.86 + 0.14 * dry[..., None])
    bgr, alpha = over(bgr, alpha, fill, mask)
    return finish(bgr, alpha)


def serif(text, size, seed=0):
    # plain heavy white serif capitals with a soft shadow, for quieter titles
    mask = text_mask(text, 'serif', size, int(size * PAD))
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(mask, size * 0.03, size * 0.04), size * 0.04) * 0.8)
    bgr, alpha = over(bgr, alpha, hex_bgr('#f4f1ea'), mask)
    return finish(bgr, alpha)


TREATMENTS = {'ice': ice, 'gold': gold, 'chrome': chrome, 'scorched': scorched, 'stone': stone,
              'brush': brush, 'serif': serif}
FONT_OF = {'ice': 'slab', 'gold': 'slab', 'chrome': 'slab', 'scorched': 'stencil', 'stone': 'block',
           'brush': 'brush', 'serif': 'serif'}

def draw_words(text, treatment, size, seed=0):
    # the words in one treatment, as a BGRA image: `size` px font, with PAD * size empty
    # pixels all round
    text = text.strip()
    if not text:
        raise ValueError('nothing to write: the text is empty')
    if treatment not in TREATMENTS:
        raise ValueError(f'unknown treatment "{treatment}"; use one of {list(TREATMENTS)}')
    return TREATMENTS[treatment](text, int(size), seed)


# --- supporting text: presents lines, featuring lists and the sticker -----------------

def paste(bgr, alpha, img, x, y):
    # lay a BGRA image over bgr/alpha with its top-left corner at (x, y), clipped at the edges
    h, w = alpha.shape
    ih, iw = img.shape[:2]
    x, y = int(round(x)), int(round(y))
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + iw, w), min(y + ih, h)
    if x0 < x1 and y0 < y1:
        part = img[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
        bgr[y0:y1, x0:x1], alpha[y0:y1, x0:x1] = over(bgr[y0:y1, x0:x1], alpha[y0:y1, x0:x1],
                                                      part[..., :3], part[..., 3] / 255.0)
    return bgr, alpha

def plain(text, font_name, size, colour=WHITE, outline=BLACK):
    # supporting text in one flat colour with a thin outline and a soft shadow, so it reads
    # on a busy picture; PAD * size empty pixels all round, like draw_words()
    mask = text_mask(text, font_name, int(size), int(size * PAD))
    edge = max(1, size * 0.06)
    bgr, alpha = blank(mask)
    bgr, alpha = over(bgr, alpha, BLACK, soften(shifted(grow(mask, edge), size * 0.04, size * 0.05), size * 0.05) * 0.7)
    bgr, alpha = over(bgr, alpha, outline, grow(mask, edge))
    bgr, alpha = over(bgr, alpha, colour, mask)
    return finish(bgr, alpha)

def wrap(names, font, width):
    # names joined with commas into lines no wider than `width` pixels (a name is never split)
    lines, line = [], ''
    for i, name in enumerate(names):
        piece = name + (',' if i < len(names) - 1 else '')
        trial = f'{line} {piece}' if line else piece
        if line and font.getlength(trial) > width:
            lines.append(line)
            trial = piece
        line = trial
    return lines + [line]

def even_lines(names, font, count, width):
    # the names split into `count` lines of about the same width (the split with the
    # smallest sum of squared line widths), each no wider than `width`; None if impossible
    pieces = [name + (',' if i < len(names) - 1 else '') for i, name in enumerate(names)]
    n, widths = len(pieces), {}
    def line_width(i, j):
        if (i, j) not in widths:
            widths[(i, j)] = font.getlength(' '.join(pieces[i:j]))
        return widths[(i, j)]
    best = [[float('inf')] * (n + 1) for _ in range(count + 1)]
    cut = [[0] * (n + 1) for _ in range(count + 1)]
    best[0][0] = 0.0
    for lines in range(1, count + 1):
        for j in range(1, n + 1):
            for i in range(lines - 1, j):
                w = line_width(i, j)
                if w <= width and best[lines - 1][i] + w * w < best[lines][j]:
                    best[lines][j], cut[lines][j] = best[lines - 1][i] + w * w, i
    if best[count][n] == float('inf'):
        return None
    out, j = [], n
    for lines in range(count, 0, -1):
        out.append(' '.join(pieces[cut[lines][j]:j]))
        j = cut[lines][j]
    return out[::-1]

LIST_COLOURS = (WHITE, hex_bgr('#ff3b2f'))      # featuring lines alternate white and red

def featuring_list(names, width, height, heading='Featuring:', colours=LIST_COLOURS):
    # a crowded, centred column of names in narrow capitals, filling a width x height box
    # (the text shrinks until everything fits), as a BGRA image of exactly that size
    names = [n.strip().upper() for n in names if n.strip()]
    if not names:
        raise ValueError('the featuring list is empty')
    for size in np.geomspace(max(height / 2.5, 8), 6, 60):
        font = load_font('narrow', int(size))
        lines = wrap(names, font, width * 0.94)
        head = size * 0.85 if heading else 0
        used = head * 1.25 + len(lines) * size * 1.18
        if used <= height * 0.96 and max(font.getlength(line) for line in lines) <= width * 0.94:
            break
    if len(lines) > 1:
        lines = even_lines(names, font, len(lines), width * 0.94) or lines
    size = int(size)
    bgr, alpha = np.zeros((height, width, 3), np.float32), np.zeros((height, width), np.float32)
    y = (height - used) / 2
    if heading:
        img = plain(heading, 'brush', head, GLOW_YELLOW)
        bgr, alpha = paste(bgr, alpha, img, (width - img.shape[1]) / 2, y - int(head * PAD))
        y += head * 1.25
    for i, line in enumerate(lines):
        img = plain(line, 'narrow', size, colours[i % len(colours)])
        bgr, alpha = paste(bgr, alpha, img, (width - img.shape[1]) / 2, y - int(size * PAD))
        y += size * 1.18
    return finish(bgr, alpha)

STICKER_STYLES = ['badge', 'stamp', 'hazard']

def rounded_box(height, width, radius):
    # a soft-edged rounded rectangle filling height x width (1 inside, 0 outside)
    box = np.zeros((height, width), np.uint8)
    cv2.rectangle(box, (radius, radius), (width - 1 - radius, height - 1 - radius), 255, -1)
    box = cv2.dilate(box, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1)))
    return soften(box.astype(np.float32) / 255.0, 0.7)

def shrink(mask, px):
    # the mask made `px` pixels thinner all round; beyond the canvas counts as empty, so a
    # shape that touches the edges still shrinks there
    px = max(1, int(round(px)))
    return cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1)),
                     borderType=cv2.BORDER_CONSTANT, borderValue=0)

def rotated(img, degrees):
    # a BGRA image turned by `degrees`, on a canvas big enough to keep the corners
    h, w = img.shape[:2]
    turn = cv2.getRotationMatrix2D((w / 2, h / 2), degrees, 1.0)
    cos, sin = abs(turn[0, 0]), abs(turn[0, 1])
    nw, nh = int(w * cos + h * sin) + 2, int(w * sin + h * cos) + 2
    turn[0, 2] += (nw - w) / 2
    turn[1, 2] += (nh - h) / 2
    return cv2.warpAffine(img, turn, (nw, nh), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))

def sticker(lines=('CERTIFIED', 'HOOD CLASSIC'), height=200, style='badge', seed=0):
    # our own advisory-style stickers, never the real Parental Advisory mark. The lines are
    # in narrow capitals, the last one biggest. Styles:
    #   badge:  a rounded black box with a gold border and white words
    #   stamp:  a red rubber stamp with a double border and worn ink, slightly tilted
    #   hazard: a yellow box with a black hazard-stripe border and black words
    lines = [line.strip().upper() for line in lines if line.strip()]
    if not lines:
        raise ValueError('the sticker has no words')
    if style not in STICKER_STYLES:
        raise ValueError(f'unknown sticker style "{style}"; use one of {STICKER_STYLES}')
    border = max(2, int(height * (0.12 if style == 'hazard' else 0.05)))
    margin = int(height * 0.13) + (border if style == 'hazard' else 0)
    sizes = [height * 0.2] * (len(lines) - 1) + [height * 0.36]
    scale = min(1.0, (height - 2 * margin) / (sum(sizes) * 1.12))     # many lines: shrink them all
    masks = [text_mask(line, 'narrow', max(6, int(s * scale)), 0) for line, s in zip(lines, sizes)]
    width = max(m.shape[1] for m in masks) + 2 * margin
    box = rounded_box(height, width, int(height * (0.06 if style == 'hazard' else 0.12)))
    words = np.zeros_like(box)
    y = (height - sum(m.shape[0] for m in masks) * 1.12) / 2
    for m in masks:
        x, top = int((width - m.shape[1]) / 2), int(round(y))
        words[top:top + m.shape[0], x:x + m.shape[1]] = np.maximum(words[top:top + m.shape[0], x:x + m.shape[1]], m)
        y += m.shape[0] * 1.12
    bgr, alpha = blank(box)
    if style == 'badge':
        bgr, alpha = over(bgr, alpha, hex_bgr('#e8b923'), box)               # gold border
        bgr, alpha = over(bgr, alpha, hex_bgr('#0b0b0b'), soften(shrink(box, border), 0.7))
        bgr, alpha = over(bgr, alpha, WHITE, words)
        return finish(bgr, alpha)
    if style == 'hazard':
        yy, xx = np.indices(box.shape)
        stripes = (((xx + yy) // max(3, int(height * 0.09))) % 2).astype(np.float32)
        inside = soften(shrink(box, border), 0.7)
        bgr, alpha = over(bgr, alpha, hex_bgr('#ffd400'), box)
        bgr, alpha = over(bgr, alpha, hex_bgr('#111111'), (box - inside) * stripes)
        bgr, alpha = over(bgr, alpha, hex_bgr('#111111'), np.clip(box - shrink(box, max(1, border * 0.15)), 0, 1))
        bgr, alpha = over(bgr, alpha, hex_bgr('#111111'), words)
        return finish(bgr, alpha)
    # stamp: two rings and the words in red ink, with patchy wear, then a slight tilt
    ring = np.clip(box - shrink(box, border), 0, 1)
    inner = shrink(box, border * 2.2)
    ring = np.maximum(ring, np.clip(inner - shrink(inner, max(1, border * 0.5)), 0, 1))
    ink = np.maximum(ring, words)
    wear = noise(box.shape, max(2, height * 0.04), np.random.default_rng(seed))
    ink = ink * smoothstep(0.18, 0.4, wear) * 0.92
    bgr, alpha = over(bgr, alpha, hex_bgr('#c8102e'), ink)
    return rotated(finish(bgr, alpha), 8)
