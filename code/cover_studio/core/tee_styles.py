# tee_styles: ways to print a cover on a shirt other than a hard-edged square, the way
# bootleg rap tees do it. 'faded' dissolves the cover's edges into the shirt in halftone
# dots, with a slightly ragged edge; 'knockout' leaves out the parts of the artwork close to
# the shirt's colour, so the shirt itself shows through. Both turn anything part-printed
# into halftone dots rather than see-through ink, since shirt printers print soft fades
# badly (speckled, or with a muddy halo from the white base layer on dark shirts).
# Experimental: see experiments/tee_styles_sheet.py.
import cv2
import numpy as np

STYLES = ('classic', 'faded', 'knockout', 'faded_knockout')

DOT_IN = 1 / 22             # the halftone grid (about 22 dots to the inch, a coarse screen print)
FADE = 0.13                 # how far in from the edge the fade reaches, as a fraction of the cover
RAGGED = 0.35               # how uneven the fade's inner edge is (0: an even band)
KNOCKOUT = (28, 80)         # colour distance from the shirt: left out below the first, printed above the second
KNOCKOUT_LIGHTNESS = (12, 50)   # on dark (light) shirts: how much lighter (darker) than the shirt a
                                # part must be to print (0-255 lightness), from left out to solid
DARK_SHIRT, LIGHT_SHIRT = 90, 175   # the shirt's lightness (0-255) below or above which that rule applies


def halftone(coverage, cell, angle=45):
    # coverage (0-1 per pixel) as a pattern of solid dots on a grid of `cell` pixels, turned
    # by `angle` degrees: True where ink goes
    h, w = coverage.shape
    a = np.radians(angle)
    xs = np.arange(w, dtype=np.float32)[None, :]
    out = np.empty((h, w), bool)
    for y0 in range(0, h, 256):                          # in strips, to keep print-size covers light
        ys = np.arange(y0, min(h, y0 + 256), dtype=np.float32)[:, None]
        u, v = xs * np.cos(a) + ys * np.sin(a), -xs * np.sin(a) + ys * np.cos(a)
        du, dv = (u % cell) - cell / 2, (v % cell) - cell / 2
        radius = cell * np.sqrt(np.clip(coverage[y0:y0 + 256], 0, 1) / np.pi)   # a dot's area is the coverage
        out[y0:y0 + 256] = np.hypot(du, dv) < radius
    return out

def edge_fade(side, seed=1):
    # coverage for a side x side cover: 1 in the middle, falling to 0 at the edges over a
    # ragged band
    t = np.linspace(0, 1, side, dtype=np.float32)
    to_edge = np.minimum(np.minimum(t, 1 - t)[None, :], np.minimum(t, 1 - t)[:, None])   # 0 at the edge, 0.5 in the middle
    rough = np.random.default_rng(seed).random((12, 12)).astype(np.float32)
    rough = cv2.resize(rough, (side, side), interpolation=cv2.INTER_CUBIC) - 0.5
    reach = to_edge / FADE + rough * RAGGED * 2
    return np.clip(reach, 0, 1) ** 1.5

def knockout_coverage(cover, shirt_colour):
    # coverage for the cover's pixels: 0 where the shirt can stand in for them (that part
    # isn't printed: the shirt shows), 1 where they need ink. On a dark shirt that's every
    # part about as dark as the shirt or darker (its shadows and blacks become the shirt); on
    # a light shirt, every part about as light or lighter; on a coloured shirt, the parts
    # close to its colour
    lab = cv2.cvtColor(cover, cv2.COLOR_BGR2LAB).astype(np.float32)
    shirt = cv2.cvtColor(np.uint8([[shirt_colour]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
    if shirt[0] < DARK_SHIRT or shirt[0] > LIGHT_SHIRT:
        lighter = lab[..., 0] - shirt[0]
        stands_out = lighter if shirt[0] < DARK_SHIRT else -lighter
        lo, hi = KNOCKOUT_LIGHTNESS
        return np.clip((stands_out - lo) / (hi - lo), 0, 1)
    distance = np.linalg.norm(lab - shirt, axis=2)
    lo, hi = KNOCKOUT
    return np.clip((distance - lo) / (hi - lo), 0, 1)

def style_cover(cover, style, shirt_colour=(30, 30, 30), dpi=300, seed=1):
    # the cover (BGR, square) as BGRA in a tee style. shirt_colour: the garment's colour (BGR),
    # for the knockout
    if style not in STYLES:
        raise ValueError(f'Unknown tee style: {style}')
    side = cover.shape[0]
    coverage = np.ones(cover.shape[:2], np.float32)
    if style in ('faded', 'faded_knockout'):
        coverage *= edge_fade(side, seed)
    if style in ('knockout', 'faded_knockout'):
        coverage *= knockout_coverage(cover, shirt_colour)
    if style == 'classic':
        ink = np.ones(cover.shape[:2], bool)
    else:
        # solid where fully covered, dots where part-covered, nothing where uncovered
        ink = (coverage >= 0.98) | halftone(coverage, max(3.0, dpi * DOT_IN))
    return np.dstack([cover, np.where(ink, 255, 0).astype(np.uint8)])

def style_print_file(print_file, style, shirt_colour=(30, 30, 30), dpi=300, seed=1):
    # a garment print file (BGRA, the cover as the opaque square in it) with its cover in a
    # tee style
    if style == 'classic':
        return print_file
    out = print_file.copy()
    ys, xs = np.nonzero(print_file[..., 3] > 127)
    if not len(ys):
        return out
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    out[y0:y1, x0:x1] = style_cover(print_file[y0:y1, x0:x1, :3], style, shirt_colour, dpi, seed)
    return out
