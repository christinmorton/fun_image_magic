# Merch App: Plan

A new app, copied from the image service template, that turns a person (or a crew) into
merch designs in the 1990s Southern rap cover style. Written 2026-11-02.
**Status: draft.** Desktop and local only for now.

> **Current focus (2026-11-08): getting the code working on the desktop.** Selling (stores,
> Etsy, print-on-demand, order flow) is on hold, and so is the web API. The app is
> `code/cover_studio/`; most of the work goes in its `core/` and `desktop/` folders.

---

## The idea

A design comes from four separate processes (see `docs/merch-styles/README.md`):

1. **Style:** a written guide per region: scenes, colours, lettering looks, layouts and
   prompt pieces.
2. **Likeness:** a guided multi-angle webcam scan (look straight, turn left, turn right),
   or a few loaded photos.
3. **Artwork:** the AI puts the person into one of the style's scenes, with no text in it.
   This is the only step that costs money.
4. **Lettering:** the name, title and featuring list, drawn with fonts and graphic effects,
   never by the AI.

The app then lays the lettering over the artwork and **exports** print-ready files for a
**t-shirt, hoodie, poster and phone case**, built so more products can be added later.

It starts with **one style (New Orleans) and one person per design**. Crews and the other
regions come after that works end to end.

## What we're not doing yet

- No API, website, Etsy listings or print-on-demand ordering. Those come once the local
  app makes designs worth selling.
- No custom AI training. We start with reference photos sent to an image model, and only
  train a style model later if prompting isn't consistent enough (see "Later").

---

## Ground rules

| Rule | Why |
| --- | --- |
| **The album covers in `resources/ghetto_asethetic_merch/` are research only.** They are never sent to the AI model, traced or trained on | They're copyrighted art with real artists, label logos and the Parental Advisory mark in them. We borrow the style (lettering, colours, layout), not the artwork |
| **No real logos or marks in designs**: no label logos, car badges, designer logos or the RIAA Parental Advisory mark. Our own parody sticker is fine | Trademarks get merch pulled from Etsy and print-on-demand services |
| **Only scan people who agreed to it.** No celebrities, no minors | People's likeness has legal protection. You're the operator, so this is a checklist you confirm, not a filter |
| **Scans stay local and get deleted** when a design or order is done | Face scans are personal data |
| **AI calls cost money** (about $0.045 per image). The app shows the cost and asks before each paid batch, and tests use fake generators | Same rule as the image service |

---

## Where it lives

- **Folder:** `code/cover_studio/` ("Cover Studio" is a working name), on the branch
  `cover-studio`.
- **Started from:** `code/image_service_template/` at **0.2.0**. Its README records that
  version, as `docs/template-plan.md` asks.
- **Desktop first.** The `api/` folder came along with the copy but stays untouched until
  the API phase. The template's booth features stay too, unused for now.
- **New work goes in new files** (for example `core/scan.py`, `core/styles.py`,
  `core/lettering.py`, `core/products.py`, `desktop/studio.py`). The template's own files
  change as little as possible, so later template fixes still apply cleanly. General fixes
  go into `code/image_service/` first, as usual.
- **Screens:** OpenCV windows for the camera, scan and previews, as the booth does now.
  Tkinter dialogs (already used for "choose a file") handle typing names and titles.
- **Local folders**, all gitignored:

  | Folder | Holds |
  | --- | --- |
  | `subjects/<name>/` | One person's scan: the angle photos and a small JSON file (date, consent ticked) |
  | `designs/<id>/` | One design's layers, its previews and a JSON recipe (style, prompt, subjects, model, cost), so it can be remade |
  | `exports/<id>/` | Print files per product |

---

## Steps

### Phase 0: Set up the app
1. ✅ Create the `cover-studio` branch and copy the template to `code/cover_studio/`
   (2026-11-08), with its output and personal-data folders gitignored.
2. ✅ Give it its own `.venv` and README (template version 0.2.0). The `.env` with the
   Gemini key waits until Phase 4, the first step that needs it.
3. ✅ Run its tests to prove the copy works (72 pass, 2026-11-08).
4. ✅ Add it to the layout table in `CLAUDE.md` and the readme.

**New Orleans goes all the way through first.** Phases 1–5 use only the New Orleans style.
Other regions start once a New Orleans design can be scanned, made, lettered and exported
(see "Later").

### Phase 1: The New Orleans style guide (writing, no code)
5. ✅ Write the first guide, `docs/merch-styles/new-orleans.md` (draft, 2026-11-08), and set
   the format every guide follows in `docs/merch-styles/README.md`.
6. ✅ Pick the first style pack: **New Orleans, 1996–2001**, the best-documented set and the
   core of the look.
7. ✅ Write its **prompt pieces** (in the guide): base, scenes, person, layout space. These are
   what the model sees, never the covers themselves.
8. Settle the guide's open questions as later phases answer them: fonts, sticker wording,
   and whether to keep the War zone scene.

### Phase 2: Lettering (no AI, no cost)
9. ✅ **Effects in code** for the six New Orleans treatments: ice, gold bevel, chrome, scorched
   metal, stone and brush script. Real fonts plus layered effects: gradient fills, bevels,
   outlines, glows, shadows, textures and sparkles (`core/lettering.py`, 2026-11-08; preview
   with `experiments/lettering_sheet.py`).
10. ✅ **Fonts:** only fonts licensed for commercial use (for example Google Fonts under the
    OFL), stored in `core/assets/fonts/` with their licences: Alfa Slab One, Black Ops One,
    Bungee, Permanent Marker (Apache 2.0), Anton and Abril Fatface.
11. ✅ **Text pieces:** the name, a "presents" line, the title, the featuring list and our own
    advisory-style sticker (2026-11-08). Featuring lists shrink to fit and split into even
    lines; a plain serif treatment was added for quieter titles.
12. ✅ **Layout templates:** the guide's four layouts (Hero, Head in the sky, Boss desk, Crew
    row) as positions for each text piece on the square cover, checked over a placeholder
    picture (`core/cover_layout.py`; preview with `experiments/cover_layouts_sheet.py`).
    Titles can arch or recede in perspective.
13. ✅ **A lettering screen** in the desktop app: type the words, pick a treatment and layout,
    see the result, and save it as a transparent PNG at print size (`desktop/studio.py`,
    2026-11-08). Saving writes `designs/<date>-<name>/` with `lettering.png` (3600 px),
    `preview.jpg` and `recipe.json`, and takes 2–5 seconds. Its logic is tested; the
    window itself still needs a first try by hand.
14. **Only if a treatment needs it:** a vector template (SVG) or a hand-made alphabet, as
    described in the style README.

### Phase 3: The guided scan (likeness)
15. **Live guide:** MediaPipe's face landmarker in video mode, with head pose turned on,
    shows on screen which way to turn ("look straight", "turn left", "turn right", maybe
    "chin up").
16. **Auto-capture** each angle when the head is in position *and* the shot is good: one
    face only, face big enough, sharp, well lit, eyes open.
17. **Save** the angles to `subjects/<name>/` with a consent checkbox. A **"load photos"**
    option covers people who can't sit at the webcam.

### Phase 4: Artwork for one person (the only paid step)
18. **Likeness test first:** a small script sends your own three photos with the Inferno
    and Boss office prompts. It asks before running and costs under $1. The results decide
    between one AI request and the collage approach.
19. **Prompt builder:** the guide's base + one scene + the person + clothing and jewellery
    choices + layout space. Always "no text".
20. **Send the subject's angle photos as references** to Nano Banana. It accepts several
    reference images.
21. **Previews:** generate 4 variants at 1K (about $0.18), shown side by side to pick from.
22. **Finals:** remake the picked one at 2K or 4K, or upscale it locally (see step 26).
23. **Cost guard:** show the cost before each batch, keep a running daily total, and reuse
    the template's daily limit.

### Phase 5: Put it together and export
24. **Combine:** the chosen artwork plus the lettering, laid out with one of the layouts.
25. **Keep the design as layers** (artwork, lettering, extras), not one flat image. Each
    product then gets its own layout: a square "cover" for a poster, a cover with
    lettering above and below for a tee, a tall crop for a phone case.
26. **Upscaling:** test the model's 2K and 4K output against OpenCV's own super-resolution
    (`dnn_superres`, part of `opencv-contrib`, which we already use) for print sizes.
27. **Product specs** in one file (`core/products.py`): print area, pixel size, DPI, bleed
    and shape for each product. The exact numbers depend on the print-on-demand provider,
    so they're confirmed when one is chosen. Adding a product means adding one entry.
28. **Mockups:** each design shown on a plain shirt, hoodie, poster and phone-case image, for
    proofs.

### Phase 6: Crews
29. **Scan each member** as their own subject.
30. **Try two approaches and compare:**
    - **All at once:** every member's references in one AI request. This is simpler, but
      likeness may weaken past 3–4 people.
    - **Collage:** generate each person, cut them out with the person segmenter, and arrange
      them in a crew layout. This keeps each likeness strong and is true to the style: the
      original covers were Photoshop collages of people shot separately.
31. **Crew lettering:** a crew name as the title, and members' names in the featuring list.

### Phase 7: The "cheap way" order flow (still local)
32. **An order folder per customer:** subjects, chosen design, proof sheet with mockups,
    final print files, and a checklist (consent, proof approved, files sent, scans deleted).
33. This is what you'd use to fill hand-run Etsy orders before any website exists.

---

## Costs

| What | Rough cost |
| --- | --- |
| 4 preview variants at 1K | about $0.18 |
| One final at 2K / 4K | about $0.05 / $0.11 output, plus input |
| One design, start to finish | under $0.50 if previews aren't redone many times |

Figures are from `docs/ai-api-pricing.md`. Real billing ran about 20% above the list price,
so treat these as low estimates.

## When the desktop version is done

- You can scan yourself, pick a style, and have a tee file and a poster file in about
  10 minutes, for under $1.
- The name lettering looks right with no AI text in the image.
- You'd actually wear the shirt.

## Later (not planned in detail)

- **API and website:** use the AI and final renders as a service, and keep the scan and
  previews next to the user. See `docs/desktop-to-api-lessons.md`.
- **Etsy and print-on-demand** (Printful or Printify) listings and ordering.
- **Getting customers**, store-first or alongside Etsy: see `docs/merch-getting-customers.md`.
- **More style packs**, once New Orleans works end to end: Memphis, Houston and Compton from the research, plus Atlanta,
  Miami, Detroit and New York once their covers are collected (see the TODO in the
  research notes).
- **A style model (LoRA)**, trained only on our own curated designs, if prompts alone
  aren't consistent enough.
- More products: mugs, stickers, tote bags and so on, as new entries in the product specs.

---

## Open questions

| Question | Leaning |
| --- | --- |
| App name and folder name | `merch_studio` as a working name |
| First style pack | New Orleans 1996–2001 |
| Screens: stay with OpenCV + Tkinter, or a fuller desktop UI later? | Start with OpenCV + Tkinter; revisit if it gets awkward |
| Which print-on-demand provider sets the product specs? | Decide before Phase 5 |
| Crews: all at once or collage? | Test both in Phase 6 |
| Brand name and listing words | Open (see the brainstorm: "90s rap cover", "Dirty South", "bling era") |
