# CSN Image Service: Hand-off

> **Archived record.** This describes the image service as it was handed to another
> project on 2026-11-01 (v0.1.0, git tag `image-service-v0.1.0`). It was moved here from
> `code/image_service/` and isn't kept up to date. The current service is brand-neutral
> and written for any calling app.

A standalone Python service that creates and edits photo-booth images (filters, stickers,
background swaps, frames, props, layouts, AI styles and backgrounds) behind an HTTP API.
It was built to be called by a separate web app (Laravel), which owns users, the UI and
storage. **How that app integrates is up to that app;** this document only states what the
service offers and how it behaves.

Status as of **2026-11-01**: version `0.1.0`, built and tested. Not yet integrated with
Laravel. Source: the `fun_image_magic` repo, branch `image-service`, folder
`code/image_service/`.

---

## Running it

- **Python 3.15.2**, CPU only. Pinned packages (`requirements.txt`): numpy 2.5.4,
  mediapipe 1.2.0, opencv-contrib-python 5.0.0.93 (**not** `opencv-python`, which conflicts),
  google-genai 2.34.0, fastapi 0.162.0, uvicorn 0.54.0, python-multipart 0.0.33.
- **Setup** (from this folder):
  `py -3.15 -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
- **Start:** `.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000`
  - Interactive docs at `/docs`; machine-readable contract at `/openapi.json`.
  - **Run a single process** (uvicorn's default). Photos, jobs and counters live in memory and
    are not shared between workers.
- **Settings** come from `.env` in this folder (copy `.env.example`); real environment
  variables win over `.env`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `IMAGE_SERVICE_TOKEN` | (none) | Shared secret; **required**. Without it every `/v1` route returns 503 |
| `GEMINI_API_KEY` | (none) | Enables AI. Without it the AI routes return 503; everything else works |
| `PHOTO_TTL_SECONDS` | 7200 | How long photos and AI jobs are kept (minimum 60) |
| `AI_DAILY_LIMIT` | 100 | AI images per UTC day, then 429 |
| `RATE_LIMIT_PER_MINUTE` | 120 | Uploads + renders + composes + AI jobs per minute per client IP (0 = off) |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `RECRAFT_KEY` | (none) | Placeholders; **not used** by the code yet |

---

## Authentication

Every `/v1` route needs `Authorization: Bearer <IMAGE_SERVICE_TOKEN>` (compared
timing-safely; a doubled `Bearer Bearer` from the docs page is tolerated). `/health`,
`/docs` and `/openapi.json` are open. Catalog thumbnails are protected too, so a browser
`<img>` cannot load them without going through the caller. There is no CORS; it's designed
for server-to-server calls.

---

## Endpoints

| Method and path | Purpose | Success |
| --- | --- | --- |
| `GET /health` | Liveness and version | 200 `{"status":"ok","version":"0.1.0"}` |
| `GET /v1/catalog` | Every selectable option, with the number to use in a look | 200 JSON |
| `GET /v1/catalog/{kind}/{index}/thumbnail.png` | PNG, up to 200 px, transparency kept. `kind`: stickers, backgrounds, frames, mascots, props | 200 PNG |
| `POST /v1/photos` | Multipart field `image` (JPEG/PNG/BMP/WebP, ≤15 MB; long side shrunk to 2048 px); analysed once (faces, person) | 201 `{photo_id, width, height, faces, person_found, expires_at}` |
| `GET /v1/photos/{id}` | The same info | 200 |
| `DELETE /v1/photos/{id}` | Delete one photo now | 204 |
| `DELETE /v1/photos` | Delete **all** photos and AI jobs (e.g. at the end of an event) | 200 `{deleted_photos, deleted_ai_jobs}` |
| `POST /v1/render` | `{photo_id, look, format?, quality?, max_width?}` → finished image | 200 PNG/JPEG |
| `POST /v1/compose` | `{layout: "strip"\|"grid", slots: [{photo_id\|null, look}] (1–4), format?, quality?, max_width?}` | 200 PNG/JPEG |
| `POST /v1/ai/jobs` | `{photo_id, preset, callback_url?}` → background AI job | 202 job JSON |
| `GET /v1/ai/jobs/{id}` | Job status and progress | 200 job JSON |
| `GET /v1/ai/jobs/{id}/events` | Server-Sent Events: about one `progress` event per second, then `done` or `failed`; closes (10 min maximum) | 200 `text/event-stream` |
| `GET /v1/ai/usage` | `{date, used, limit, remaining, estimated_cost_usd}` for the current UTC day | 200 |

**Image responses:** `format` is `png` (default, lossless) or `jpeg` (`quality` 40–100,
default 90). `max_width` (64–4096) shrinks the result and never enlarges it. Each comes
with `Content-Disposition: inline; filename="render.png"` (or `strip` / `grid`).

**Every response** has `X-Processing-Time-Ms` and `Server-Timing: app;dur=…`. Measured
locally: upload with analysis about 70 ms; render about 25–70 ms at 640×480.

### The look (JSON)

All fields are optional; anything left out keeps its default. **Unknown fields are
rejected.** Catalog numbers are checked against the art, and a 422 message gives the valid
range.

| Field | Range (default) | Meaning |
| --- | --- | --- |
| `contrast` | 0–3 (1.0) | 1.0 = no change |
| `brightness` | 0–100 (50) | 50 = no change |
| `kernel` | 0–6 (0) | Catalog `filters` (none, sharpen, 2 blurs, box blur, emboss, edges) |
| `grayscale` | 0–1 (0) | |
| `preset` | 0–16 (0) | Catalog `presets` (Original, Vintage, Sketch, Cartoon, Pop Art…) |
| `sticker` | −1–6 (−1) | Face-tracked sticker; −1 = off. Needs a detected face |
| `background` | −1–5 (−1) | Background swap; needs a detected person |
| `mascot` | −1–2 (−1) | Cody pose, fixed in the bottom-right corner |
| `frame` | −1–5 (−1) | Branded frame. Note: the default here is **no frame** |
| `focus` | 0–3 (0) | Off, Color Pop, Portrait Blur, Mask Preview; needs a person |
| `props` | list, ≤20 | `{prop: 0–7, x: 0–1, y: 0–1, size: 0.08–1.5}`. Centre and height are fractions of the photo, so they don't depend on resolution. The last item is on top |

The order of operations: background swap → focus → filter, brightness and contrast →
greyscale → preset → stickers (before the preset for Pop Art and Mirror) → Cody → props →
frame. `look_defaults` in the catalog is a complete default look.

Catalog counts today: 17 presets, 7 filters, 4 focus modes, 2 layouts, 7 stickers, 6
backgrounds, 6 frames, 3 Cody poses, 8 props (5 placeholders plus the 3 Cody poses), 9 AI
presets. Art is loaded from `core/assets/` at start-up, in file-name order, so the counts
change when files are added or removed.

---

## AI jobs

- **Model:** Google `gemini-nano-banana-2.1` through `google-genai` (`client.interactions`),
  at 1K output with the closest supported aspect ratio, resized back to the photo's size.
- **Presets** (send the `key`):
  - styles: `comic`, `anime`, `oil_painting`, `superhero`, `vegas_neon`
  - backgrounds: `vegas_strip`, `csn_court`, `outer_space`, `red_rock`
- **The result is a new photo** (`result_photo_id`), rendered and composed like any other.
  Send the *unedited* photo to the AI and add frames and props afterwards, so branding stays
  exact.
- **Backgrounds:** the original person is pasted back over the AI image only if the person
  mask in the AI output overlaps the original by ≥85%. Otherwise the AI image is used as it
  is (the model sometimes reframes). `person_kept` reports which happened.
- **Workers:** 2 jobs run at once; others wait (`queued`). Measured: 13.0–13.5 s per job.
- **Cost:** the code's estimate is **$0.037/image**. Google billing showed about $0.22 for 5
  images, so about **$0.044/image** in practice: the model always "thinks", and reference
  images add input. Budget **$0.045–0.05 per image**. The figure in `/v1/ai/usage` is an
  estimate from that constant (`core/ai.py`), not the real bill.
- **Daily limit:** counted at submit time (failed jobs count too), reset at UTC midnight
  **and on restart**. Use the provider's budget alert as the hard cap.

### Job JSON and progress

```json
{ "job_id": "…", "photo_id": "…", "preset": "vegas_strip", "status": "running",
  "stage": "generating", "stage_label": "The AI is creating the image", "progress": 57,
  "elapsed_seconds": 8.1, "estimated_seconds": 15.5, "eta_seconds": 7.4,
  "result_photo_id": null, "person_kept": null, "error": null,
  "created_at": "…", "started_at": "…", "finished_at": null }
```

- **Status:** `queued` → `running` → `done` | `failed`.
- **Stages and progress:** `queued` 0, `preparing` 5, `generating` 10→90, `checking_person`
  92 (backgrounds only), `saving` 96, `done`/`failed` 100.
- **The provider reports no real progress.** During `generating`, progress moves with time
  against the average of the last 10 AI calls (20 s until one has been timed);
  `estimated_seconds` = that average + 2 s. It never shows more than 90% until it's
  actually finished.

### Webhooks (optional `callback_url`)

- **When:** one POST per stage change (`"event": "progress"`), then one at the end
  (`"done"` or `"failed"`).
- **Body:** the job JSON plus `"event"`.
- **Signature:** `X-Image-Service-Signature: sha256=<hex HMAC-SHA256 of the raw body,
  keyed with IMAGE_SERVICE_TOKEN>`. In PHP:
  `hash_equals('sha256='.hash_hmac('sha256', $rawBody, $token), $header)`.
- **Timeouts:** 3 s for `progress`, 10 s for the final event.
- **Failed deliveries are not retried;** polling still works. Webhooks are sent from the job
  thread in order.

---

## Errors

| Status | When |
| --- | --- |
| 400 | The upload isn't a readable image |
| 401 | Missing or wrong token |
| 404 | Unknown or expired photo or job; unknown thumbnail kind or index |
| 413 | Upload over 15 MB |
| 422 | Invalid look or request (the message names the field and range; compose names the slot, e.g. `slots[1]: …`) |
| 429 | Rate limit (`Retry-After` header), or daily AI limit reached |
| 503 | `IMAGE_SERVICE_TOKEN` not set, or AI not configured |

Error bodies are FastAPI's `{"detail": "…"}`.

---

## Behaviour to plan around

- **Everything is in memory:**
  - Photos and jobs expire after `PHOTO_TTL_SECONDS`; the oldest are dropped beyond 200 photos.
  - **A restart loses all photos and jobs.** The caller should store finished images itself
    and treat a 404 as "upload again".
- **The rate limit is per client IP,** so if every call comes from one Laravel server, the
  limit is shared by all its users.
- **Face and person analysis is serialised behind a lock** (MediaPipe models aren't
  thread-safe). Rendering runs in FastAPI's thread pool.
- **No persistence, no database, no queue system:** AI jobs use an in-process thread pool.
- **The art is placeholder CSN branding,** made by `tools/make_assets.py`, plus Photoshop
  Cody cut-outs in `core/assets/mascot/`. Replacing files keeps the numbering if file names
  and order are kept.

---

## Code map

| Path | Contents |
| --- | --- |
| `core/` | The engine. No web code. `look.py` (`Look`, `render`), `filters.py`, `masks.py`, `overlays.py`, `props.py`, `slots.py`, `tracking.py` (MediaPipe), `asset_library.py`, `ai.py` (presets, generator, person-keeping), `env_file.py`, plus `assets/` and `models/` |
| `api/` | FastAPI: `main.py` (routes), `auth.py`, `catalog.py`, `looks.py` (look schema and validation, encoding), `photos.py` (store), `ai_jobs.py` (jobs, progress, webhooks, daily limit), `limits.py`, `settings.py` |
| `desktop/` | The original OpenCV desktop booth (`app.py`), sharing `core/` |
| `tools/make_assets.py` | Regenerates the placeholder art (never touches Cody) |
| `experiments/ai_trial.py` | A stand-alone Nano Banana trial (costs money) |
| `tests/` | 72 `unittest` tests. AI tests use fake generators, so there are no paid calls. Run: `.\.venv\Scripts\python.exe -m unittest discover tests` |

---

## Not done / known issues

- **No caller integration yet:** no Laravel code exists.
- **Live video** (record and edit in real time) isn't built. Options are in
  `docs/api-service-plan.md` in the source repo.
- **AI cost** in `/v1/ai/usage` is an estimate. The real token usage per request is available
  from the provider's response but isn't recorded yet.
- **Presets, filters and focus modes have no thumbnails** (`thumbnail: null`).
- **Single process only;** state isn't shared or persisted.
- **Unused keys:** the OpenAI, Anthropic and Recraft keys aren't used. Google is the only AI
  provider.
- **A deprecation warning in the tests:** Starlette warns that `httpx` in its test client is
  deprecated in favour of `httpx2`. The tests pass; it only affects the test client.
- **Python 3.15:** the pinned packages were installed and tested on one Windows 11 machine
  only. Check they install on the target host (MediaPipe and OpenCV wheels are the ones most
  likely to differ).

## Background documents (in the source repo's `docs/`)

`api-service-plan.md` (architecture, build log), `ai-image-generation-plan.md` (AI
decisions, trial findings), `ai-costs-overview.md` and `ai-api-pricing.md` (provider
pricing, 2026-11-01), `enhanced-plan.md` (desktop feature history).
