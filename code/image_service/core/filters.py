# filters: the convolution kernels from the course, and the named preset effects.
# Every preset takes a BGR image and returns a new BGR image of the same size.
import cv2
import numpy as np


# define convolution kernels
identity_kernel = np.array([[0,0,0], [0,1,0], [0,0,0]])
sharpen_kernel = np.array([[0,-1,0], [-1,5,-1], [0,-1,0]])
# getGaussianKernel gives a single column (it would only blur up and down), so multiply
# it by its own transpose to get a square kernel that blurs in every direction
gaussian_kernel1 = cv2.getGaussianKernel(3, 0) @ cv2.getGaussianKernel(3, 0).T   # 3x3
gaussian_kernel2 = cv2.getGaussianKernel(5, 0) @ cv2.getGaussianKernel(5, 0).T   # 5x5
box_kernel = np.array([[1,1,1], [1,1,1], [1,1,1]], np.float32) / 9.0
# (1 + 2 + 3 + 4 + 5) / 5 = 1 * 1/5 + 2 * 1/5 + 3 * 1/5 + 4 * 1/5 + 5 * 1/5
emboss_kernel = np.array([[-2,-1,0], [-1,1,1], [0,1,2]])
edge_kernel = np.array([[-1,-1,-1], [-1,8,-1], [-1,-1,-1]])

KERNELS = [identity_kernel, sharpen_kernel, gaussian_kernel1, gaussian_kernel2, box_kernel, emboss_kernel, edge_kernel]


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

def comic_dots(img, cell=None):
    # halftone: a coloured dot per cell, bigger where the photo is darker
    # cells grow with the picture (8 px at webcam size), so big photos don't need
    # thousands more dots - and the dots look the same size on screen
    h, w = img.shape[:2]
    cell = cell or max(8, w // 80)
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

# presets that move parts of the picture around: face stickers go on before these, so
# they get copied / mirrored along with the face instead of floating where the face was
MOVES_PIXELS = {'Pop Art', 'Mirror'}

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
