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

- First time only, after making the `.venv`: fetch the upscaling models (about 80 MB,
  Apache 2.0, kept out of git): `.\.venv\Scripts\python.exe tools\get_upscale_models.py`

- Tests: `.\.venv\Scripts\python.exe -m unittest discover tests`. MediaPipe's `W0000`
  warnings are normal.
- **Cover Studio lettering screen** (free, no AI): `.\.venv\Scripts\python.exe desktop\studio.py`.
  Type the words, pick a layout and styles, and press S to save the lettering as a
  print-size transparent PNG (3600 px square) in `designs\`, with a preview and a recipe
  that remakes it. TAB picks a part (all, name, title, presents, featuring, sticker) and A
  cycles its aged finish (clean, print, VHS). K cycles the sticker (none, Hood Classic,
  Street Certified stamp, Warning) and E edits its words. Artwork is moved automatically so
  the name and title don't cover the face; arrows move it, [ ] zoom it, Z fits it again and
  O puts it back as the AI made it (saved with the design). D opens a saved design to change
  or re-export it: moving its picture and pressing X updates it in place, while other changes
  are saved as a new design with S. After S saves a design, X makes
  its print files (about a minute, in the background): a poster (5400 x 7200), t-shirt
  front (4500 x 5400), hoodie front (4200 x 3600) and phone case (1500 x 3000), all 300 dpi
  PNGs, plus `mockups.jpg`, in `exports\<design>\`. The artwork is upscaled and the
  lettering redrawn at each size. The keys are shown at the top of the window.
- **Guided face scan** (free, no AI): `.\.venv\Scripts\python.exe desktop\scan.py`. Asks for
  the person's name and permission, then guides them through three angles with the webcam
  (straight on, a three-quarter turn to their left, then to their right), capturing each
  automatically. S saves them to `subjects\<name>\`; P loads photos instead.
  Someone scanned before the current permission wording can be asked again with
  `desktop\scan.py --reconfirm <their folder>`.
- **Artwork screen** (COSTS MONEY, always asked first): `.\.venv\Scripts\python.exe desktop\artwork.py`.
  Pick a scanned person, or Ctrl/Shift-click up to 6 for a crew (one AI request with
  everyone's photos; a crew's previews are kept in `subjects\_crews\`, and L opens the crew
  row layout with the members as the featuring list). Then S scene (the last one, Custom, asks you to describe your own),
  D your own extra details, C clothes, J jewellery and extras; G makes four
  previews (about $0.18), 1-4 picks one, F remakes it at 2K (about $0.06), and L sends it
  to the lettering screen to finish the cover. Everything is saved in
  `subjects\<name>\artwork\`. Spending is logged in `spending.json`, with a daily limit of
  $2.00 (`COVER_STUDIO_DAILY_LIMIT_USD` in `.env` changes it).
- **Likeness test** (COSTS MONEY with `--run`, about $0.18): sends a subject's photos to
  Gemini with two New Orleans scenes, once with the front photo and once with all angles.
  Without `--run` it's a free dry run that prints what it would send:
  `.\.venv\Scripts\python.exe experiments\likeness_test.py <subject> [--run]`. It refuses to
  send anyone who hasn't agreed to the current wording.
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
