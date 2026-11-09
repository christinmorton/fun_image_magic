# mockups: quick previews of each product, drawn here rather than photographed - a black
# t-shirt, a black hoodie, a framed poster on a wall and a phone case - so a design can be
# judged on the thing it will be printed on. Licensed photo mockups can replace them later.
import cv2
import numpy as np

TILE = 800                  # each mockup, in pixels
SHIRT = (28, 28, 30)        # the garments' colour (black)


def fit(img, width, height):
    # img scaled to fit inside width x height, keeping its shape
    scale = min(width / img.shape[1], height / img.shape[0])
    return cv2.resize(img, (max(1, int(img.shape[1] * scale)), max(1, int(img.shape[0] * scale))),
                      interpolation=cv2.INTER_AREA)

def lay(canvas, img, cx, top):
    # a BGR or BGRA image laid on the canvas, centred across at cx, from `top` down
    h, w = img.shape[:2]
    x = int(cx - w / 2)
    if img.shape[2] == 4:
        a = img[..., 3:] / 255.0
        canvas[top:top + h, x:x + w] = (img[..., :3] * a + canvas[top:top + h, x:x + w] * (1 - a)).astype(np.uint8)
    else:
        canvas[top:top + h, x:x + w] = img

def label(canvas, text):
    cv2.putText(canvas, text, (20, TILE - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 60), 2, cv2.LINE_AA)

def tee(print_file):
    canvas = np.full((TILE, TILE, 3), 225, np.uint8)
    body = np.array([(250, 120), (330, 95), (400, 130), (470, 95), (550, 120), (690, 230), (620, 320),
                     (570, 280), (575, 720), (225, 720), (230, 280), (180, 320), (110, 230)], np.int32)
    cv2.fillPoly(canvas, [body], SHIRT, cv2.LINE_AA)
    cv2.ellipse(canvas, (400, 112), (62, 30), 0, 0, 180, (60, 60, 62), 6, cv2.LINE_AA)       # collar
    lay(canvas, fit(print_file, 270, 324), 400, 190)
    label(canvas, 'T-shirt')
    return canvas

def hoodie(print_file):
    canvas = np.full((TILE, TILE, 3), 225, np.uint8)
    cv2.ellipse(canvas, (400, 150), (110, 120), 0, 180, 360, SHIRT, -1, cv2.LINE_AA)        # hood
    body = np.array([(260, 150), (540, 150), (640, 230), (735, 600), (668, 625), (585, 360), (585, 730),
                     (215, 730), (215, 360), (132, 625), (65, 600), (160, 230)], np.int32)       # long sleeves
    cv2.fillPoly(canvas, [body], SHIRT, cv2.LINE_AA)
    cv2.rectangle(canvas, (300, 560), (500, 680), (40, 40, 42), -1)                         # pocket
    cv2.line(canvas, (372, 160), (365, 300), (200, 200, 200), 3, cv2.LINE_AA)                # drawstrings
    cv2.line(canvas, (428, 160), (435, 300), (200, 200, 200), 3, cv2.LINE_AA)
    lay(canvas, fit(print_file, 250, 214), 400, 320)
    label(canvas, 'Hoodie')
    return canvas

def poster(print_file):
    canvas = np.full((TILE, TILE, 3), (190, 200, 205), np.uint8)                            # a wall
    art = fit(print_file, 420, 560)
    h, w = art.shape[:2]
    x, y = (TILE - w) // 2, 90
    cv2.rectangle(canvas, (x - 14 + 10, y - 14 + 12), (x + w + 14 + 10, y + h + 14 + 12), (150, 158, 162), -1)   # shadow
    cv2.rectangle(canvas, (x - 14, y - 14), (x + w + 14, y + h + 14), (25, 25, 25), -1)                          # frame
    canvas[y:y + h, x:x + w] = art
    label(canvas, 'Poster')
    return canvas

def phone(print_file):
    canvas = np.full((TILE, TILE, 3), 225, np.uint8)
    art = fit(print_file, 300, 620)
    h, w = art.shape[:2]
    x, y = (TILE - w) // 2, 70
    mask = np.zeros((h, w), np.uint8)
    r = 40
    cv2.rectangle(mask, (r, 0), (w - r, h), 255, -1)
    cv2.rectangle(mask, (0, r), (w, h - r), 255, -1)
    for cx, cy in [(r, r), (w - r, r), (r, h - r), (w - r, h - r)]:
        cv2.circle(mask, (cx, cy), r, 255, -1, cv2.LINE_AA)
    region = canvas[y:y + h, x:x + w]
    m = mask[..., None] / 255.0
    canvas[y:y + h, x:x + w] = (art * m + region * (1 - m)).astype(np.uint8)
    cv2.rectangle(canvas, (x + 20, y + 20), (x + 120, y + 130), (30, 30, 30), -1)          # camera bump
    for cx, cy in [(x + 48, y + 50), (x + 92, y + 50), (x + 70, y + 100)]:
        cv2.circle(canvas, (cx, cy), 17, (70, 70, 75), -1, cv2.LINE_AA)
    label(canvas, 'Phone case')
    return canvas

MOCKUPS = {'tee': tee, 'hoodie': hoodie, 'poster': poster, 'phone': phone}

def mockup_sheet(print_files):
    # the mockups of the products given (key -> print file), two to a row
    tiles = [MOCKUPS[key](img) for key, img in print_files.items() if key in MOCKUPS]
    if not tiles:
        return np.full((TILE, TILE, 3), 225, np.uint8)
    if len(tiles) % 2:
        tiles.append(np.full((TILE, TILE, 3), 225, np.uint8))
    return np.vstack([np.hstack(tiles[i:i + 2]) for i in range(0, len(tiles), 2)])
