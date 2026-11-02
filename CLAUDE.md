# fun_image_magic: project notes for Claude

These are this project's own instructions. The `CLAUDE.md` in `C:\Users\msdnC\Documents\`
belongs to a WordPress theme project. Its rules (theme-only scope, `bootstrap.php`, Tailwind,
the Postman collection, `TASKS.md`) **do not apply here**.

## What this is

A photo booth for a CSN college event, featuring Cody the mascot: filters, presets, face stickers,
background swap, frames, props, photo strips and AI styles. It started as a course project
on OpenCV image processing. It's a personal experiment, and the owner is free to change
anything.

## The Laravel hand-off is finished; it's not this project's concern

- A separate Laravel project took its own copy of the image service (v0.1.0, described in
  `code/image_service/HANDOFF.md` on 2026-11-01). **That project owns that version.**
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
- Placeholder art: `.\.venv\Scripts\python.exe tools\make_assets.py`. It never touches
  Cody's poses.

## Things to know

- **AI calls cost real money** (about $0.045 per image with Gemini Nano Banana). The tests
  use fake generators. Ask before running `experiments/ai_trial.py` or a real AI job.
- API keys live in `.env`, which git ignores. Only `.env.example`, with the names but no
  values, is committed.
- Use `opencv-contrib-python`, never `opencv-python`; the two conflict.
- Docs are plain-English Markdown in `docs/`. Mark plan steps ✅ when they're done.
- Commit messages: a short subject in the imperative ("Add …", "Mark …"), and a body that
  says what changed and why when that isn't obvious.
