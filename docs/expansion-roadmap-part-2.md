# Expansion Roadmap, Part 2: layers, selection and masks

Part 1 (`docs/expansion-roadmap.md`) builds the photo booth. Part 2 adds creative tools:
**layers**, **stacking order**, **object selection** and **masking**. The goal is not to
rebuild a full photo editor. It's a small set of tools that let students arrange stickers,
cut themselves out and decorate their photos.

These tools are also the foundation for two later directions: **AR-style stickers** that
follow a face, and **AI image generation**, which uses masks as its input.

| Step | Feature | Builds on |
| --- | --- | --- |
| 7 | Layers | Part 1, Step 3 (overlay) |
| 8 | Stacking order | Step 7 |
| 9 | Object selection (mouse) | Steps 7–8 |
| 10 | Masking | Step 7 |
| 11 | Asset library | Steps 7–10 |
| 12 | Anchored layers (AR-style) | Part 1, Step 5 + Step 7 |
| 13 | AI image generation (later) | Step 10 |

## Step 7: Layers

The Part 1 overlay is already one layer. Generalise it: a **layer** is a transparent image
(BGRA, with an alpha channel) plus its position, size and opacity on the canvas.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(eq=False)   # eq=False: compare layers by identity, not by their pixel arrays
class Layer:
    name: str
    image: np.ndarray                    # BGRA
    x: int = 0                           # top-left corner on the canvas
    y: int = 0
    scale: float = 1.0
    opacity: float = 1.0
    visible: bool = True
    mask: Optional[np.ndarray] = None    # grey, same size as image (Step 10)
```

Drawing one layer onto the canvas, clipped at the edges so it can hang partly off-screen:

```python
def draw_layer(canvas, layer):
    if not layer.visible:
        return
    rgb = layer.image[..., :3]
    alpha = layer.image[..., 3] / 255.0 * layer.opacity
    if layer.mask is not None:
        alpha = alpha * (layer.mask / 255.0)
    if layer.scale != 1.0:
        rgb = cv2.resize(rgb, None, fx=layer.scale, fy=layer.scale)
        alpha = cv2.resize(alpha, None, fx=layer.scale, fy=layer.scale)

    h, w = alpha.shape
    H, W = canvas.shape[:2]
    x0, y0 = max(layer.x, 0), max(layer.y, 0)
    x1, y1 = min(layer.x + w, W), min(layer.y + h, H)
    if x0 >= x1 or y0 >= y1:
        return                           # entirely off the canvas
    sx, sy = x0 - layer.x, y0 - layer.y
    a = alpha[sy:sy + (y1 - y0), sx:sx + (x1 - x0), None]
    src = rgb[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    canvas[y0:y1, x0:x1] = (src * a + canvas[y0:y1, x0:x1] * (1 - a)).astype(np.uint8)

def composite(background, layers):
    canvas = background.copy()
    for layer in layers:                 # first in the list = bottom of the stack
        draw_layer(canvas, layer)
    return canvas
```

The webcam frame (after its preset filter) is the background, and the layers go on top.
Rotation can be added later with `cv2.getRotationMatrix2D` and `cv2.warpAffine`.

## Step 8: Stacking order

The **order of the list is the stacking order**: index 0 is drawn first (at the bottom) and
the last item is drawn last (on top). Moving a layer up or down is a list swap.

```python
def bring_forward(layers, layer):
    i = layers.index(layer)
    if i < len(layers) - 1:
        layers[i], layers[i + 1] = layers[i + 1], layers[i]

# send_backward is the same, swapping with i - 1 when i > 0

def bring_to_front(layers, layer):
    layers.append(layers.pop(layers.index(layer)))
```

Suggested keys: `]` forward, `[` backward, `}` to front, `h` hide or show, `x` delete.

## Step 9: Object selection

**Click to select** the top layer under the mouse, then **drag to move** it. Checking the
alpha channel (not just the rectangle) means clicking a transparent gap, like the middle of a
ring sticker, selects whatever is underneath.

```python
def layer_at(layers, px, py):
    for layer in reversed(layers):       # check the top layer first
        lx = int((px - layer.x) // layer.scale)
        ly = int((py - layer.y) // layer.scale)
        h, w = layer.image.shape[:2]
        if layer.visible and 0 <= lx < w and 0 <= ly < h and layer.image[ly, lx, 3] > 0:
            return layer
    return None

state = {'selected': None, 'drag_from': None}

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        state['selected'] = layer_at(layers, x, y)
        state['drag_from'] = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_LBUTTON:
        layer = state['selected']
        if layer is not None:
            layer.x += x - state['drag_from'][0]
            layer.y += y - state['drag_from'][1]
            state['drag_from'] = (x, y)

cv2.setMouseCallback('app', on_mouse)
```

Draw a rectangle around the selected layer with `cv2.rectangle` on the **displayed** frame
only, so the box doesn't end up in saved photos. Use `+` and `-` to change its `scale`.

## Step 10: Masking

A **mask** is a grey image where 255 means "keep", 0 means "hide" and values in between are
partly see-through. Masks are what make selection and cut-outs possible. Ways to make one:

```python
# From a shape: a filled circle (-1 = filled)
mask = np.zeros(img.shape[:2], np.uint8)
cv2.circle(mask, (w // 2, h // 2), min(h, w) // 2, 255, -1)

# From a colour: remove a green backdrop, using HSV colour space
green = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), (35, 80, 80), (85, 255, 255))
mask = 255 - green                       # keep everything that is NOT green

# Feathering: soften any mask's edges so cut-outs don't look pasted on
mask = cv2.GaussianBlur(mask, (31, 31), 0)
```

**By painting:** a mouse callback that draws white circles on the mask with the left button
and black circles with the right button, like a simple brush and eraser.

**By drawing a box around an object.** OpenCV's GrabCut separates an object from its
background given a rough rectangle. It takes about a second, so use it on a captured photo,
not on live video.

```python
def grabcut_select(img):
    rect = cv2.selectROI('app', img)     # the user drags a box, then presses Enter
    mask = np.zeros(img.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    keep = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    return np.where(keep, 255, 0).astype(np.uint8)
```

**From a person segmenter:** the MediaPipe selfie mask from Part 1, Step 5 is a mask too.

### Two things masks make possible

**Turning a selection into a new layer** (cut yourself out as a sticker):

```python
def cutout_layer(img, mask, name):
    bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    bgra[..., 3] = mask
    x, y, w, h = cv2.boundingRect(mask)  # the smallest box around the kept pixels
    return Layer(name, bgra[y:y + h, x:x + w], x=x, y=y)
```

**Applying a filter to one region only.** "Colour pop" is a popular example: the student
stays in colour and the background turns grey.

```python
a = (mask / 255.0)[..., None]
grey = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
result = (img * a + grey * (1 - a)).astype(np.uint8)
```

## Step 11: Asset library

Put special images in folders and load them all at start-up, so new art can be added without
changing code.

- Use `assets/stickers/` (mascot, hats, glasses, speech bubbles as transparent PNGs),
  `assets/frames/` (Part 1, Step 3 overlays) and `assets/backgrounds/` (background swap).
- Press a key to cycle through stickers, and another to add the current one as a new layer.
- Save a "scene" (each layer's file name, position, scale and order) to a JSON file, so a
  good arrangement can be reused as a ready-made template at the event.
- Make sure any art used is yours, made for the event or licensed for it, especially the
  school's mascot and logo.

## Step 12: Anchored layers (AR-style)

This is where layers meet augmented reality. An **anchored layer** has its position updated
every frame from face tracking (Part 1, Step 5) instead of staying where it was dropped.

- Add an `anchor` field to `Layer` (for example `'forehead'` or `'nose'`) and an offset.
- Each frame, set `x` and `y` from that face landmark's position.
- Set `scale` from the distance between the eyes, so the sticker grows as a student gets
  closer to the camera.
- Set rotation from the angle of the line between the eyes, so it tilts with the head.

**An honest assessment:** anchored 2D layers give most of the fun of face filters like phone
camera lenses, and they reuse everything in this document. True 3D AR, such as a 3D mascot
that walks around the room or appears in students' own phone cameras, is a different set of
tools (3D engines and phone AR frameworks, not OpenCV). Decide on that after the 2D version
has been used at an event. You may find it isn't needed.

## Step 13: AI image generation (later)

The general term is **generative AI image generation**. These are the specific kinds that fit
a photo booth:

| Name | What it does | Booth example |
| --- | --- | --- |
| **Text-to-image** | Makes a new image from a written prompt | A custom background scene |
| **Image-to-image** | Restyles an existing photo, guided by a prompt | "Make me an anime character" |
| **Inpainting** | Regenerates only the **masked** part of a photo | Replace the background, add armour |
| **Outpainting** | Extends a photo beyond its edges | Widen a selfie into a poster |
| **Style transfer** | Applies the look of an art style | Oil painting, comic book |

**Why Step 10 matters here:** inpainting takes a photo **and a mask**. The selection and
masking tools above become the way students choose what the AI changes.

**Two ways to run it:**

- **A hosted API** (a cloud image-generation service): no special hardware and quick to set
  up, but there's a cost per image and students' photos leave your computer.
- **Open models run locally** (such as the Stable Diffusion family, via Hugging Face's
  `diffusers` library): photos stay on your machine, but it needs a strong graphics card.

**Plan for these at an event:**

- **Preset styles, not free-text prompts,** as `readme.md` recommends. Students will test
  free text with inappropriate requests.
- **A wait** of several seconds per image, so show a "generating..." screen.
- **Consent:** put up a sign at the booth, and decide when photos are deleted.
- **A fallback:** keep the non-AI booth working in case the service is slow or offline.
