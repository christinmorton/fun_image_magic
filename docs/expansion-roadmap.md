# Expansion Roadmap: from course project to photo booth

Steps to grow `app.py` into the student photo booth described in `readme.md`, in the order
they should be done. Steps 1–4 use only skills from the course and together make a usable
event photo booth. Bugs to fix first are listed in `docs/project-review.md`.

Work in `code/course_project_extended/app.py` (currently a copy of the course version), so
the original stays as a record of the course.

| Step | Feature | New skills needed |
| --- | --- | --- |
| 1 | Live webcam input | None |
| 2 | Named filter presets | None (more kernels and colour maths) |
| 3 | Branded frame overlay | Alpha blending |
| 4 | Countdown and photo strip | Timing in the loop |
| 5 | Face stickers and background swap | MediaPipe library |
| 6 | Code structure | Python modules |

---

## Step 1: Use the webcam

The biggest single step. Replace the still image with a frame from the camera on every loop,
and the app becomes a live filter mirror.

```python
cap = cv2.VideoCapture(0)          # 0 = the default webcam
if not cap.isOpened():
    raise SystemExit('No webcam found')

while True:
    ok, color_original = cap.read()
    if not ok:
        break
    color_original = cv2.flip(color_original, 1)    # mirror it, like a selfie camera
    gray_original = cv2.cvtColor(color_original, cv2.COLOR_BGR2GRAY)

    # ...the existing filter, adjust, key and display code...

cap.release()
cv2.destroyAllWindows()
```

Also change `cv2.waitKey(100)` to `cv2.waitKey(1)`. At 100 ms the video runs at about
10 frames per second at best; at 1 ms it runs as fast as the camera allows.

---

## Step 2: Turn the sliders into named presets

Students at an event won't adjust sliders. Give them named looks they switch between with the
number keys. Each preset is a function that takes an image and returns a new one.

**Vintage (sepia + vignette):**

```python
# Sepia colour matrix, written for OpenCV's BGR channel order
SEPIA = np.array([[0.131, 0.534, 0.272],
                  [0.168, 0.686, 0.349],
                  [0.189, 0.769, 0.393]])

def sepia(img):
    return cv2.transform(img, SEPIA)

def vignette(img, strength=1.5):
    # Darkens the edges, using two 1D Gaussians multiplied into a 2D mask
    h, w = img.shape[:2]
    mask = cv2.getGaussianKernel(h, h / strength) @ cv2.getGaussianKernel(w, w / strength).T
    mask = mask / mask.max()
    return (img * mask[..., None]).astype(np.uint8)
```

**Pencil sketch:**

```python
def sketch(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(255 - gray, (21, 21), 0)
    out = cv2.divide(gray, 255 - blur, scale=256)
    return cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
```

**Cartoon:**

```python
def cartoon(img):
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 7)
    edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                  cv2.THRESH_BINARY, 9, 9)
    color = cv2.bilateralFilter(img, 9, 250, 250)   # smooths colours, keeps edges
    return cv2.bitwise_and(color, color, mask=edges)
```

**Pop-art grid (four tinted copies, Warhol style):**

```python
def pop_art(img):
    small = cv2.resize(img, None, fx=0.5, fy=0.5)
    tints = [(1.0, 0.3, 0.3), (0.3, 1.0, 0.3), (0.3, 0.3, 1.0), (1.0, 1.0, 0.2)]  # BGR
    tiles = [(small * np.array(t)).astype(np.uint8) for t in tints]
    return np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
```

**Two more kernels for the existing list:**

```python
emboss_kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
edge_kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
```

**Switching presets with number keys:**

```python
PRESETS = {
    '1': ('Original', lambda img: img),
    '2': ('Vintage', lambda img: vignette(sepia(img))),
    '3': ('Sketch', sketch),
    '4': ('Cartoon', cartoon),
    '5': ('Pop Art', pop_art),
}
current = '1'

# inside the loop, after waitKey:
if key != -1 and chr(key & 0xFF) in PRESETS:
    current = chr(key & 0xFF)

name, effect = PRESETS[current]
display = effect(color_original)
cv2.putText(display, name, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
```

Ideas for more presets: "Noir" (grey + high contrast + vignette), "School Colors" (tint toward
the school's colours), "Neon" (edge detection with bright coloured edges on black).

---

## Step 3: Branded frame overlay

Lay a transparent PNG (mascot in a corner, event name, date) over every photo. Make the PNG in
any image editor with a transparent middle, at the same shape as the camera frame.

```python
frame_png = cv2.imread(str(BASE_DIR / 'frame.png'), cv2.IMREAD_UNCHANGED)   # keeps alpha

def apply_overlay(img, overlay):
    overlay = cv2.resize(overlay, (img.shape[1], img.shape[0]))
    alpha = overlay[..., 3:] / 255.0        # 0 = transparent, 1 = solid
    return (overlay[..., :3] * alpha + img * (1 - alpha)).astype(np.uint8)
```

Apply the overlay **after** the preset, so the frame itself isn't filtered.

---

## Step 4: Countdown and photo strip

The classic booth format: press the space bar, see a 3-2-1 countdown, and get 4 shots stacked
into one strip.

The loop must keep running during the countdown so the video stays live, so don't use
`time.sleep`. Track the countdown state in variables instead:

```python
import time

SHOTS_PER_STRIP = 4
SECONDS_PER_SHOT = 3
shooting, shots, next_shot_at = False, [], 0

# inside the loop, after building `display`:
if key == ord(' ') and not shooting:
    shooting, shots, next_shot_at = True, [], time.time() + SECONDS_PER_SHOT

if shooting:
    now = time.time()
    if now >= next_shot_at:
        shots.append(display.copy())          # take the shot before drawing any text
        next_shot_at = now + SECONDS_PER_SHOT
        if len(shots) == SHOTS_PER_STRIP:
            strip = np.vstack(shots)
            cv2.imwrite(str(OUTPUT_DIR / f'strip-{datetime.now():%Y%m%d-%H%M%S}.png'), strip)
            shooting = False
    else:
        seconds_left = int(next_shot_at - now) + 1
        cv2.putText(display, str(seconds_left), (display.shape[1] // 2 - 30, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 8)

cv2.imshow('app', display)
```

Nice extras: a white "flash" frame when each shot is taken, and showing the finished strip
on screen for a few seconds.

---

## Step 5: Face stickers and background swap

These go beyond the course but need no AI training. The **MediaPipe** library
(`pip install mediapipe`) does the hard part and works on the same frames from the same loop.

- **Face-tracked stickers.** MediaPipe's *Face Landmarker* returns the positions of points on
  each face (eyes, nose, forehead, chin) on every frame. Use those positions to place and size
  a transparent sticker PNG (mascot ears, hat, glasses) with the same alpha blending as Step 3.
- **Background swap.** MediaPipe's *Image Segmenter* (selfie model) returns a mask of which
  pixels are a person. Blend the person over a background image (the stadium, a campus
  landmark, space) with that mask. No green screen needed.
- **"Pose with the mascot."** No library needed: a large mascot PNG fixed on one side of the
  overlay from Step 3, so students stand next to it.

MediaPipe's Python API has changed between versions, so follow the current examples in its
official documentation rather than older tutorials.

---

## Step 6: Organise the code as it grows

One file gets hard to work in after a few presets. A suggested layout:

```
code/course_project_extended/
├── app.py            # the main loop: camera, keys, display, saving
├── filters.py        # kernels and preset functions (sepia, sketch, cartoon...)
├── overlays.py       # frame overlay and stickers
├── booth.py          # countdown and photo strip logic
├── assets/           # frame.png, stickers, backgrounds
├── output/           # saved photos and strips (add to .gitignore)
└── requirements.txt  # opencv-python, numpy (and mediapipe for Step 5)
```

Then `app.py` starts with `from filters import PRESETS` and stays short.

---

## After that

From the engagement ideas in `readme.md`, the most valuable next features are:

1. **QR code sharing.** Show a QR code on screen so students can download their photo to their
   phone. This needs a small web server or upload service, and is probably the feature that
   matters most at the event, because photos end up on social media.
2. **A live gallery.** A second window or screen that cycles through recent photos.
3. **AI style presets.** A fixed menu of tested styles (no free-text prompts) sent to an
   image-generation service. Add these only after the basic booth has worked at an event.
