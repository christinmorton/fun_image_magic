# Cover Studio

A desktop app that puts a person into 1990s Southern rap album-cover art: their face from a
guided webcam scan, a scene in the style, and their name in chrome, gold or diamond
lettering. "Cover Studio" is a working name.

- **Started from:** the image service template **0.2.0** (`code/image_service_template/`,
  git tag `image-service-template-v0.2.0`), copied 2026-11-08.
- **Plan:** `docs/merch-app-plan.md`. Style guides: `docs/merch-styles/`.
- **Current focus:** getting the code working on the desktop. Selling, the web API and
  online stores are on hold.

## What's used for now

| Folder | Status |
| --- | --- |
| `core/` | **Where the new work goes:** lettering, the scan, styles, artwork, layouts |
| `desktop/` | **Where the new screens go** |
| `api/` | Came with the template, untouched and not used yet |
| `tools/`, `experiments/` | From the template, as they were |

The template's booth features (presets, stickers, frames, props) are still here and still
work, but aren't part of this app's focus.

## Commands (PowerShell, from `code/cover_studio/`)

- Tests: `.\.venv\Scripts\python.exe -m unittest discover tests`. MediaPipe's `W0000`
  warnings are normal.
- Desktop booth (from the template): `.\.venv\Scripts\python.exe desktop\app.py`
- Lettering preview sheet (free, no AI):
  `.\.venv\Scripts\python.exe experiments\lettering_sheet.py "YOUR NAME"`, saved to
  `experiments\output\lettering_sheet.png`
- Cover layouts preview (free, no AI): every layout's lettering over a placeholder picture:
  `.\.venv\Scripts\python.exe experiments\cover_layouts_sheet.py "YOUR NAME"`, saved to
  `experiments\output\cover_layouts_sheet.png`

## Rules

- **The album covers in `resources/ghetto_asethetic_merch/` are research only.** They're
  never sent to an AI model, traced or trained on.
- **The AI never draws text.** All lettering is drawn by the app.
- **AI calls cost money.** Ask before running anything that calls a real model; tests use
  fake generators.
- **Fixes that apply to every app** go into `code/image_service/` first (see
  `docs/template-plan.md`).
