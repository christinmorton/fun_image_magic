# Lessons: Turning the Desktop Booth into an API Service

Recorded 2026-11-02, after the image service (v0.1.0, git tag `image-service-v0.1.0`) was
used by a separate web app.

---

## What happened

- **The webcam was lost entirely.**
- **The app stopped feeling fluid.** In the desktop booth, effects respond as you change them.
  Through the web app, applying the different effects to a picture became more difficult.
- **Most features were made to work,** but there was a **noticeable drop in quality**
  compared with the desktop app.
- **Tracking had problems.** The web app's admin panel could only find about one person.
  After a few changes it found people facing the camera, but not people at an angle.
  (More detail to come.)
- The most likely cause is the conversion itself: a live desktop app was turned into a
  request-and-response API service.

---

## Why: how the two versions differ

| | Desktop booth (`desktop/`) | API service (`api/`) |
| --- | --- | --- |
| **Camera** | Reads the webcam itself (`desktop/sources.py`) | Has no camera. The calling app must capture a still and upload it |
| **Feedback** | Redraws every frame as sliders and keys change (about 25–70 ms at 640×480) | Each change is a separate HTTP request: render, encode as PNG or JPEG, download |
| **Face and person tracking** | MediaPipe video mode, following faces from frame to frame | Image mode: each photo is analysed once, when it's uploaded |
| **Live video** | Yes | Not built |
| **Limits** | None | 120 uploads, renders and AI jobs per minute **per client IP**. Every user behind one web server shares that limit |

For the same photo and look, the service's render was **pixel-identical** to the desktop
engine (checked in step 3 of `api-service-plan.md`). So the drop in quality most likely
came from what happens *around* the engine, not from the engine itself. Possible causes
(not checked, because the web app isn't in this repo):

- the browser's camera capture: resolution, and compression before upload
- photos over 2048 px shrunk on upload, plus `max_width` and JPEG output on the way back
- a page that renders on every slider move: it waits for each round trip, and it can reach
  the rate limit

### Tracking

What this repo's tracking does, which may explain the problems (not checked against the
web app):

- **Faces:** MediaPipe's face landmarker is set to find up to **4 faces**
  (`core/tracking.py`). Its face detector is built for selfie-style shots: faces close to
  the camera and turned towards it. It often misses faces that are small, far away or
  turned to the side.
- **Video mode helps; stills don't get that help.** In the desktop booth, a face is found
  once and then *followed* from frame to frame, so it stays tracked as the person turns.
  The service analyses each uploaded still from scratch, so a face at an angle has to be
  detected cold. That's the step the detector is weakest at.
- **People:** the selfie segmenter returns **one mask for everyone**. The service reports
  `person_found` (yes or no), not a count of people, so "how many people" can only come
  from the face count.

---

## Takeaways for the reusable base

- **Keep the interactive loop next to the user.** The camera, live preview and sliders
  belong in the desktop app or in the browser.
- **Use a service only for work that is slow or needs secrets:** AI calls that need API
  keys, and final high-quality renders. This is option C in `api-service-plan.md`.
- **Keep `core/` free of web and window code.** That split worked: the engine moved into
  the service unchanged, and its output was identical.

---

## What we did next (2026-11-02)

The web app now owns its own copy of the service, so this project became free to change.
Three steps followed, all on the `image-service` branch.

### 1. Archived the old image service

- **What:** v0.1.0, exactly as it was handed over: the CSN branding, the Cody cut-outs and
  the original hand-off document.
- **How:** an annotated git tag, `image-service-v0.1.0`, on commit `e7602fc`. It's not a
  separate folder or branch, and its 64 files are all intact in the tag.
- **Getting it back:**

  | To… | Run (from the repo root) |
  | --- | --- |
  | See one file | `git show image-service-v0.1.0:code/image_service/HANDOFF.md` |
  | Switch to it for a while | `git checkout image-service-v0.1.0`, then `git switch image-service` to come back |
  | Have it in a folder beside this one | `git worktree add ..\fun_image_magic_v0.1 image-service-v0.1.0` (it needs its own `.venv`) |
  | See what has changed since | `git diff image-service-v0.1.0 -- code/image_service` |

- The hand-off document moved to `docs/image-service-v0.1.0-handoff.md`, marked as an
  archived record.
- The repo has no remote yet, so the tag exists only on this machine.

### 2. Removed the CSN branding (commit `23acc5b`)

- **One file to rebrand.** `core/brand.py` holds the name, cheer and colours. The
  placeholder art and the "School Colors" preset read from it. To rebrand a copy, edit
  that file and run `tools\make_assets.py`.
- **New placeholder art.** Every frame, sticker, background and prop is drawn from the
  brand, and long text shrinks to fit.
- **A placeholder mascot** in three poses replaces Cody. It's only drawn into an empty
  `core/assets/mascot/` folder, so real mascot art is never overwritten.
- **CSN-only art removed** (it's all kept in the tag): the Cody poses, and the "go coyotes",
  "go CSN" and coyote-ears art. These became a cheer frame, a spotlights background, a
  cheer sign and cat ears.
- **Kept on purpose:** the Las Vegas scenes and AI presets, and the source art in
  `resources/`.

### 3. Made the service caller-neutral (commit `7f38389`)

- The code, settings template and tests now assume a general **app API** as the caller,
  server to server with the shared token. They no longer name a particular framework.
- `docs/api-service-plan.md` is marked as a historical plan.

All 72 tests pass after each step.
