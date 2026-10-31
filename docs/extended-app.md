# Extended App: CSN Photo Booth

`code/course_project_extended/` started as a copy of the course project (a still-image editor
with sliders). It has been grown into a photo booth prototype for a College of Southern Nevada
(CSN) event, following `docs/expansion-roadmap.md` Part 1, Steps 1–5. Step 6 (splitting the
code into modules) was skipped on purpose: this version is for experimenting on one machine,
so it stays a single `app.py` in the style of the course code. Last updated 2026-10-31.

All CSN art in `assets/` is **placeholder** art, made by `make_assets.py` from the brand
colours and mascot photo in `resources/csn_assets/`.

---

## What changed from the course version

| Area | Course version | Extended version |
| --- | --- | --- |
| Input | One still image | Webcam, or any uploaded image |
| Looks | 5 kernel filters, brightness, contrast, greyscale | Same, plus emboss and edge kernels and 17 named presets |
| Extras | None | 7 face stickers, 6 background swaps, Cody the mascot, 6 branded frames |
| Saving | `output-N.png`, overwritten each run | Timestamped photos and 4-shot photo strips in `output/` |
| Windows | One window, sliders above the image | Video window plus a separate controls window |

---

## Setup

The app has its own virtual environment in `code/course_project_extended/.venv` (Python 3.15).
To recreate it, from the `course_project_extended` folder in PowerShell:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy mediapipe
```

- MediaPipe installs **`opencv-contrib-python`**, which provides `cv2`. Don't also install
  `opencv-python`: both write to the same `cv2` folder and conflict. If both end up installed,
  uninstall `opencv-python`, then run
  `pip install --force-reinstall --no-deps opencv-contrib-python`.
- **Models** are in `models/`. If they're missing, download them:
  - `face_landmarker.task` from
    `https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task`
  - `selfie_segmenter.tflite` from
    `https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite`
- **VS Code:** run *Python: Select Interpreter* and pick `course_project_extended\.venv`.
  Otherwise VS Code reports "mediapipe could not be resolved".

## Running

```powershell
.\.venv\Scripts\python.exe app.py              # starts with the webcam
.\.venv\Scripts\python.exe app.py photo.jpg    # starts with an image
```

If no webcam is found, the app opens a file dialog to choose an image instead.
Run it as a file (as above). Typing `app.py` at a `>>>` Python prompt gives
`NameError: name 'app' is not defined`.

---

## Controls

Two windows open side by side: **app** (the picture only) and **controls** (sliders plus a key
list). Keys only work after clicking one of the app's windows, not the terminal.

| Slider | Range | What it does |
| --- | --- | --- |
| Contrast, Brightness, Filter, Greyscale | as in the course | Unchanged from the course version |
| Preset | 0–16 | Picks one of the 17 presets |
| Sticker | 0–7 | 0 = off, then each face sticker |
| Background | 0–6 | 0 = off, then each background |
| Cody | 0–1 | Shows the mascot on the right |
| Frame | 0–6 | 0 = off, then each branded frame (starts on 1) |

| Key | Action |
| --- | --- |
| `1`–`9`, `0` | First ten presets |
| `[` / `]` | Previous / next preset |
| `F` / `B` / `O` | Cycle stickers / backgrounds / frames |
| `M` | Cody on or off |
| `Space` | Photo strip: 3-2-1 countdown, 4 shots, white flash |
| `S` | Save the current picture |
| `U` / `W` | Upload an image / back to the webcam |
| `Q` | Quit |

Keys move the matching slider, so the sliders always show the current state.
A key takes effect on the next frame.

---

## Features

**Presets:** Original, Vintage, Sketch, Cartoon, Pop Art, Noir, School Colors (CSN blue to
gold), Neon, Heat Vision, X-Ray, Pixel Art, Comic Dots, Night Vision, VHS, Watercolor, Mirror,
Desert Sunset (CSN purple to orange). Most run in under 40 ms per frame. Comic Dots and Night
Vision take about 45 ms. Watercolor takes about 80 ms (about 12 frames per second), even
though it runs on a half-size copy.

**Face stickers** follow up to 4 faces using MediaPipe's Face Landmarker. Each one is sized from
the distance between the outer eye corners (landmarks 33 and 263) and tilts with the head.
The `STICKERS` list in `app.py` sets each sticker's width (times the eye distance) and its
**lift** (how far above the eyes, in eye distances; negative means below):

| Sticker | Width | Lift |
| --- | --- | --- |
| sunglasses, star_glasses | 1.9 | 0.0 |
| party_hat | 1.7 | 1.65 |
| coyote_ears | 2.2 | 1.65 |
| crown | 1.6 | 1.45 |
| grad_cap | 1.9 | 1.1 |
| mustache | 1.1 | −0.62 |

**Background swap** uses MediaPipe's selfie segmenter: a mask of which pixels are a person,
blended over a background image. No green screen is needed. Backgrounds: celebration, court,
desert_sunset, go_csn, space, vegas_night.

**Cody** is a cut-out of `resources/csn_assets/mascot-2025.jpg`, made with the same
segmenter, standing on the right at 3/4 of the picture height.

**Branded frames:** classic, Go Coyotes, Polaroid, film strip, brand stripes, corners.

**Upload:** big photos are shrunk to fit 960×720 and small ones are never enlarged. The webcam
is turned off while a photo is open. Each frame starts from a fresh copy of the photo, so
effects never stack, and the original file is never changed.

### Processing order (each frame)

1. Read the webcam (mirrored) or copy the uploaded image.
2. Background swap, on the raw picture.
3. Kernel filter, then brightness and contrast (the course sliders).
4. Greyscale switch.
5. Preset.
6. Face stickers, using face positions found in the raw picture.
7. Cody.
8. Frame.
9. Screen-only text (preset name, key hints, countdown). This step is never saved.

---

## Assets

```
assets/
├── frames/        # PNG with transparency, loaded in name order (1_classic.png ...)
├── stickers/      # PNG with transparency; also needs a line in STICKERS in app.py
├── backgrounds/   # JPG, loaded in name order
└── mascot.png     # Cody cut-out
```

- `python make_assets.py` rebuilds all placeholder art. Colours and captions are at the top
  of each section. **It overwrites files with the same name**, so give real art different
  names, or stop running it once real art is in place.
- Frames are 640×480 (4:3) and are stretched to the picture's shape.
- Saved photos and strips go to `output/`, which git ignores.

---

## Fixes and known issues

Applied from `docs/project-review.md`, because the roadmap code depends on them:

- File paths are built from the script's own folder.
- Saved files use timestamps instead of overwriting each other.

Not fixed yet (outside Roadmap Part 1):

- The Gaussian kernels still blur only up and down.
- The Contrast slider still steps in whole numbers.
- Closing the window with **X** doesn't exit cleanly; use `Q`.

Known quirks:

- On pictures that aren't 4:3, the frames are stretched.
- Stickers are placed using face positions in the raw picture. With presets that move
  things around (Pop Art, Mirror), they don't line up with the faces.
- Windows display scaling is switched off for the app's windows, so they stay sharp. On a 125%
  display, the video looks smaller than other apps.

---

## Update history

1. **Webcam and roadmap features (Part 1, Steps 1–5):** live mirrored webcam, 8 presets,
   frame overlay, photo strip, face stickers, background swap, Cody. Includes the new venv
   and MediaPipe models.
2. **Discoverable controls:** sliders for every feature, kept in sync with the keys, plus an
   on-screen key hint.
3. **Window layout fix:** the sliders moved to their own window, and Windows display scaling
   was switched off for the app's windows, so the video is sharp and not pushed off-screen.
4. **Upload:** `U` / `W` switch between an image file and the webcam, a start-up image
   argument, and an image prompt when no webcam is found.
5. **More content:** 17 presets, 7 stickers, 6 backgrounds and 6 frames, plus
   `make_assets.py` to generate all placeholder art.

### Testing

Each update was checked with a scripted test. It ran `app.py` with a fake webcam (a sample
portrait from MediaPipe), a fake file dialog and scripted key presses, saved every screen,
and the screens were checked by eye. The app was then run by hand with the real webcam.
