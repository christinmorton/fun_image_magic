# Image Service API: Plan

Plan for turning the photo booth into a **standalone Python image service** that a Laravel
web app calls. Written 2026-11-01 to start a later session. **No code yet.**

Starting point: `code/course_project_enhanced/` (branch `photo-booth-enhanced`), a finished
desktop app: presets, stickers, background swap, masks and focus, Cody poses, scene props,
the four-slot editor, start-over reset, and an AI trial with Google Nano Banana 2.1.

---

## Goals

1. **One job:** create and edit images (and later video) from photos and webcam captures,
   using the features built in the desktop app.
2. **Triggered by Laravel:** the web app sends a request, and the service responds with the
   processed content.
3. **The core stays independent:** the image "engine" doesn't depend on Laravel, FastAPI or
   any web code. Laravel decides *how it talks* to the service (the API contract), not how
   the engine works. The engine can keep serving the desktop app too.
4. **Simple to run:** Docker is optional, not required.

---

## Architecture: three layers

```text
image_service/
├── core/        the engine: no web code, no windows
│   ├── filters.py  masks.py  overlays.py  props.py  look.py  slots.py
│   ├── tracking.py  asset_library.py  ai.py (Nano Banana, from the trial)
│   └── assets/  models/
├── api/         a thin FastAPI layer: routes, request/response schemas, auth, jobs
└── desktop/     the current OpenCV app (app.py), still working, using core/
```

- **`core/`** is today's modules, almost unchanged. The module split already separated them
  from the windows and keys. It gets its own tests (today's `tests/`).
- **`api/`** only translates HTTP into calls to `core/` and back. If Laravel's needs change,
  only this layer changes.
- **`desktop/`** keeps the local app for testing and offline events.

**Why FastAPI rather than Django:** the service has one focused job and no database of its
own (Laravel already has one). FastAPI is lighter, handles file uploads simply, runs async,
and **generates OpenAPI docs automatically**: a machine-readable contract that Laravel can
code against.

---

## Who owns what

| Concern | Laravel app | Image service |
| --- | --- | --- |
| Users, accounts, sessions | ✔ | |
| The user interface (browser), webcam capture | ✔ | |
| Each user's slots and looks (stored as JSON) | ✔ in its database | |
| "Start over" (reset) | ✔ deletes the session's slots | (nothing to do) |
| Storing finished images long-term | ✔ (its storage / S3) | |
| Turning a photo + look into an image | | ✔ |
| Face and person analysis (MediaPipe) | | ✔ |
| Calling the AI provider; the Gemini key | | ✔ (key in its `.env`) |
| The catalog of presets, stickers, frames, props | | ✔ |

The service is **stateless**, apart from a short-lived cache of uploaded photos and their
analysis (deleted after a set time, e.g. 2 hours). That makes it easy to restart, scale and
reset.

---

## API sketch (version 1)

All routes under `/v1`. Every request carries a shared secret from Laravel
(`Authorization: Bearer <token>`), and the service isn't exposed publicly.

| Route | Purpose | Request | Response |
| --- | --- | --- | --- |
| `GET /health` | Is the service up? | none | `{"status": "ok"}` |
| `GET /v1/catalog` | What can be used | none | presets, stickers, backgrounds, frames, focus modes, props (names and thumbnail URLs) |
| `POST /v1/photos` | Upload a photo once; analyse faces and person | image file | `{"photo_id", "width", "height", "faces": n, "expires_at"}` |
| `POST /v1/render` | Photo + look → finished image | `{"photo_id", "look", "format": "png"\|"jpeg", "max_width"}` | the image (or a URL) |
| `POST /v1/compose` | Up to 4 photos + looks → strip or grid | `{"layout": "strip"\|"grid", "slots": [{"photo_id", "look"}…]}` | the image |
| `POST /v1/ai/jobs` | Start an AI style or background | `{"photo_id", "preset", "callback_url"?}` | `{"job_id", "status": "queued"}` |
| `GET /v1/ai/jobs/{id}` | Check an AI job | none | `{"status", "result_photo_id"?, "error"?}` |
| `DELETE /v1/photos/{id}` | Delete a photo now (privacy) | none | `204` |

**A look is JSON.** Today's `Look` dataclass becomes the request schema:

```json
{ "contrast": 1.0, "brightness": 50, "kernel": 0, "grayscale": 0, "preset": 4,
  "sticker": -1, "background": 2, "mascot": -1, "frame": 0, "focus": 1,
  "props": [ { "prop": 0, "x": 0.78, "y": 0.65, "size": 0.45 } ] }
```

Prop positions are already **fractions of the photo**, so the browser can let users drag
props at any screen size and send the same numbers.

**AI results become new photos:** an AI job returns a `result_photo_id`, which can then be
rendered with any look. Frames and props go on top, so the branding stays exact (a lesson
from the trial).

---

## Laravel integration

1. The browser captures a webcam photo (or the user uploads one) and sends it to Laravel.
2. Laravel forwards it: `POST /v1/photos` (server to server, with the shared secret).
3. When the user picks options, Laravel saves the look as JSON and calls `POST /v1/render`.
   It stores the result, or streams it back to the browser.
4. AI: Laravel calls `POST /v1/ai/jobs`, then either polls `GET /v1/ai/jobs/{id}` from a
   queued job or receives a **webhook** at `callback_url` when it's done.
5. Laravel's Http client handles all of this, for example
   `Http::withToken($token)->attach('image', $file)->post($url.'/v1/photos')`.

Laravel stays in charge of the experience. The service only answers clearly defined
requests, documented by its OpenAPI page at `/docs`.

---

## Live video (a later task)

Goal: users **record live video** in the web app and see these effects **in real time**.
Options, from simplest to most ambitious:

| Option | How | Pros | Cons |
| --- | --- | --- | --- |
| **A. Process a recorded clip** | The browser records (MediaRecorder) and uploads; the service runs `render` on every frame (video-mode tracking) and returns an MP4 (ffmpeg) | Reuses the engine as it is; simple | Not live; waits for processing |
| **B. Live through the service (WebRTC)** | The browser streams the webcam to the service (`aiortc`); each frame goes through the Python pipeline and streams back; record the result | Reuses Python effects; true live preview | Server CPU per active user; more networking work |
| **C. Live in the browser** | Re-create the effects in the browser (canvas/WebGL plus MediaPipe's JavaScript version); the service handles AI and final renders | Fastest preview; no server load per frame | Effects must be rewritten in JavaScript or shaders |
| **D. Prototype in the desktop app first** | Add record and play back to `course_project_enhanced` (OpenCV `VideoWriter`); try effects on video locally | Quick way to learn what works on video | Desktop only |

Suggested path: **D** (if you want to try it here first) → **A** in the service → **B**
for a live preview. **C** later if many users need live video at once. Decide once photos
work end to end.

---

## Running it (Docker optional)

- **Without Docker (simplest):** a Python venv on the server, `pip install -r
  requirements.txt`, and run `uvicorn api.main:app` as a background service (systemd on
  Linux, or a Windows service). Put it behind the same web server as Laravel, or on a
  private port.
- **With Docker (optional, later):** one image with Python, OpenCV, MediaPipe, the models and
  assets, useful if hosting needs it. The code doesn't change.
- **Either way:** pin versions (`requirements.txt`), keep the models and assets with the code,
  and keep keys in `.env`.

---

## Build order (proposed)

1. ✅ **New project folder** `code/image_service/` (done 2026-11-01, branch
   `image-service`): the engine is in `core/` (with `assets/` and `models/`), the desktop app
   in `desktop/`, plus `tools/`, `experiments/`, `tests/` and an empty `api/`. It has its own
   `.venv` from `requirements.txt`. No behaviour change: 26 tests pass, and 102 screens and
   saved files from all seven scripted scenarios are pixel-identical to
   `course_project_enhanced`.
2. ✅ **FastAPI skeleton** (done 2026-11-01): `/health`; `/v1/catalog` with the look number,
   name and thumbnail URL of every option; `/v1/catalog/{kind}/{index}/thumbnail.png`;
   Bearer-token auth (`IMAGE_SERVICE_TOKEN`; without one, `/v1` refuses with 503); `/docs`.
   34 tests pass, and a real uvicorn server was checked over HTTP. Start it with
   `.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000`.
3. ✅ **Photos and rendering** (done 2026-11-01):
   - `POST /v1/photos`: up to 15 MB, long side shrunk to 2048 px, analysed once.
   - `GET` and `DELETE /v1/photos/{id}`.
   - An in-memory store with expiry (`PHOTO_TTL_SECONDS`, default 2 h; max 200 photos).
   - `POST /v1/render`: the look is checked against the catalog; PNG or JPEG, optional
     `max_width`.
   - `POST /v1/compose`: strip or grid, up to 4 slots, `null` for empty.
   - 47 tests pass. On a real server with a real portrait: upload 0.07 s, render 0.07 s,
     and the result is pixel-identical to the desktop engine.
4. **Laravel test call:** a minimal Laravel route that uploads a photo and shows the
   rendered result.
5. ✅ **AI jobs** (done 2026-11-01):
   - `core/ai.py`: nine presets (5 styles, 4 backgrounds), Nano Banana 2.1, and backgrounds
     that put the original person back only if their mask overlaps by 85% or more.
   - `POST /v1/ai/jobs` (202, 2 worker threads) and `GET /v1/ai/jobs/{id}`; the result is a
     new photo to render with any look.
   - An optional signed webhook (`X-Image-Service-Signature: sha256=<HMAC of the body with
     the token>`).
   - `AI_DAILY_LIMIT` (default 100/day, then 429), and `GET /v1/ai/usage` with an estimated
     cost. Without `GEMINI_API_KEY`, 503.
   - **Progress:** stages (`queued` 0% → `preparing` 5% → `generating` 10–90%, moving with
     time against the average of recent AI calls → `checking_person` 92% → `saving` 96% →
     `done` 100%), shown in three ways:
     - fields on the job: `progress`, `eta_seconds`, `estimated_seconds`
     - a webhook for every stage
     - an SSE stream, `GET /v1/ai/jobs/{id}/events`
   - Every response has `X-Processing-Time-Ms` / `Server-Timing`.
   - **Real end-to-end check** (2026-11-01, about $0.07):
     - comic finished in 13.5 s; the Vegas background in 13.0 s with the person kept
     - 9 webhooks, all with valid signatures
     - renders took about 30 ms
     - the estimate improved from 22 s to 15.5 s after one job
6. ✅ **Privacy and limits** (done 2026-11-01):
   - Photos only in memory, expiring (`PHOTO_TTL_SECONDS`); `DELETE /v1/photos/{id}`.
   - `DELETE /v1/photos` wipes every photo and AI job (end of an event).
   - 15 MB upload cap.
   - `RATE_LIMIT_PER_MINUTE` (default 120) on uploads, renders, layouts and AI jobs: 429
     with `Retry-After`.
   - 67 tests pass.
7. **Video:** option A (recorded clips), then decide on B or C.

## Open decisions

| Question | Leaning |
| --- | --- |
| Where does the service run (same server as Laravel, or separate)? | Same server first, private port |
| Return images directly, or a URL? | Directly at first; URLs if Laravel stores them |
| Polling or webhooks for AI jobs? | Webhooks, with polling as a fallback |
| Live video in this desktop version first? | Your call: option D above |
| Python version for the server | Match what the host supports; pin it |
