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
