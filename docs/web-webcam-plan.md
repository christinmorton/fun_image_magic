# Web Webcam: Plan

A browser version of the booth's live camera, in `code/image_service/web/`, so any web app
can have the webcam, live effects and face tracking the desktop booth has, and use the image
service only for the finished picture. Written 2026-11-08. **Status: in progress.**

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
1. Write this plan.
2. Set up the Vite project: pages, the dev proxy that adds the token, and the models and
   MediaPipe files served from where they already are.
3. **Camera:** pick a camera and a resolution (the camera's best by default), mirror like a
   selfie camera, and capture a still at full resolution.
4. **Live effects** on the GPU: contrast, brightness, greyscale, the course filters, and
   every preset in `core/filters.py`, approximated where OpenCV does something a shader
   can't do in one pass.
5. **Face tracking** with MediaPipe in video mode (up to 4 faces, as in `core/tracking.py`),
   with the face count and outlines on screen.
6. **Service client:** the catalog, upload, render, compose and AI jobs, through the page's
   own server.
7. **The vanilla page:** controls, a 3-2-1 countdown, the captured photo uploaded once, and
   the service's exact render shown next to it, with how long it took.
8. Engine tests, a production build, and a check in a real browser.

### Phase 2: Live art
9. A route for full-size art (the catalog only has 200 px thumbnails).
10. Face stickers drawn live on the tracked faces, frames and the mascot over the preview.
11. Background swap and focus effects from MediaPipe's person segmenter.

### Phase 3: React and Vue
12. A React hook and component over the same engine.
13. A Vue composable and component over the same engine.

## Open questions

| Question | Leaning |
| --- | --- |
| Ship the engine as an npm package, or copy the folder? | Copy the folder for now, like the template |
| Strips: four captures in the browser, then one compose request? | Yes, in Phase 2 or later |
| The rate limit counts per client IP, and every user behind one server shares it | Note it for apps; change it only if it bites |
