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

**After the first hand test (2026-11-08):**
- ✅ **Titles are placed by their letters**, after any arch or perspective, so short titles
  sit centred inside their box. Arches are gentler on short words.
- ✅ **Ice looks like real stones:** brilliant-cut stones with bright and dark facets,
  small stones in the gaps, rare rainbow flashes, glints and bloom, instead of round beads.
- ✅ **Aged finishes** (`core/finish.py`): `print` (an early-Photoshop JPEG, printed and
  scanned: soft, blocky, colour fringes, faded warm blacks, grain, dust) and `vhs` (plus
  smeared colour, scan lines, wobble and tracking noise). The lettering screen starts on
  `print` and the A key cycles them; saved files and recipes include the finish. Once there
  is artwork, the same finish should age the whole cover together.
- ✅ **A finish for each part:** the name, title, presents line, featuring list and sticker
  can each be clean, print or VHS (Tab picks the part, A changes it), measured against the
  whole cover so grain and scan lines match. Recipes record each part's finish.
- ✅ **Sticker choices:** none, Hood Classic (black badge, gold border), Street Certified
  (red rubber stamp) or Warning (yellow, hazard stripes), each with editable words. The
  real Parental Advisory mark stays out: it's the RIAA's trademark. Also fixed: sticker
  borders only showed at the corners.

### Phase 3: The guided scan (likeness)
15. ✅ **Live guide:** MediaPipe's face landmarker in video mode shows on screen which way to
    turn ("look straight", "turn your head slowly to your left", then right), with an
    arrow, a face oval and a ring that fills while the pose is held (`core/scan.py`,
    `desktop/scan.py`, 2026-11-08). The head turn is measured from where the nose tip sits
    between the sides of the face.
16. ✅ **Auto-capture** each angle when the head is in position *and* the shot is good: one
    face only, face big enough (by height, which doesn't change as the head turns),
    centred, well lit, sharp, eyes open, and the chin level with the front shot. The pose
    must be held steady (within 4°) for a second, so a side shot is taken where the head
    stops, not while it's still turning; the sharpest frame of the hold is kept, then
    "Got it!" shows for a moment before the next angle.
17. ✅ **Save** the angles to `subjects/<name>/` (`core/subjects.py`) only after a permission
    box is ticked (agreed, not under 18, not a public figure). A **"load photos"** option
    sorts photos into front, left and right by how the head is turned.

**Checked on 13 stock portraits** (in `resources/sample_profile_pics/`, not committed):
turns read the right way, and front-facing faces read within ±5°. The face finder can't
find a full side profile, so the side shots are three-quarter turns (20–55°), which also
show the AI more of the face. The scan's logic is tested with made-up faces; the live
webcam screen still needs a first try by hand, and its angles may need tuning then.

✅ **Hair no longer reads as a dark face (2026-11-09).** A person with a fringe down to her
eyes and hair over the sides of her face kept getting "too dark" until a lamp was turned
on: the light was measured over the whole face box, hair included. It's now measured on
the middle of the face only (between the cheeks, from below the eyes to the upper lip),
which hair rarely covers. Checked on the stock portraits: the box sits on the nose and
cheeks, clear of hair and glasses, and reads a little brighter than the whole box did.

### Phase 4: Artwork for one person (the only paid step)
18. ✅ **Likeness test first:** a small script sends your own three photos with the Inferno
    and Boss office prompts. It asks before running and costs under $1. The results decide
    between one AI request and the collage approach.
    **Result (2026-11-08, one subject, 4 images, about $0.18, 13–26 s each):**
    - The person stayed recognisable in all four; the **three-angle** versions looked closer
      than front-only. Use all three angles by default.
    - The style landed (fire, gold library, cash, chandelier), a little too clean for 1998;
      the `print` finish over the whole cover fixes that.
    - No text in the images (one scribble on a cigar box). The top and bottom were mostly
      left clear for the lettering.
    - **One AI request works for one person**, so the collage approach is only needed if
      crews need it.
    - The AI added gold chains every time: jewellery must be controlled in the prompt
      (chosen pieces, or "no jewellery").
    - Artwork + lettering + `print` finish made a convincing full cover locally, for free.
19. ✅ **Prompt builder:** the guide's base + one scene + the person + clothing and jewellery
    choices + layout space. Always "no text" (`core/styles.py`). Jewellery is always a
    choice; with none picked the prompt says "no jewellery", since the AI otherwise adds
    chains.
20. ✅ **Send the subject's angle photos as references** to Nano Banana, all three, front
    first (`core/artwork.py`).
21. ✅ **Previews:** generate 4 variants at 1K (about $0.18), made at the same time and
    shown side by side to pick from, on the artwork screen (`desktop/artwork.py`).
22. ✅ **Finals:** remake the picked one at 2K (about $0.06) by sending the preview back with
    the photos. Local upscaling is still to compare in step 26. Whether a final keeps the
    preview's look closely enough is still to see on real runs.
23. ✅ **Cost guard:** the cost and the day's total are shown and confirmed before each
    batch, every paid image is logged in `spending.json`, and a daily limit ($2.00 by
    default) refuses anything over it (`core/spending.py`). Nothing is sent for someone who
    hasn't agreed to the current permission wording.

**The user's own words (2026-11-08):** D adds extra details to any scene ("a white tiger
beside them"), and a Custom scene (the last one on S) replaces the scene with the user's
own description, while the era's base style, the person and the wardrobe still apply. The
no-text / no-logos / keep-the-face rules are repeated after the user's words, and the
words are checked first for real artists, labels, brands and the Parental Advisory mark
(`check_user_text` in `core/styles.py`). Famous people can't all be listed, so they aren't
caught by that check; Google's own filters still apply.

The artwork screen hands the pick to the lettering screen (L), where the artwork gets its
own finish and a saved design includes `artwork.png` and the whole `cover.jpg`. The screen
is tested with a fake image AI; its first real run still needs trying by hand.

### Phase 5: Put it together and export
24. ✅ **Combine:** the chosen artwork plus the lettering, laid out with one of the layouts
    (the lettering screen, with the artwork aged as its own part).
25. ✅ **Keep the design as layers:** a saved design keeps `artwork.png` and a recipe, so each
    product redraws the lettering at its own size instead of stretching a flat image. The
    poster puts the square cover in the middle with the artwork blurred out to the edges;
    the tee and hoodie put it on a see-through print area; the phone case has its own tall
    layout (name below the camera corner, artwork, title).
26. ✅ **Upscaling** (`core/upscale.py`): on a 1K artwork made 3600 px, OpenCV's FSRCNN took
    0.8 s and was clearly sharper than a plain resize; EDSR looked only slightly cleaner and
    took 3.5 minutes. FSRCNN is the default. The models (Apache 2.0, about 80 MB) are kept
    out of git and fetched by `tools/get_upscale_models.py`. Comparing it with the AI's 2K
    final is still to do on real runs.
27. ✅ **Product specs** in one file (`core/products.py`): poster 5400 x 7200 (18 x 24 in), tee
    front 4500 x 5400 (15 x 18 in), hoodie front 4200 x 3600 (14 x 12 in), phone case
    1500 x 3000, all 300 dpi PNGs. These are common print-on-demand sizes, **to confirm with
    the provider** when one is chosen (bleed too). Adding a product means adding one entry.
28. ✅ **Mockups** (`core/mockups.py`): each design drawn on a black tee, a black hoodie, a
    framed poster and a phone case, in one `mockups.jpg`. They're simple drawings;
    licensed photo mockups can replace them later.

X on the lettering screen exports a saved design's print files and mockups to
`exports/<design>/` in the background (about a minute).

**Framing (2026-11-08):** the AI sometimes puts the head right under the name despite the
prompt, so the first real export had the name across the face. The lettering screen now
finds the face (MediaPipe, on this computer) and moves the artwork just enough to clear
the name and title, or zooms it out if the face can't fit between them; the gap is filled
with a blurred stretch of the artwork. Arrows move it, [ ] zoom, Z refits, O undoes, and
the framing is saved with the design and used by the cover-based exports
(`core/framing.py`). The prompt also asks for the head to sit below the top quarter.
D on the lettering screen opens a saved design (words, styles, finishes, sticker, artwork,
framing); moving its picture and pressing X updates that design in place and re-exports
it, while other changes are saved as a new design. The first export (Devin Money) was
re-made this way, with the face clear of the name.

### Phase 6: Crews
29. ✅ **Scan each member** as their own subject (the existing scan screen).
30. **Try two approaches and compare:**
    - ✅ **All at once (built 2026-11-08):** every member's references in one AI request.
      Up to 4 people send all three angles (12 photos; the model takes 14 and a final adds
      the preview); 5–6 send front photos only. The prompt says whose photos are whose
      ("photos 4 to 6 are the second person"), asks for everyone side by side without
      mixing features, dresses them alike, and makes "the person" in a scene mean the
      whole crew. A Crew line-up scene is offered only for crews. Previews are kept in
      `subjects/_crews/` with the members' names. **Still to test on a real crew.**
    - **Collage:** generate each person, cut them out with the person segmenter, and arrange
      them in a crew layout. This keeps each likeness strong and is true to the style: the
      original covers were Photoshop collages of people shot separately. **Only to build if
      the all-at-once test mixes faces up.**
31. ✅ **Crew lettering:** L from a crew opens the crew row layout, named "THE CREW" (to
    change with N), with the members' names in the featuring list. The automatic framing
    keeps all the faces clear of the lettering.

### Phase 7: The "cheap way" order flow (still local)
32. **An order folder per customer:** subjects, chosen design, proof sheet with mockups,
    final print files, and a checklist (consent, proof approved, files sent, scans deleted).
33. This is what you'd use to fill hand-run Etsy orders before any website exists.

### Phase 8: Photo mockups (added 2026-11-09)
The drawn mockups (step 28) show where a design goes, but they don't sell it. The owner
bought two Etsy mockup bundles (in `resources/`, zipped): photos of models in blank tees,
hoodies and sweatshirts. The licence covers showing our own designs on them, not sharing
the photos, so **they never go into git**: chosen photos are copied into the gitignored
`mockup_photos/` folder.

34. ✅ **A sweatshirt product** for the crewneck photos (Gildan 18000), 14 x 16 in, to confirm
    with the provider like the others.
35. ✅ **Where the print goes, guessed** (`core/photo_mockups.py`): MediaPipe's pose model finds
    the shoulders and hips, and the product's print area is placed on the chest from them,
    at its real size. A second model marks which pixels are clothes, so hands, hair and
    bags in front of the shirt stay in front of the print. It also guesses front or back
    and the garment's colour, and flags photos to check by hand (arms in the way, a turned
    body, no person found).
36. ✅ **Printed, not pasted:** the design is warped into the four corners, bent a little by the
    fabric's folds, shaded by them and given the fabric's texture.
37. ✅ **The mockup tool** (`desktop/mockup_tool.py`): go through the photos, see the guess with
    a sample design on it, drag the corners to fix it, set the product and front or back,
    or skip a photo. One key sets up every photo at once and jumps to the ones to check.
    Another puts any design PNG on every set-up photo of its product. Its logic is tested;
    the window itself still needs a first try by hand.
38. ✅ **Exports use them:** X on the lettering screen adds photo mockups of each product next to
    the drawn sheet, when photos are set up for it.
39. ✅ **Sorted the bundles** (2026-11-09): all 358 tee, hoodie and sweatshirt photos are in
    `mockup_photos/`, already guessed. 248 passed every check (66 tees, 57 hoodies, 125
    sweatshirts) and 110 are marked to check: something in front of the shirt, the print
    running off the photo, back views, two people. The couples, kids, mugs, pillows and
    listing graphics were left out. Back views were missed at first (a bit of neck or ear
    read as a face); which side each shoulder is on now tells front from back. Many of the
    photos are AI-made, so they still need an eye for warped hands or seams: S skips one.
    Exports use the first 6 per product, the ones confirmed with C first.

**After the first listing mockups (2026-11-09):** the prints sat too low and too big, and
looked pasted on. Now:
- **Garment covers print 12 in wide** (11 on the hoodie), centred at the top of the print
  area, instead of filling it. 15 in reached from armpit to armpit on a fitted tee.
- **The print hangs from the neckline** (found in the clothes mask), about 2½ in below it
  and centred on the neck opening. The shoulders only give the size and slope, since a
  raised arm moves them. On the tee photos the neckline sits about 1½ in above
  MediaPipe's shoulder points, which stands in when it can't be found; a beard over the
  collar can't push it more than a quarter of an inch below them.
- **The print looks printed:** matte ink colours (no pure black or white, a little less
  vivid), wrapped round the chest, as soft as the photo, with more of the fabric's grain.
- Twelve tee mockups of the four saved covers are in `docs/etsy-listings/mockups/`
  (gitignored: they use the bought photos and show real faces).

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
- **More style packs** (started 2026-11-08): guides for Memphis, Houston and Compton and LA
  are written (`docs/merch-styles/`), and their **artwork** prompts are in the app (R on the
  artwork screen). Still to build for them: their own lettering, layouts and finishes.
  Later: Atlanta,
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
