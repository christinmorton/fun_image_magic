# fun_image_magic: project notes for Claude

These are this project's own instructions. The `CLAUDE.md` in `C:\Users\msdnC\Documents\`
belongs to a WordPress theme project. Its rules (theme-only scope, `bootstrap.php`, Tailwind,
the Postman collection, `TASKS.md`) **do not apply here**.

## What this is

A **brand-neutral photo booth base**, meant to be copied into future apps: filters, presets,
face stickers, background swap, frames, props, a mascot, photo strips and AI styles. It
started as a course project on OpenCV image processing and was first built for a CSN college
event. The CSN version is archived (see below). It's a personal experiment, and the owner is
free to change anything.

## The Laravel hand-off is finished; it's not this project's concern

- A separate Laravel project took its own copy of the image service (v0.1.0, described in
  `code/image_service/HANDOFF.md` on 2026-11-01). **That project owns that version.**
- That version is archived as the git tag `image-service-v0.1.0` (commit `e7602fc`). To see
  what has changed since: `git diff image-service-v0.1.0 -- code/image_service`.
- This project has no obligations to it. The API routes, the look JSON, catalog numbering
  and settings can all change freely. Don't add backwards compatibility, versioning or
  migration notes for it.
- Don't plan, build or test Laravel integration here. Step 4 of `docs/api-service-plan.md`
  belongs to that project.
- `HANDOFF.md` is a historical record of what was handed over. Leave it as it is; don't
  keep it in sync with new changes.

## Layout

| Folder | Branch | What it is |
| --- | --- | --- |
| `code/course_project/` | `master` | The original course app (sliders, kernels, greyscale) |
| `code/course_project_extended/` | `photo-booth-extended` | The first CSN photo booth |
| `code/course_project_enhanced/` | `photo-booth-enhanced` | The modular desktop booth: four-slot editor, masks, props, Cody poses |
| `code/image_service/` | `image-service` | **Current work.** `core/` (the engine), `api/` (FastAPI), `desktop/` (the OpenCV booth using `core/`) |
| `docs/` | | Plans, reviews and pricing notes, in plain English |
| `resources/` | (gitignored) | Source art (Cody PSDs and cut-outs, CSN branding), test images, research |

- Each folder under `code/` has its own `.venv` (Python 3.15.2, Windows).
- `core/` has no web or window code; `api/` and `desktop/` both build on it.

## Commands (PowerShell, from `code/image_service/`)

- Tests: `.\.venv\Scripts\python.exe -m unittest discover tests`. MediaPipe's `W0000`
  warnings are normal.
- API: `.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000`, with docs at
  `/docs`. It needs `IMAGE_SERVICE_TOKEN` in `.env`.
- Desktop booth: `.\.venv\Scripts\python.exe desktop\app.py`
- Placeholder art: `.\.venv\Scripts\python.exe tools\make_assets.py`. It uses the words and
  colours in `core/brand.py`.

## Things to know

- **Read `docs/desktop-to-api-lessons.md` before putting the live booth behind a network.**
  Turning the desktop app into an API service lost the webcam and the live feel.
- **Keep `code/image_service/` brand-neutral.** Don't add school, company or event names.
  The Las Vegas scenes and AI presets are kept on purpose. `HANDOFF.md` keeps its CSN
  history.
- **Rebranding a copy:**
  1. Edit `core/brand.py` (name, cheer, colours).
  2. Run `tools\make_assets.py`.
  3. Replace any file in `core/assets/` with real art of the same name.
  
  The placeholder mascot is only drawn into an empty `core/assets/mascot/`, so real
  mascot art is never overwritten.
- `resources/` belongs to the owner. Don't delete or move anything in it.
- **AI calls cost real money** (about $0.045 per image with Gemini Nano Banana). The tests
  use fake generators. Ask before running `experiments/ai_trial.py` or a real AI job.
- API keys live in `.env`, which git ignores. Only `.env.example`, with the names but no
  values, is committed.
- Use `opencv-contrib-python`, never `opencv-python`; the two conflict.
- Docs are plain-English Markdown in `docs/`. Mark plan steps ✅ when they're done.
- Commit messages: a short subject in the imperative ("Add …", "Mark …"), and a body that
  says what changed and why when that isn't obvious.
