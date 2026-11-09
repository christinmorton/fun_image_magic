# Cover Studio: Session Summary, 2026-11-02 to 2026-11-08

A record of the first long working session on Cover Studio: what was built, what was
decided, and what's still open. Written 2026-11-08 to start the next session from. The
full plan, with every step marked, is `docs/merch-app-plan.md`.

---

## In one paragraph

The session started with a review of the image service and a brainstorm about merch in
the 1990s Southern rap cover style. It ended with **Cover Studio**, a working desktop app
in `code/cover_studio/` (branch `cover-studio`, 75 commits): a guided face scan, AI artwork
in four regional styles (solo or crew), lettering drawn in code with aged finishes, the
artwork placed so the lettering never covers the face, saved designs that can be reopened,
and print files for a poster, t-shirt, hoodie and phone case. **185 tests pass.** Selling
(stores, Etsy, print-on-demand) is on hold on purpose: the focus is the desktop app working
well.

---

## How a cover is made

A design is four separate processes:

| Process | What it does | Where | Costs money? |
| --- | --- | --- | --- |
| **Style** | A region's look: scenes, colours, lettering, layouts, prompt pieces | `docs/merch-styles/`, `core/styles.py` | No |
| **Likeness** | A guided webcam scan: front, then a three-quarter turn each way | `desktop/scan.py`, `core/scan.py` | No |
| **Artwork** | The AI puts the person (or crew) into a scene, with no text | `desktop/artwork.py`, `core/artwork.py` | **Yes**, about $0.18 for 4 previews |
| **Lettering** | Name, title, featuring list and sticker, drawn with fonts and effects | `desktop/studio.py`, `core/lettering.py` | No |

Then the lettering screen puts them together and exports print files.

**To run it** (from `code/cover_studio/`, PowerShell):

| Step | Command |
| --- | --- |
| Scan a person | `.\.venv\Scripts\python.exe desktop\scan.py` |
| Make artwork, then letter it (L) | `.\.venv\Scripts\python.exe desktop\artwork.py` |
| Letter, open saved designs, export | `.\.venv\Scripts\python.exe desktop\studio.py` |
| Tests | `.\.venv\Scripts\python.exe -m unittest discover tests` |
| First time on a new machine | `.\.venv\Scripts\python.exe tools\get_upscale_models.py` |

The keys for each screen are shown in its window and listed in `code/cover_studio/README.md`.

---

## What was done, in order

1. **Reviewed the image service** (`code/image_service/`). Three problems were confirmed by
   running them; **none were fixed** (see "Still open").
2. **Brainstormed and planned** the merch idea: `docs/merch-app-plan.md` and
   `docs/merch-getting-customers.md` (the second one is on hold with selling).
3. **Wrote the New Orleans style guide**, and set the format for all guides
   (`docs/merch-styles/README.md`).
4. **Started Cover Studio** from image service template 0.2.0. The template's other features
   are still there but unused, including `api/`.
5. **Lettering (Phase 2):** six New Orleans treatments (ice, gold, chrome, scorched, stone,
   brush) plus serif; presents line, featuring list, stickers; four layouts (Hero, Head in
   the sky, Boss desk, Crew row); the lettering screen.
   After testing: titles placed by their letters, cut-stone gems instead of beads, and
   **aged finishes** (`print`, `vhs`) per part, three sticker designs, and the Crew row's
   inline "Feat." label.
6. **Guided scan (Phase 3):** auto-capture after a steady one-second hold, side shots at a
   real three-quarter turn (28–55° on the reading), forgiving brief dropouts, the turn
   reading on screen. Calibrated on stock portraits in `resources/sample_profile_pics/`.
7. **Privacy:** the permission box says photos go to Google's Gemini image AI (paid tier:
   not used to improve Google's products). The exact wording and a version are saved with
   each person; nothing is sent without the current version.
8. **Artwork (Phase 4):** a paid likeness test (about $0.18) showed the person stays
   recognisable and three angles beat one. Then the artwork screen: scene, clothes,
   jewellery (always a choice, or the AI adds chains), four previews, a 2K final, a
   spending log with a $2.00 daily limit.
9. **Print files (Phase 5):** a built-in upscaler (FSRCNN: 0.8 s and sharp; EDSR barely
   better and 3.5 minutes), four products at 300 dpi, drawn mockups, export with X.
10. **Fixes from the first real exports:** fire was in every scene (the base prompt asked
    for it); "Ghetto skyline" became **Block at dusk**; the user's own words (**D** details,
    a **Custom** scene) with guardrails; **framing** so the lettering never covers the face
    (automatic fit, arrows to adjust); **opening saved designs** (D) and re-exporting.
11. **Crews (Phase 6):** up to 6 people in one AI request (all three angles for up to 4),
    a Crew line-up scene, the crew row lettering with members as the featuring list.
12. **Three more style guides:** Memphis, Houston, Compton and LA, and their **artwork
    prompts in the app** (R on the artwork screen).

---

## Decisions worth remembering

| Decision | Why |
| --- | --- |
| **The album covers are research only**: never sent to the AI, traced or trained on | Copyright, real artists' likeness, label logos |
| **The AI never draws text**; all lettering is drawn by the app | AI garbles words; names must be spelled right |
| **No real Parental Advisory mark**, label logos, car badges, team or designer logos | Trademarks |
| **Desktop first; selling and the web API on hold** | Get the app working well first |
| **One AI request per cover**, all angles sent | The likeness test showed it works for one person |
| **FSRCNN is the default upscaler** | Sharp and fast; EDSR isn't worth the wait |
| **Jewellery is always an explicit choice** | Without it the AI adds gold chains every time |
| **The prompt's base never mentions fire** | Fire belongs only to the scenes that ask for it |
| **Crew photos are kept in `subjects/_crews/`** | They show several people, so they belong to no single one |
| **One commit per feature** | The owner's standing preference |

---

## Still open

**To test (needs the owner):**
- **Crews with a real second person.** All saved subjects so far are the owner under
  made-up names, so a crew test with them can't show whether different faces blend. If
  they do, build the **collage** approach (each person made separately, cut out and
  arranged).
- **The new regions' artwork:** try Houston *Slab parade* and Compton and LA *Lowrider*
  first.
- **The 2K final:** whether it keeps the preview's look closely enough, compared with the
  local upscaler.
- The live webcam scan has been tried and tuned; keep an eye on the angle ranges.

**To build next (pick when ready):**
- **Stage 2 of the new regions:** their own lettering (blood, slime, typewriter, candy,
  trunk neon, Old English, spray stencil), layouts (wanted poster, cassette insert, front
  page, big letters) and finishes (photocopy, screwed, sun-faded). Listed in each guide.
- The owner's "small prompt tweaks", still to be described.
- Maybe a better name than "Block at dusk".
- **Print sizes and bleed** are common print-on-demand sizes, to confirm with a provider.
- Atlanta, Miami, Detroit and New York need their covers collected before guides.

**Left alone on purpose:**
- **The image service review's three problems are not fixed** in `code/image_service/`, and
  Cover Studio inherited them from the template: "delete everything" doesn't stop queued AI
  jobs (a known, parked issue), the frame cache grows without limit, and a small upload can
  decode to a huge image. All three are in the API, which Cover Studio doesn't use yet. Fix
  them in `image_service` first (see `docs/template-plan.md`) before Cover Studio uses its API.
- Selling: `docs/merch-getting-customers.md` and Phase 7 (the order flow).

---

## Notes for working on it

- **Personal data stays out of git:** `subjects/` (scans and artwork), `designs/`,
  `exports/`, `spending.json` and `.env` are all gitignored. The upscaling models in
  `core/models/upscale/` are too, and are fetched by `tools/get_upscale_models.py`.
- **AI calls cost money:** always ask first. Tests use fake generators. The artwork screen
  asks before every paid batch and keeps to the daily limit.
- **Run the tests with `discover`.** Some test files import helpers from others, so running
  one file as `tests.test_x` fails to import; that isn't a real failure.
- **PowerShell and commit messages:** double quotes inside a `git commit -m` message break
  PowerShell's argument passing (it once merged two commits; they were redone). Use single
  quotes inside messages, or none.
- **Tests that step a fake clock by 0.1 s** need one extra step to reach a whole second
  (adding 0.1 ten times comes to just under 1).
- **Never edit `code/image_service_template/` by hand**; general fixes go into
  `code/image_service/` first.
- `resources/` belongs to the owner: read it, never change or move it.

---

## Where things are

| What | Where |
| --- | --- |
| The plan, with every step marked | `docs/merch-app-plan.md` |
| Style guides (4) | `docs/merch-styles/` |
| The app and its README | `code/cover_studio/` |
| The engine (no window code) | `code/cover_studio/core/` |
| The three screens | `code/cover_studio/desktop/` (`scan.py`, `artwork.py`, `studio.py`) |
| Preview sheets (free, no AI) | `code/cover_studio/experiments/` |
| Research (the owner's) | `resources/ghetto_asethetic_merch/` |
