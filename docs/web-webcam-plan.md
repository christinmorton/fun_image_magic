# Web Webcam: Plan

A browser version of the booth's live camera, in `code/image_service/web/`, so any web app
can have the webcam, live effects and face tracking the desktop booth has, and use the image
service only for the finished picture. Written 2026-11-08. **Status: Phases 1 and 2 done.**

---

## Why

When v0.1.0 of the service was used by a web app, the webcam was lost and the booth stopped
feeling live (see `docs/desktop-to-api-lessons.md`). The service has no camera: each change
was a request, a render and a download, and faces were found in single stills, where the
face finder is weakest. The lesson was to **keep the interactive loop next to the user**.

So the browser does what the desktop booth's loop does, and the service does the rest:

| Where | What |
| --- | --- |
| **Browser** (`web/`) | The camera, the live preview with effects, face tracking from frame to frame, the countdown and capture |
| **Service** (`api/`) | The exact final render of the captured photo, strips and grids, and AI (which needs the secret key) |

The live preview is drawn with WebGL shaders written to look like `core/filters.py`. It is
close, not pixel-identical. The finished picture always comes from the service, which is.

## Ground rules

- **The browser never sees `IMAGE_SERVICE_TOKEN`.** The page sends requests to its own
  server, which adds the token and forwards them to the service. In development, Vite's dev
  server does this, reading the token from `image_service/.env` on the server side.
- **No particular calling app or framework is named** in the code or docs, as for the rest
  of the base.
- **One engine, several front ends.** The camera, effects, tracking and service client are
  plain JavaScript modules with no UI (`web/src/engine/`), like `core/`. The vanilla, React
  and Vue versions are thin layers over it.
- **The models aren't copied.** The page loads the same `core/models/face_landmarker.task`
  the Python code uses.
- `node_modules/` and `dist/` are gitignored, so the template cutter leaves them out.

## Layout

```
web/
  index.html           a page linking the versions
  vanilla/             the plain HTML, CSS and JavaScript booth
  react/  vue/         later
  src/engine/          camera.js, effects.js, tracker.js, service.js, booth.js, presets.js
  vite.config.js       the pages, the dev proxy to the service, and serving the models
  tests/               engine tests (node --test, no extra packages)
```

## Steps

### Phase 1: The vanilla booth
1. ✅ Write this plan.
2. ✅ Set up the Vite project (Vite 8.3, MediaPipe tasks-vision 1.2.2): pages, the dev
   proxy that adds the token, and the models and MediaPipe files served from where they
   already are (`vite.config.js`).
3. ✅ **Camera** (`camera.js`): pick a camera and a resolution (the camera's best by
   default), mirror like a selfie camera, and capture a still at full resolution as a 0.95
   JPEG.
4. ✅ **Live effects** on the GPU (`effects.js`): contrast, brightness, greyscale, the
   course filters, and all 17 presets, approximated where OpenCV does something a shader
   can't do in one pass. Effects measured in pixels are scaled to the photo the service
   will keep, so pixel art blocks and comic dots match the final size.
5. ✅ **Face tracking** (`tracker.js`) with MediaPipe in video mode (up to 4 faces, as in
   `core/tracking.py`), on the GPU with a CPU fallback, with the face count and outlines
   on screen. Outlines are left off Pop Art and Mirror, which move the face.
6. ✅ **Service client** (`service.js`): health, catalog, upload, render, compose and AI
   jobs (with the live event stream), through the page's own server.
7. ✅ **The vanilla page** (`vanilla/`): camera, adjust, preset and final-render controls
   from the service's catalog, a countdown, and the captured photo uploaded once with the
   service's exact render beside it. Changing a final-render extra (frame, sticker…)
   renders the latest capture again. `mountBooth()` puts it into any page.
8. ✅ 17 engine tests (`npm test`), 7 Python tests that keep `web/` in step with `core/`
   (`tests/test_web.py`), a production build, and a check in Chrome.

**Checked in Chrome (2026-11-08)**, with a stock portrait as a fake 1280 x 720 camera:
29–30 fps with tracking on the GPU, the face found and followed, and a capture uploaded
and rendered in 50–90 ms. Each preset's preview was compared with the service's render of
the same frame. Most match closely. Watercolor and Neon were redrawn after the first
comparison. Night Vision and X-Ray are still brighter on the service, because OpenCV evens
out the whole picture's histogram; doing the same live would need a histogram pass. A
real webcam still needs a first try by hand.

### Phase 2: Live art
9. ✅ **Full-size art from the service:** `GET /v1/catalog/{kind}/{index}/image.png`. Frames
   take `?width=&height=` and come back fitted by `fit_frame`, so the preview's frame is
   exactly the render's. Sticker catalog items say where they go (`width_factor`,
   `lift_factor`). `fit_frame` now keeps at most 32 sizes, since a page can ask for any.
10. ✅ **Face stickers, the mascot and frames, live** (`art.js`, drawn by `effects.js`):
    stickers are placed from the outer eye corners as `add_face_sticker` does, on every
    tracked face, tilting with the head; before the preset for Pop Art and Mirror, after
    it otherwise. The mascot and frame go on top. One catch: MediaPipe numbers the eye
    corners by which side of the picture they're on, so for the mirrored preview they're
    swapped back, or stickers would turn upside down.
11. ✅ **Background swap and focus, live:** MediaPipe's person segmenter in video mode,
    given a 256 px copy of each frame (the model's own size), only while a background or
    focus effect is on. The mask is firmed up as `refine_mask` starts to (under 0.3 is
    background, over 0.7 the person); its clean-up steps aren't copied, and the GPU's
    smoothing of the small mask stands in for them. Colour pop, portrait blur and the mask
    preview are drawn as in `core/masks.py`.

**Checked in Chrome (2026-11-08)** with the fake camera: 29–31 fps with face tracking and
the person segmenter both on the GPU. With sunglasses, a frame and the mascot, the live
preview and the service's render of the capture look the same. The art pickers show the
catalog's thumbnails. Each capture has "Render with the current look", which renders the
uploaded photo again instead of re-rendering on every change.

### Phase 3: React and Vue
12. A React hook and component over the same engine.
13. A Vue composable and component over the same engine.

## Open questions

| Question | Leaning |
| --- | --- |
| Ship the engine as an npm package, or copy the folder? | Copy the folder for now, like the template |
| Strips: four captures in the browser, then one compose request? | Yes, in Phase 2 or later |
| The rate limit counts per client IP, and every user behind one server shares it | Note it for apps; change it only if it bites |
