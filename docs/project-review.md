# Project Review: fun_image_magic (course project)

A record of what the course project in `code/course_project/app.py` does, what it is worth,
and the problems found in it. Reviewed 2026-10-31.

---

## What you built

`app.py` is a small **live image editor** built with OpenCV and NumPy. It loads
`resources/test_image.jpg` and opens a window named `app` with four sliders (trackbars):

| Slider | Range | What it does |
| --- | --- | --- |
| **Contrast** | 0–100 (starts at 1) | Multiplies every pixel value |
| **Brightness** | 0–100 (starts at 50) | Adds `brightness - 50` to every pixel, so 50 means no change |
| **Filter** | 0–4 | Picks one of five convolution kernels |
| **Greyscale** | 0–1 | An on/off switch between the colour and grey versions |

The five kernels are:

| Index | Kernel | Effect |
| --- | --- | --- |
| 0 | Identity | No change |
| 1 | Sharpen | Makes edges crisper |
| 2 | Gaussian (3) | Light blur (see the bug below) |
| 3 | Gaussian (5) | Stronger blur (see the bug below) |
| 4 | Box | Even 3×3 average blur |

Keyboard controls:

- `s` saves the current image as `output-N.png`
- `q` quits

### How it works

Every 100 ms the main loop runs these steps:

1. **Read the controls:** get each slider's position with `cv2.getTrackbarPos`.
2. **Filter:** apply the selected kernel with `cv2.filter2D` (convolution).
3. **Adjust:** apply contrast and brightness with `cv2.addWeighted`, which computes
   `new = old × contrast + (brightness - 50)`.
4. **Handle keys:** `cv2.waitKey(100)` waits for a key press and checks for `s` or `q`.
5. **Display:** show the colour or grey result with `cv2.imshow`.

### Ideas the project teaches

- **Images are NumPy arrays.** A colour image is a `height × width × 3` grid of numbers in
  **BGR** order (not RGB), and a grey image is `height × width`.
- **Point operations.** Brightness and contrast change each pixel on its own, using only that
  pixel's value.
- **Convolution.** A kernel is a small grid of weights that slides over the image. Each output
  pixel is a weighted sum of its neighbours. Sharpening, blurring, edge detection and emboss
  are all just different kernels.
- **An interactive loop.** The program reads input, processes the image, shows it and repeats.

---

## Is it worth anything?

**As a finished product: no.** Every phone and photo app already does brightness, contrast,
blur and sharpen, and with a nicer interface.

**As a starting point: yes, for two reasons.**

1. **It already has the basic shape of a photo booth app.** It reads a frame, takes settings
   from controls, processes the image, shows it and saves it on a key press. The student photo
   booth described in `readme.md` is this same loop with a webcam as the input instead of a
   file.
2. **Convolution is a core idea in computer vision.** The 3×3 grids on lines 12–16 are the
   same idea behind edge detection, sketch and emboss effects. Even the neural networks behind
   face tracking and AI filters are built from many stacked convolutions. The course taught a
   basic building block, not a toy trick.

**In short:** it is a solid foundation, and the photo booth can be built on top of it rather
than started over.

---

## Bugs and weak spots

### 1. The Gaussian blurs only blur up and down

**Where:** `app.py` lines 14–15

`cv2.getGaussianKernel(3, 0)` returns a **1D column** (3×1), not a 2D square. Passed to
`filter2D`, it blurs only vertically, so filters 2 and 3 smear the image up and down instead
of blurring it evenly.

**Fix:** multiply the column by its own transpose to get a 2D kernel.

```python
g3 = cv2.getGaussianKernel(3, 0)
g5 = cv2.getGaussianKernel(5, 0)
gaussian_kernel1 = g3 @ g3.T   # 3x3
gaussian_kernel2 = g5 @ g5.T   # 5x5
```

### 2. The Contrast slider is too coarse

**Where:** `app.py` line 31

Trackbars only return whole numbers, so contrast can only be 0, 1, 2, 3 and so on. At 0 the
image is black, 1 is normal, 2 is already strong, and anything above about 3 is washed out.
Most of the slider's 0–100 range is unusable.

**Fix:** use a 0–30 slider and divide by 10, which gives steps of 0.1 from 0.0 to 3.0.

```python
cv2.createTrackbar('Contrast', 'app', 10, 30, dummy)   # 10 means 1.0
...
contrast = cv2.getTrackbarPos('Contrast', 'app') / 10
```

### 3. The image path only works from one folder

**Where:** `app.py` line 22

`'../../resources/test_image.jpg'` is relative to the folder you **run** the script from,
not the folder the script is in. Run it from anywhere else and `cv2.imread` returns `None`
without an error. Line 23 then crashes with an unclear OpenCV message.

**Fix:** build the path from the script's own location, and check that the image loaded.

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IMAGE_PATH = BASE_DIR.parent.parent / 'resources' / 'test_image.jpg'

color_original = cv2.imread(str(IMAGE_PATH))
if color_original is None:
    raise SystemExit(f'Could not load image: {IMAGE_PATH}')
```

### 4. Saved images overwrite each other

**Where:** `app.py` lines 40 and 68–70

`count` restarts at 1 every time the program starts, so the next session's `output-1.png`
replaces the old one. The files are also saved to whatever folder you ran the script from.

**Fix:** use a timestamp in the filename and save to a fixed folder.

```python
from datetime import datetime

OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)
...
filename = OUTPUT_DIR / f'output-{datetime.now():%Y%m%d-%H%M%S}.png'
cv2.imwrite(str(filename), image_to_save)
```

### 5. Closing the window doesn't stop the program

**Where:** the main loop

Only `q` ends the loop. Clicking the window's X button doesn't, so the program keeps running
or crashes on the next `getTrackbarPos` call.

**Fix:** check whether the window is still visible right after `waitKey`.

```python
key = cv2.waitKey(100)
if key == ord('q') or cv2.getWindowProperty('app', cv2.WND_PROP_VISIBLE) < 1:
    break
```

### 6. Extra work on every frame

**Where:** `app.py` lines 50–56

- Both the colour **and** grey versions are filtered and adjusted on every frame, even though
  only one is shown.
- `np.zeros_like(...)` creates a new, unused image-sized array twice per frame, only because
  `addWeighted` needs a second image.

This doesn't matter for one still image. It will matter once the input is live webcam video.

**Fix:** process only the version on screen, and pass the same image twice with a weight of 0.

```python
source = gray_original if grayscale else color_original
modified = cv2.filter2D(source, -1, kernels[kernel_idx])
modified = cv2.addWeighted(modified, contrast, modified, 0, brightness - 50)
```

> **Correction:** an earlier suggestion was to use `cv2.convertScaleAbs` here. Don't: it
> takes the **absolute value** of the result, so negative brightness would turn dark pixels
> bright instead of darker. `addWeighted` as shown above is correct.

### 7. Smaller issues

- **Spelling is inconsistent.** The code uses "Greyscale" for the slider, `grayscale` for the
  variable and `gray_original`/`grey_modified` for the images. Pick one spelling.
- **Typo:** "teh" on line 27.
- **Large photos may not fit on screen.** The image is shown at full size. Resize it for
  display with `cv2.resize` if needed.
- **No `requirements.txt`.** Anyone else running the project has to guess the dependencies
  (`opencv-python`, `numpy`).
- **The comment on line 17** describes an average but doesn't say which kernel it explains
  (it belongs to the box kernel on the line above).

---

## Summary

| Area | Status |
| --- | --- |
| Core idea (load → control → process → show → save) | Works, and is the right base for a photo booth |
| Filters | Sharpen and box blur are correct; both Gaussian blurs are broken |
| Controls | Contrast is too coarse; the others are fine |
| Robustness | Breaks if run from another folder or closed with the X button |
| Saving | Works, but overwrites earlier saves |
| Performance | Fine for a still image; needs trimming before using live video |
