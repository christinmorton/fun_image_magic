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

## Who calls the service

- **An app's API, in general.** The service is called server to server with the shared
  token, by any app in any framework or language. Don't assume a particular caller, and
  don't plan, build or test integration with a specific app here.
- An earlier version (v0.1.0) was handed to another project, which owns its own copy. It's
  archived as the git tag `image-service-v0.1.0` (commit `e7602fc`). To see what has
  changed since: `git diff image-service-v0.1.0 -- code/image_service`.
- This project has no obligations to that copy. The API routes, the look JSON, catalog
  numbering and settings can all change freely. Don't add backwards compatibility,
  versioning or migration notes for it.
- History, kept as it was: `docs/image-service-v0.1.0-handoff.md` (what was handed over) and
  `docs/api-service-plan.md` (the original plan). Don't keep them in sync with new changes.

## Layout

| Folder | Branch | What it is |
| --- | --- | --- |
| `code/course_project/` | `master` | The original course app (sliders, kernels, greyscale) |
| `code/course_project_extended/` | `photo-booth-extended` | The first CSN photo booth |
| `code/course_project_enhanced/` | `photo-booth-enhanced` | The modular desktop booth: four-slot editor, masks, props, Cody poses |
| `code/image_service/` | `image-service` | **The reusable base.** `core/` (the engine), `api/` (FastAPI), `desktop/` (the OpenCV booth using `core/`), `web/` (the live webcam in the browser: Vite, plain JavaScript) |
| `code/image_service_template/` | `image-service` | **Frozen template** for starting new apps: an exact copy of one release of `image_service` |
| `code/cover_studio/` | `cover-studio` | **Current work.** A desktop app from template 0.2.0 that puts a person into 90s Southern rap cover art, with print files and photo mockups. New work goes in `core/` and `desktop/`; `api/` is unused for now. Plan: `docs/merch-app-plan.md`. A personal challenge project first: selling (`docs/etsy-listings/`) is an optional, low-pressure try, so don't push business plans |
| `docs/` | | Plans, reviews, pricing notes and archived records, in plain English. `project-history.md` (what happened, session by session) and `open-items.md` (what's left) are the place to start; the root `readme.md` maps the rest |
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
- Web webcam (from `web/`): `npm install` once, then `npm run dev` with the API running,
  and open `http://localhost:5173/vanilla/`. `npm test` runs the engine tests. See
  `web/README.md`.
- **Cover Studio** (from `code/cover_studio/`): the same test command. On a new machine or a
  fresh checkout, first fetch the gitignored models with `tools\get_upscale_models.py` and
  `tools\get_mockup_models.py`. Without the upscaling models, about a dozen tests fail with
  "the upscaling model is missing"; that isn't a code problem. Its screens and keys are in
  `code/cover_studio/README.md`.
- Run tests with `discover`: some test files import helpers from others, so running one
  file on its own can fail to import without anything being wrong.

## Things to know

- **Never edit `code/image_service_template/` by hand.** It's a frozen copy for starting new
  apps. Fixes go into `code/image_service/`, and the template only changes when a new
  release is cut from it. See `docs/template-plan.md`.
- **Releases:**
  1. Record each change under "Unreleased" in `code/image_service/CHANGELOG.md`.
  2. To release, turn "Unreleased" into the version, set `SERVICE_VERSION` in
     `api/settings.py`, run the tests, and commit.
  3. Run `py tools\cut_template.py`, then the template's tests.
  4. Commit the template and tag it `image-service-template-v<version>`.

  Only cut a release when the owner asks.
- **Read `docs/desktop-to-api-lessons.md` before putting the live booth behind a network.**
  Turning the desktop app into an API service lost the webcam and the live feel.
- **Keep `code/image_service/` brand-neutral.** Don't add school, company or event names,
  or the name of a particular calling app or framework. The Las Vegas scenes and AI presets
  are kept on purpose.
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
- **Never print a secret.** Don't show tokens or API keys in output, error traces or logs,
  and check `.env` by its names only. A test once printed the service token, and it had to
  be rotated.
- **Personal data and bought files never go into git.** In Cover Studio: `subjects/` (face
  scans, the owner's own photos under made-up names), `designs/`, `exports/`,
  `spending.json`, `mockup_photos/`, the models in `core/models/upscale/` and
  `core/models/mockups/`, and `docs/etsy-listings/mockups/`. Keep `.gitignore` the same on
  every branch: switching to a branch without these rules once left the face scans
  untracked, one `git add -A` away from being committed.
- **The mockup photos** (two bundles bought on Etsy, zipped in `resources/`) are licensed
  for showing the owner's own designs, not for sharing. Never commit them, copy them into
  `code/image_service/` or the template, or ship them with software for others.
- **The album covers in `resources/ghetto_asethetic_merch/` are research only:** never send
  them to an AI model, trace them or train on them. Borrow the style. No real label logos,
  brands or the Parental Advisory mark in designs, and the AI never draws the lettering.
- Use `opencv-contrib-python`, never `opencv-python`; the two conflict.
- Docs are plain-English Markdown in `docs/`. Mark plan steps ✅ when they're done.
- **At the end of a working session,** add a short entry to `docs/project-history.md` and
  update `docs/open-items.md` (remove what's done, add what's new), rather than starting
  a separate summary file.
- **Dates and times are Pacific** (the owner's, and git's). Transcript and memory
  timestamps are in UTC, so convert before writing a date: an evening was once recorded
  as the next day.
- **One commit per feature or unrelated change,** never bundled (the owner's standing
  preference). When one file holds changes for several commits, stage each version
  separately rather than committing them together.
- Commit messages: a short subject in the imperative ("Add …", "Mark …"), and a body that
  says what changed and why when that isn't obvious.
- **Commit messages from PowerShell:** double quotes inside a message break the arguments
  (it once merged two commits). Write the message to a file as UTF-8 without a BOM and use
  `git commit -F <file>`.
