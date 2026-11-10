# photo_mockups: designs shown on real photos of people wearing blank garments, so they
# look printed rather than pasted on. Each photo is set up once: where the product's print
# area sits on it (four corners), which product it shows, front or back, and the garment's
# colour, kept next to the photo as <photo>.mockup.json. MediaPipe guesses all of that
# (guess()): the pose model finds the shoulders (for the size and slope), a second model
# marks which pixels are clothes (kept as <photo>.clothes.png), and the print area hangs a
# couple of inches below the neckline it shows, at its real size. Hands, hair and bags in
# front of the shirt stay in front of the print. print_on() then makes the design look
# printed rather than pasted on: matte ink colours, wrapped round the chest, as soft as the
# photo, bent along the fabric's folds, shaded by them and given the fabric's texture.
# The photos are bought mockups, licensed for showing our own designs but not for sharing,
# so mockup_photos/ is kept out of git.
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import cv2
import numpy as np

from . import CORE_DIR, MODELS_DIR

MOCKUP_PHOTOS_DIR = CORE_DIR.parent / 'mockup_photos'
MOCKUP_MODELS_DIR = MODELS_DIR / 'mockups'       # fetched by tools/get_mockup_models.py
PHOTO_TYPES = ('.png', '.jpg', '.jpeg', '.webp')

# the multiclass selfie segmenter's labels, one per pixel
BACKGROUND, HAIR, BODY_SKIN, FACE_SKIN, CLOTHES, OTHERS = range(6)

# an adult's body, to put a print area on it at its real size: MediaPipe's shoulder points
# (the joints) are about 15 in apart, and its hip points about 21 in below them
SHOULDER_IN, TORSO_IN = 15.0, 21.0
# where each product's print area starts, in inches below the bottom of the neckline: a
# couple of inches under the collar, or under the hood's drawstrings
PRINT_TOP_IN = {'tee': 2.5, 'sweatshirt': 2.5, 'hoodie': 4.0}
# the neckline is about 1.5 in above MediaPipe's shoulder line (measured on the tee photos),
# which stands in for it when it can't be found. It's hardly ever more than a quarter of an
# inch below it: lower than that is a beard or hair hanging over the collar
COLLAR_ABOVE_SHOULDERS_IN = 1.5
COLLAR_LOWEST_IN = 0.25
MAX_TILT = 10               # degrees: a sloping shoulder line is mostly a raised arm, not a tilted chest

# a photo's state: 'good' (guessed, and passed every check), 'check' (guessed, but something
# needs a look), 'set' (placed or confirmed by hand), 'skip' (not to be used)
STATUSES = ('good', 'check', 'set', 'skip')
USABLE = ('good', 'set')


@dataclass(frozen=True)
class Placement:
    product: str                  # a product key: 'tee', 'hoodie' or 'sweatshirt'
    corners: tuple                # the print area in photo pixels: top left, top right,
                                  # bottom right, bottom left (as the photo shows them)
    view: str = 'front'           # 'front' or 'back'
    colour: tuple = (128, 128, 128)   # the garment's colour (BGR)
    status: str = 'check'
    notes: tuple = ()             # why a guess needs checking, in plain words

    @property
    def dark(self):
        # a dark garment: prints are shaded differently on it
        b, g, r = self.colour
        return 0.114 * b + 0.587 * g + 0.299 * r < 110


@dataclass
class Analysis:
    # what the models found in a photo
    bodies: list                  # one dict per person: landmark name -> (x, y, visibility), in pixels
    labels: object                # uint8 per pixel (BACKGROUND ... OTHERS), or None


# the pose landmarks used here, by MediaPipe's numbers. "left" is the person's left
LANDMARKS = {'nose': 0, 'left_shoulder': 11, 'right_shoulder': 12, 'left_hip': 23, 'right_hip': 24}


class BodyFinder:
    # MediaPipe's pose landmarker and multiclass segmenter, for single photos; call it with a
    # BGR photo to get an Analysis
    def __init__(self, models_dir=MOCKUP_MODELS_DIR):
        from mediapipe.tasks.python import BaseOptions, vision
        pose, segmenter = models_dir / 'pose_landmarker_full.task', models_dir / 'selfie_multiclass_256x256.tflite'
        if not (pose.is_file() and segmenter.is_file()):
            raise FileNotFoundError('The mockup models are missing: run tools\\get_mockup_models.py once')
        self.pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(pose)), running_mode=vision.RunningMode.IMAGE, num_poses=3))
        self.segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(segmenter)), running_mode=vision.RunningMode.IMAGE,
            output_category_mask=True, output_confidence_masks=False))

    def __call__(self, photo):
        import mediapipe as mp
        h, w = photo.shape[:2]
        rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(photo, cv2.COLOR_BGR2RGB))
        bodies = [{name: (lm[i].x * w, lm[i].y * h, lm[i].visibility) for name, i in LANDMARKS.items()}
                  for lm in self.pose.detect(rgb).pose_landmarks]
        # copy the mask: MediaPipe may reuse the memory
        labels = np.array(self.segmenter.segment(rgb).category_mask.numpy_view()).reshape(h, w)
        return Analysis(bodies, labels)

    def close(self):
        self.pose.close()
        self.segmenter.close()


# --- photos and their set-up files --------------------------------------------------------

def list_photos(folder=MOCKUP_PHOTOS_DIR):
    # every mockup photo under the folder (sub-folders too), by path
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.rglob('*') if p.suffix.lower() in PHOTO_TYPES
                  and not p.name.endswith('.clothes.png') and p.is_file())

def read_photo(path):
    # np.fromfile + imdecode also works for paths with non-English characters
    try:
        return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_COLOR)
    except OSError:
        return None

def placement_path(photo_path):
    return photo_path.with_name(photo_path.name + '.mockup.json')

def clothes_path(photo_path):
    return photo_path.with_name(photo_path.name + '.clothes.png')

def save_placement(photo_path, placement):
    data = asdict(placement)
    data['corners'] = [[round(x, 1), round(y, 1)] for x, y in placement.corners]
    data['colour'], data['notes'] = list(placement.colour), list(placement.notes)
    placement_path(photo_path).write_text(json.dumps(data, indent=2), encoding='utf-8')

def load_placement(photo_path):
    # the photo's set-up, or None if it hasn't been set up
    path = placement_path(photo_path)
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    return Placement(data['product'], tuple(tuple(c) for c in data['corners']), data.get('view', 'front'),
                     tuple(data.get('colour', (128, 128, 128))), data.get('status', 'check'), tuple(data.get('notes', ())))

def save_clothes(photo_path, labels):
    # which pixels are clothes, as a black and white PNG
    cv2.imencode('.png', np.where(labels == CLOTHES, 255, 0).astype(np.uint8))[1].tofile(str(clothes_path(photo_path)))

def load_clothes(photo_path):
    # the clothes mask (0 or 255 per pixel), or None
    path = clothes_path(photo_path)
    if not path.is_file():
        return None
    return cv2.imdecode(np.fromfile(str(path), np.uint8), cv2.IMREAD_GRAYSCALE)

def product_from_name(path):
    # the product a photo probably shows, from the words in its folder and file names
    words = str(path).lower().replace('_', ' ').replace('-', ' ')
    if 'hoodie' in words:
        return 'hoodie'
    if any(w in words for w in ('sweatshirt', 'crewneck', '18000')):
        return 'sweatshirt'
    return 'tee'


# --- guessing the print area ---------------------------------------------------------------

def print_size_in(product, dpi=300):
    # a product's print area, in inches (width, height)
    return product.width / dpi, product.height / dpi

def find_collar(labels, mid, shoulders):
    # the bottom of the neckline, in pixels, or None: walking up the middle of the shirt from
    # the chest, the first row that isn't shirt. Chains and pendants lie on the shirt, so they
    # count as shirt. The point is centred in the neck opening
    if labels is None:
        return None
    h, w = labels.shape
    shirt = (labels == CLOTHES) | (labels == OTHERS)
    x, half = int(round(mid[0])), max(2, int(shoulders * 0.04))
    y_chest, y_top = int(mid[1] + shoulders * 0.45), max(0, int(mid[1] - shoulders * 0.6))
    if not (half <= x < w - half and y_top < y_chest < h):
        return None
    column = shirt[y_top:y_chest + 1, x - half:x + half + 1].mean(axis=1) > 0.5
    rows = column[::-1]                                  # from the chest upwards
    if not rows[:max(1, len(rows) // 10)].all() or rows.all():
        return None                                      # no shirt at the chest, or no neckline
    y = y_chest - int(np.argmin(rows)) + 1               # the top of the shirt in the middle
    # the neck opening just above it: centre the point in it if shirt bounds it on both sides
    row = shirt[max(0, y - 2)]
    reach = int(shoulders * 0.6)
    left = np.flatnonzero(row[max(0, x - reach):x])
    right = np.flatnonzero(row[x:min(w, x + reach)])
    if len(left) and len(right):
        x = (max(0, x - reach) + left[-1] + x + right[0]) / 2
    return np.array([float(x), float(y)])

def corners_on(body, size_in, top_in, photo_shape, labels=None):
    # the print area's corners on a body, and notes about anything doubtful. The shoulders
    # give the size and the slope; the neckline (when found) gives where it starts
    notes = []
    p = {name: np.array(v[:2], np.float64) for name, v in body.items()}
    seen = {name: v[2] for name, v in body.items()}
    a, b = sorted((p['left_shoulder'], p['right_shoulder']), key=lambda q: q[0])
    across = b - a
    shoulders = float(np.linalg.norm(across))
    angle = np.clip(np.arctan2(across[1], across[0]), -np.radians(MAX_TILT), np.radians(MAX_TILT))
    ux = np.array([np.cos(angle), np.sin(angle)])
    uy = np.array([-ux[1], ux[0]])                       # a quarter turn: down the body
    mid_shoulders = (a + b) / 2
    per_in = shoulders / SHOULDER_IN
    per_in_y = per_in                                    # facing the camera, the same both ways
    h = photo_shape[0]
    hips_seen = min(seen['left_hip'], seen['right_hip']) >= 0.5 and max(p['left_hip'][1], p['right_hip'][1]) <= h * 1.05
    if hips_seen:
        ratio = float(np.dot((p['left_hip'] + p['right_hip']) / 2 - mid_shoulders, uy)) / TORSO_IN / per_in
        if ratio > 1.3:                                  # a body turned sideways: narrow shoulders
            per_in_y = per_in * min(ratio, 1.6)
            notes.append('The body looks turned: check the size')
        elif ratio < 0.7:
            notes.append('The body looks bent or seated: check the height')
    collar = find_collar(labels, mid_shoulders, shoulders)
    if collar is None:
        collar = mid_shoulders - COLLAR_ABOVE_SHOULDERS_IN * per_in_y * uy
        if labels is not None:
            notes.append('Couldn\'t find the neckline: check the height')
    else:
        below = float(np.dot(collar - mid_shoulders, uy)) / per_in_y
        if below > COLLAR_LOWEST_IN:                     # a beard over the collar: lift it back up
            collar = collar - (below - COLLAR_LOWEST_IN) * per_in_y * uy
    width, height = size_in
    corners = [collar + u * per_in * ux + v * per_in_y * uy
               for u, v in ((-width / 2, top_in), (width / 2, top_in), (width / 2, top_in + height),
                            (-width / 2, top_in + height))]
    return tuple((float(x), float(y)) for x, y in corners), notes, shoulders

def default_corners(size_in, photo_shape):
    # a print area in the middle of the photo, for when no person is found
    h, w = photo_shape[:2]
    width = w * 0.4
    height = width * size_in[1] / size_in[0]
    x0, y0 = (w - width) / 2, h * 0.3
    return ((x0, y0), (x0 + width, y0), (x0 + width, y0 + height), (x0, y0 + height))

def quad_mask(corners, shape):
    mask = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(mask, [np.round(np.array(corners)).astype(np.int32)], 255, cv2.LINE_AA)
    return mask

def garment_colour(photo, corners, labels=None):
    # the median colour of the shirt inside the print area (BGR)
    inside = quad_mask(corners, photo.shape) > 127
    if labels is not None and (inside & (labels == CLOTHES)).sum() > 50:
        inside &= labels == CLOTHES
    if not inside.any():
        return (128, 128, 128)
    return tuple(int(c) for c in np.median(photo[inside], axis=0))

def place(photo, analysis, product, dpi=300):
    # a guessed Placement for one product on the photo, from what the models found
    h, w = photo.shape[:2]
    size_in = print_size_in(product, dpi)
    notes = []
    labels = analysis.labels
    bodies = [b for b in analysis.bodies if min(b['left_shoulder'][2], b['right_shoulder'][2]) >= 0.5]
    if not bodies:
        corners = default_corners(size_in, photo.shape)
        notes.append('No person found: drag the corners onto the shirt, or skip the photo')
        # no pose to go by: a front view shows a face (a bit of neck or ear doesn't count)
        view = 'front' if labels is None or (labels == FACE_SKIN).mean() > 0.002 else 'back'
    else:
        body = max(bodies, key=lambda b: abs(b['left_shoulder'][0] - b['right_shoulder'][0]))
        # facing the camera, the person's left shoulder is on the photo's right; from
        # behind, it's on the left
        view = 'front' if body['left_shoulder'][0] > body['right_shoulder'][0] else 'back'
        if len(bodies) > 1:
            notes.append(f'{len(bodies)} people: used the biggest')
        corners, more, shoulders = corners_on(body, size_in, PRINT_TOP_IN.get(product.key, 2.5), photo.shape, labels)
        notes += more
        a, b = sorted((body['left_shoulder'][:2], body['right_shoulder'][:2]))
        tilt = abs(np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])))
        if tilt > MAX_TILT:
            notes.append(f'The shoulders slope {tilt:.0f} degrees (a raised arm?)')
        if shoulders < w * 0.12:
            notes.append('The person is small in the photo')
    if view == 'back':
        notes.append('Looks like a back view')
    xs, ys = [c[0] for c in corners], [c[1] for c in corners]
    if min(xs) < -2 or min(ys) < -2 or max(xs) > w + 2 or max(ys) > h + 2:
        notes.append('The print area runs off the photo')
    if labels is not None and bodies:
        inside = quad_mask(corners, photo.shape) > 127
        covered = 1 - (labels[inside] == CLOTHES).mean() if inside.any() else 1
        if covered > 0.1:
            notes.append(f'{covered:.0%} of the print area isn\'t shirt: look for hands, hair or a bag')
    status = 'check' if notes else 'good'
    if min(h, w) < 1200:
        notes.append(f'A small photo ({w} x {h}): fine on screen, soft as a big listing photo')
    return Placement(product.key, corners, view, garment_colour(photo, corners, labels), status, tuple(notes))

def guess(photo_path, finder, products_by_key, product_key=None, dpi=300):
    # set up one photo automatically: guess its placement, and keep it and the clothes mask
    # next to the photo. product_key: the product it shows (None: from its name)
    photo = read_photo(photo_path)
    if photo is None:
        raise ValueError(f'Could not read {photo_path.name}')
    analysis = finder(photo)
    placement = place(photo, analysis, products_by_key[product_key or product_from_name(photo_path)], dpi)
    if analysis.labels is not None:
        save_clothes(photo_path, analysis.labels)
    save_placement(photo_path, placement)
    return placement

def refit(placement, product, dpi=300):
    # the placement for another product: the same width and top edge, the new product's shape
    w_in, h_in = print_size_in(product, dpi)
    tl, tr, br, bl = (np.array(c) for c in placement.corners)
    down = (bl - tl) / max(np.linalg.norm(bl - tl), 1e-6)
    height = np.linalg.norm(tr - tl) * h_in / w_in
    corners = (tl, tr, tr + down * height, tl + down * height)
    return replace(placement, product=product.key, corners=tuple((float(x), float(y)) for x, y in corners))


# --- printing a design on a photo ------------------------------------------------------------

INK_RANGE = (14, 238)       # ink on cotton: no pure black or pure white
INK_SATURATION = 0.88       # and a little less vivid than on a screen
WRAP = 0.7                  # radians: how far the print area wraps round the chest at its sides

def as_ink(rgb):
    # screen colours (float) as they come out printed on cotton: matte and a little muted
    gray = rgb.mean(axis=2, keepdims=True)
    rgb = gray + (rgb - gray) * INK_SATURATION
    lo, hi = INK_RANGE
    return lo + rgb * (hi - lo) / 255

def wrap(img):
    # the flat print as seen wrapped round a chest: the middle a little wider, the sides
    # squeezed, as on a curved surface seen from the front
    h, w = img.shape[:2]
    seen = (np.arange(w, dtype=np.float32) + 0.5) / w * 2 - 1
    flat = np.arcsin(seen * np.sin(WRAP)) / WRAP
    map_x = np.tile(((flat + 1) / 2 * w - 0.5).astype(np.float32), (h, 1))
    map_y = np.repeat(np.arange(h, dtype=np.float32)[:, None], w, axis=1)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def print_on(photo, corners, design, clothes=None, dark=None):
    # the photo with the design printed in the corners. design: BGR or BGRA (see-through
    # parts aren't printed). clothes: the clothes mask, so whatever is in front of the shirt
    # stays in front. dark: a dark garment (None: worked out from the photo)
    out = photo.copy()
    h, w = photo.shape[:2]
    quad = np.array(corners, np.float32)
    x0, y0 = np.floor(quad.min(axis=0)).astype(int) - 4
    x1, y1 = np.ceil(quad.max(axis=0)).astype(int) + 4
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, w), min(y1, h)
    if x1 - x0 < 4 or y1 - y0 < 4:
        return out
    region = photo[y0:y1, x0:x1].astype(np.float32)
    local = quad - np.float32([x0, y0])
    if design.shape[2] == 3:
        design = np.dstack([design, np.full(design.shape[:2], 255, np.uint8)])
    # shrink the design to about the size it appears, so the warp doesn't alias it
    width = max(np.linalg.norm(quad[1] - quad[0]), np.linalg.norm(quad[2] - quad[3]))
    height = max(np.linalg.norm(quad[3] - quad[0]), np.linalg.norm(quad[2] - quad[1]))
    scale = min(1.0, 1.5 * max(width / design.shape[1], height / design.shape[0]))
    if scale < 1.0:
        design = cv2.resize(design, (max(2, round(design.shape[1] * scale)), max(2, round(design.shape[0] * scale))),
                            interpolation=cv2.INTER_AREA)
    dh, dw = design.shape[:2]
    # premultiplied, so the see-through edges don't blend in black; as ink, wrapped round the chest
    alpha = design[..., 3:].astype(np.float32) / 255
    premul = wrap(np.dstack([as_ink(design[..., :3].astype(np.float32)) * alpha, alpha]))
    matrix = cv2.getPerspectiveTransform(np.float32([(0, 0), (dw, 0), (dw, dh), (0, dh)]), local)
    layer = cv2.warpPerspective(premul, matrix, (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # as soft as the photo: these are rarely pin-sharp, and a crisp print looks pasted on
    layer = cv2.GaussianBlur(layer, (0, 0), 0.5 + width / 2000)
    # the fabric: its folds (smoothed brightness) and its weave (the fine detail)
    gray = cv2.cvtColor(region.astype(np.uint8), cv2.COLOR_BGR2GRAY).astype(np.float32)
    folds = cv2.GaussianBlur(gray, (0, 0), max(1.5, width / 300))
    weave = gray - cv2.GaussianBlur(gray, (0, 0), 1.2)
    inside = cv2.warpPerspective(np.ones((dh, dw), np.float32), matrix, (x1 - x0, y1 - y0)) > 0.5
    if clothes is not None:
        cloth = clothes[y0:y1, x0:x1] > 127
        if (inside & cloth).sum() > 50:
            inside &= cloth
    base = float(np.median(folds[inside])) if inside.any() else float(np.median(folds))
    if dark is None:
        dark = base < 110
    # bend the print along the folds: each pixel moves a little down the brightness slope
    big_folds = cv2.GaussianBlur(gray, (0, 0), max(2.0, width / 60))
    gx, gy = cv2.Sobel(big_folds, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(big_folds, cv2.CV_32F, 0, 1, ksize=3)
    steep = np.percentile(np.hypot(gx, gy)[inside], 99) if inside.any() else 1.0
    reach = width * 0.009 / max(steep, 1e-3)
    ys, xs = np.mgrid[0:y1 - y0, 0:x1 - x0].astype(np.float32)
    layer = cv2.remap(layer, xs + gx * reach, ys + gy * reach, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    # shade it: darker in the folds, brighter on the highlights (gentler on dark garments,
    # whose shadows are mostly noise)
    shade = np.clip(1 + (folds - base) / max(base, 120 if dark else 60), 0.45, 1.3)
    a = layer[..., 3] * 0.97                             # ink, not paint: a little of the fabric shows
    if clothes is not None:
        a *= cv2.GaussianBlur((clothes[y0:y1, x0:x1] > 127).astype(np.float32), (0, 0), 1.2)
    ink = layer[..., :3] * (a / np.maximum(layer[..., 3], 1e-6))[..., None]
    ink = ink * shade[..., None] + (weave * (0.5 if dark else 0.8))[..., None] * a[..., None]
    out[y0:y1, x0:x1] = np.clip(region * (1 - a[..., None]) + ink, 0, 255).astype(np.uint8)
    return out


# --- using the set-up photos ---------------------------------------------------------------

def ready_photos(product_key, folder=MOCKUP_PHOTOS_DIR, limit=None):
    # the set-up photos a design on this product can go on (front views that are good or set
    # by hand, the hand-set ones first), as (path, placement)
    found = []
    for path in list_photos(folder):
        placement = load_placement(path)
        if placement and placement.product == product_key and placement.view == 'front' and placement.status in USABLE:
            found.append((path, placement))
    found.sort(key=lambda item: (item[1].status != 'set', str(item[0])))
    return found[:limit] if limit else found

def fit_design(design, product, dpi=300):
    # the design on a see-through canvas shaped like the product's print area, at the top in
    # the middle (as garments are printed), so a design made for another product isn't stretched
    w_in, h_in = print_size_in(product, dpi)
    h, w = design.shape[:2]
    if abs(w / h - w_in / h_in) < 0.01:
        return design
    if design.shape[2] == 3:
        design = np.dstack([design, np.full((h, w), 255, np.uint8)])
    width, height = max(w, round(h * w_in / h_in)), max(h, round(w * h_in / w_in))
    out = np.zeros((height, width, 4), np.uint8)
    x = (width - w) // 2
    out[:h, x:x + w] = design
    return out

def mockup(path, placement, design):
    # one finished mockup: the design printed on the photo
    return print_on(read_photo(path), placement.corners, design, load_clothes(path), placement.dark)

def write_jpg(path, img, quality=92):
    cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])[1].tofile(str(path))

def make_photo_mockups(print_files, out_dir, folder=MOCKUP_PHOTOS_DIR, limit=6, progress=None):
    # photo mockups of each product given (key -> print file), as out_dir/<product>-<photo>.jpg;
    # returns the files written
    written = []
    for key, design in print_files.items():
        for path, placement in ready_photos(key, folder, limit):
            if progress:
                progress(f'Photo mockup: {key} on {path.stem}...')
            out_dir.mkdir(parents=True, exist_ok=True)
            target = out_dir / f'{key}-{path.stem}.jpg'
            write_jpg(target, mockup(path, placement, design))
            written.append(target)
    return written
