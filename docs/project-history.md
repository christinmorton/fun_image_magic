# Project History

How the project got from a course assignment to Cover Studio, one entry per working
session, in date order. Each entry says what happened, the decisions and their reasons,
and anything worth remembering. The details of what was built are in the plans and
records each entry points to; what's still left to do is in `docs/open-items.md`.

Consolidated on 2026-11-10 from the session summaries and the Cover Studio session record
of 2026-11-08. Times are Pacific. Commit hashes can be checked with `git show <hash>`.

**Adding to it:** at the end of a working session, add a short entry at the end in the same
form, and update `docs/open-items.md`.

---

## At a glance

| Dates | Session | Commits | Tests at the end |
| --- | --- | --- | --- |
| Oct 30–31 | The course project, by the owner | 8 | |
| Oct 31–Nov 1 | From course project to image service, plus cover research | 62 | Image service 72 |
| Nov 2, early morning | A brand-neutral base and template 0.2.0 | 8 | |
| Nov 2 and Nov 8 | Image service review, merch planning and Cover Studio | 76 | Cover Studio 185 |
| Nov 8, evening | The browser webcam and video uploads | 20 | Image service 94, web engine 31 |
| Nov 9, morning | Project review and the scan's brightness fix | 0 | Cover Studio 186 |
| Nov 9 | Business ideas, photo mockups, Etsy listings, bootleg tee styles | 11 | Cover Studio 225 |
| Nov 10 | Consolidating the records | 6 | (docs only) |

The branches build on each other: `master` → `photo-booth-extended` →
`photo-booth-enhanced` → `image-service` → `cover-studio`. There's no `main` and no
remote.

---

## Oct 30–31: The course project (by the owner)

- **Commits:** 8, from `9253221` (Oct 30, 7:55 pm) to `5024572` (Oct 31, 1:01 pm), on
  `master`. No assistant session.
- The owner's OpenCV course app (`code/course_project/`): an image loaded in greyscale,
  trackbars for brightness and contrast, convolution kernels, and saving the result. The
  last commit copied it to `code/course_project_extended/` for new features.
- The original idea, a fun photo booth for a college event, is written up in the root
  `readme.md`.

---

## Oct 31–Nov 1: From course project to image service, plus cover research

- **Commits:** 62, from `38c194f` (Oct 31, 1:16 pm) to `e7602fc` (Nov 1, 3:40 pm)
- **Branches:** `photo-booth-extended`, `photo-booth-enhanced`, `image-service`
- **Transcript:** `17f09441-1e96-441c-8fa5-50451206880a`
- **Records:** `docs/project-review.md`, `docs/expansion-roadmap.md` and `-part-2.md`,
  `docs/extended-app.md`, `docs/enhanced-plan.md`, `docs/ai-image-generation-plan.md`,
  `docs/ai-costs-overview.md`, `docs/ai-api-pricing.md`, `docs/api-service-plan.md`,
  `docs/image-service-v0.1.0-handoff.md`

**What happened**
- **A review** of the course project: not worth anything as a finished product, but a
  solid start (it already has a booth's basic loop). Two roadmaps followed.
- **The extended app** (`course_project_extended`): a webcam booth for a CSN event, with
  17 presets, face stickers, background swaps, frames, the mascot Cody and a photo strip.
- **The enhanced app** (`course_project_enhanced`): split into modules with tests, six bug
  fixes (one commit each), Cody in three poses, a four-slot editor, person masking, movable
  scene props and a start-over reset. A first AI trial with Google's Nano Banana (about
  $0.10) went well, but the AI reframed photos, which led to the "person kept" check.
- **The image service** (`image_service`): a standalone FastAPI service, meant to be called
  by a separate Laravel app. `core/` (the engine), `api/` and `desktop/`; photo upload,
  render and compose; AI jobs with nine presets, progress (fields, webhooks and a live
  stream), a daily AI limit; photos kept only in memory, "delete everything", upload and
  rate limits.
- **Handed off** as v0.1.0 (tag `image-service-v0.1.0`, `e7602fc`) to the Laravel project.
- **Merch research** (evening, in `resources/ghetto_asethetic_merch/`, not in git): 102
  album covers from New Orleans, Memphis, Houston and Compton, and a hip-hop style
  timeline by region with sources.

**Decisions**
- Cloud AI first (Nano Banana), because the models are bigger and nothing is installed.
- Send only the unedited photo to the AI, and paste the person back only if the person
  masks overlap by at least 85%, because the AI reframes pictures.
- The engine isn't shaped by the calling app, so the service stands on its own. The
  Laravel test call belongs to the Laravel project.
- The album covers are research only: borrow the style, never reuse the artwork
  (copyright).

**Worth remembering**
- A test printed the API token in an error trace, and a pasted `curl` command shared it.
  Both times the token was rotated. Since then, secrets are never printed.
- Real AI billing ran above the estimate (thinking tokens and input images): budget about
  $0.045–0.05 per image.
- Both pasted research notes credit *Guerrilla Warfare* (1999) to Big Tymers; it's a Hot
  Boys album.

---

## Nov 2, early morning: A brand-neutral base and template 0.2.0

- **Commits:** 8, from `7bfd1f0` (5:52 am) to `f6f2684` (6:52 am), on `image-service`.
  No summary was written for this session; this entry is reconstructed from its commits.
- **Records:** `CLAUDE.md`, `docs/desktop-to-api-lessons.md`, `docs/template-plan.md`,
  version 0.2.0 in `code/image_service/CHANGELOG.md`

**What happened**
- `CLAUDE.md` was added, with the project's rules for future sessions.
- The CSN branding was removed: `core/brand.py` holds the name, cheer and colours, and
  `tools/make_assets.py` draws placeholder art from them. The service was written for any
  calling app, not one framework.
- `docs/desktop-to-api-lessons.md` recorded what turning the desktop booth into an API lost
  (the webcam and the live feel).
- The readme was updated, the template plan and a script that cuts releases were written,
  and **image service 0.2.0** was released and cut as the first frozen template (tag
  `image-service-template-v0.2.0`).

---

## Nov 2 and Nov 8: Image service review, merch planning and Cover Studio

- **Commits:** 76, from `9984370` (Nov 8, 12:39 pm) to `fa54cdd` (Nov 8, 8:13 pm). Nothing
  was committed on Nov 2.
- **Branch:** `cover-studio`, created from `image-service`
- **Transcript:** `c8bf6133-c364-4557-bc8e-745a61a2bceb`
- **Records:** `docs/merch-app-plan.md` (Phases 0–6), `docs/merch-getting-customers.md`,
  `docs/merch-styles/`, `code/cover_studio/README.md`

**What happened**
- **A review of the image service** (Nov 2): three problems confirmed by running them
  (delete-everything doesn't stop queued AI jobs, the frame cache grows without limit, a
  small upload decodes to a huge image) and several smaller ones. None were fixed then.
- **The merch idea** (Nov 2): a person's face in a 1990s Southern rap cover, on merch, with
  a guided face scan, one person first and crews later, tested with hand-run orders. Etsy
  was looked at: buyers can't upload photos in the personalisation box.
- **Privacy** (Nov 8): Google's paid Gemini tier doesn't use content to improve its
  products, while the free tier may. The owner confirmed a paid key, and the permission
  wording now says photos go to Google's image AI.
- **The four-process design:** a cover is **style** (a written guide), **likeness** (the
  scan), **artwork** (the AI, the only paid step) and **lettering** (drawn in code). Making
  lettering its own process was the owner's idea.
- **Cover Studio** (`code/cover_studio/`), copied from template 0.2.0, built in one day:
  - lettering: six fonts, seven treatments (ice, gold, chrome and others), four layouts,
    stickers of our own, and aged `print` and `vhs` finishes for each part
  - the guided scan: front, then three-quarter turns each way, captured automatically
  - artwork: a paid likeness test (about $0.18) showed three angles keep the face closest;
    then scenes, clothes, jewellery, four previews, a 2K final and a $2.00 daily limit
  - print files for a poster, tee, hoodie and phone case, with a fast built-in upscaler
  - framing that keeps the name off the face, and reopening saved designs
  - crews of up to 6 in one AI request
  - style guides and artwork prompts for Memphis, Houston, and Compton and LA

**Decisions**
- Desktop first, with selling and the web API on hold, to get the app working well.
- A new app copied from the template, not changes to the image service, because that's
  what the template is for.
- The AI never draws text: it garbles words, and names must be spelled right.
- The album covers are never sent to the AI, traced or trained on. No real Parental
  Advisory mark or other trademarks; three sticker designs of our own instead.
- Jewellery is always an explicit choice, or the AI adds chains every time. The base prompt
  never mentions fire, or every scene gets flames.
- FSRCNN is the default upscaler: sharp in under a second, while EDSR takes 3.5 minutes for
  little gain.
- One commit per feature: the owner's standing preference, from this session on.
- The test subjects are the owner under made-up names, so no one else's consent is needed
  yet.

**Worth remembering**
- Double quotes inside a commit message break PowerShell's arguments; once this merged two
  commits, which were redone.
- Problems were found by looking at real output: gems tinted green and pink, fire in every
  scene, and the name across the face in the first export.

---

## Nov 8, evening: The browser webcam and video uploads

- **Commits:** 20, from `671f624` (8:28 pm) to `585be22` (9:51 pm): 19 on `image-service`,
  then the merge into `cover-studio`
- **Transcript:** `76446864-be0a-4218-8b5b-ec3fe6b609b0`
- **Records:** `docs/web-webcam-plan.md`, `code/image_service/web/README.md`, "Unreleased"
  in `code/image_service/CHANGELOG.md`

**What happened**
- **A review of the project and its history** (chat only): its findings are in
  `docs/open-items.md`.
- **The browser webcam** (`code/image_service/web/`, Vite and plain JavaScript), the fix for
  the v0.1.0 lesson that the web app lost the webcam's live feel:
  - the camera, live effects (WebGL) and face tracking run in the browser; the service only
    does the exact final render
  - the page's own server adds the token, so the browser never sees it
  - live stickers, frames, the mascot, background swap and focus effects
  - video recording, until stopped or up to 5 minutes
- **Video uploads on the API:** `POST /v1/videos` keeps a video for a while so the calling
  app can collect it from `GET /v1/videos/{id}/file`, then delete it.
- **The frame cache** in `image_service` was capped at 32 sizes, with a lock.
- `image-service` was merged into `cover-studio`; `code/cover_studio/` was unchanged by it.

**Decisions**
- Keep the interactive loop in the browser and use the service for the render, AI and video
  storage, as `docs/desktop-to-api-lessons.md` advises.
- One engine with no UI and several front ends: vanilla first, React and Vue later.
- When video storage is full, refuse new uploads rather than delete old ones, so a video
  the app hasn't fetched yet is never lost.
- Cut template release 0.3.0 another time (the owner's choice).

**Worth remembering**
- Switching to `image-service` left Cover Studio's scans and designs untracked, because
  that branch's `.gitignore` lacked Cover Studio's rules; `git add -A` would have committed
  the owner's face scans. The two `.gitignore` files are now identical.
- Mirroring the camera swaps MediaPipe's eye corners, which would have turned stickers
  upside down.

---

## Nov 9, morning: Project review and the scan's brightness fix

- **Commits:** none during the session. The fix was committed later that day as `1672a0d`
  (2:05 pm), in the next session.
- **Branch:** `cover-studio`
- **Transcript:** `8538477c-f935-4495-a230-d92bbdb1c3c5`
- **Records:** Phase 3 in `docs/merch-app-plan.md`; the review's findings are in
  `docs/open-items.md`

**What happened**
- **A review of the whole project:** all tests passed. The findings were mostly about two
  things happening at once, or quitting mid-task; nothing breaks normal one-person use. The
  image service part was reviewed by a separate agent, and its two most serious findings
  checked by hand. Nothing was fixed.
- **A failed scan:** a woman with bangs and hair over the sides of her face kept getting
  "Your face is too dark" until a lamp was turned on. The brightness check counted her hair
  as face. It now measures only the middle of the face (between the cheeks, from below the
  eyes to the upper lip). A test reproduced the problem first, and the fix was checked on
  13 stock portraits.

**Decisions**
- Keep the brightness cutoffs (70 and 215): the middle of the face reads a little brighter,
  and still stays under 215.
- Leave the turn reading and the blink check alone: only brightness was reported.

---

## Nov 9: Business ideas, photo mockups, Etsy listings and bootleg tee styles

- **Commits:** 11, from `1672a0d` (2:05 pm) to `2aab92f` (8:08 pm). The first is the
  morning session's brightness fix.
- **Ran:** about 11:50 am to 4:20 pm, then 7:45 to 8:10 pm
- **Branch:** `cover-studio`
- **Transcript:** `719b7e31-d3ef-418e-bca8-191540b9f9d1`
- **Records:** `docs/merch-app-plan.md` (Phases 8 and 9, and the note after the first
  listing mockups), `docs/etsy-listings/`, `code/cover_studio/README.md`

**What happened**
- **Business questions** (chat only): album covers for indie artists are viable but small;
  a 360 booth is a poor fit (it makes video), but event booths are promising; other uses
  are group merch, party flyers, gifts and themed event booths. How a 360 booth works was
  explained (a video with a speed ramp; buy the platform, write the software), but nothing
  was built. Most of Cover Studio isn't rap-specific, so new looks could be "style packs".
- **Photo mockups** (`bca6ab2` to `7528fd8`): from two mockup bundles the owner bought on
  Etsy (in `resources/`, licensed for showing their own designs, not for sharing).
  - a sweatshirt product, 14 x 16 in
  - `core/photo_mockups.py`: MediaPipe's pose model and clothes segmenter guess where the
    print goes and what's in front of the shirt; each photo's set-up is kept next to it
  - `desktop/mockup_tool.py` to check and fix the guesses, and put any design on every
    photo of a product
  - exports add up to 6 photo mockups per product
  - all 358 tee, hoodie and sweatshirt photos sorted into the gitignored
    `code/cover_studio/mockup_photos/`: 248 passed every check
- **The business plan** (chat only): sell by hand first (orders on Etsy, photos sent by
  Etsy Messages, each design made in Cover Studio, then printed on demand); an own
  storefront (Medusa.js) only once there's demand; no free AI previews; one listing per
  product; remote buyers send three selfies, loaded with P on the scan screen.
- **Etsy listing drafts** (`3121c74`): eight listings ready to paste, a shared README, and
  `photo-checks.md` (checks against celebrities, missing consent and minors before any
  design is made).
- **Listing mockups:** 12 tee mockups of the owner's four covers, in the gitignored
  `docs/etsy-listings/mockups/`. The owner found the prints "off a bit" and "too perfect",
  which led to covers printed 12 in wide instead of 15, prints that hang from the neckline,
  and a matte, printed-ink look (`4709a71` to `55b5469`).
- **A change of view** (evening): someone in events advised that this sells best in person,
  made on the spot. The owner decided Cover Studio is mainly a personal challenge project,
  with Etsy as a low-pressure try.
- **Bootleg tee styles** (`2fb8a8f`): faded halftone edges and knockout (the shirt shows
  through the darks or lights). Faded and knockout together look like a real bootleg print
  on black tees; white tees need the cutout collage instead. Event branding and style packs
  beyond 90s rap were noted for later (`2aab92f`).

**Decisions**
- Sell by hand first, and build a self-service site only after demand is proven, because
  it's months of work and each AI preview costs money.
- No free AI previews: AI is only spent on paid orders.
- The bought mockup photos and the listing mockups stay out of git: the licence covers
  showing the owner's designs, not sharing the photos, and the mockups show real faces.
- Front or back is decided by which side each shoulder is on, since a bit of neck read as
  a face and let back views through.
- Garment covers print 12 in wide (11 on the hoodie), because 15 in reached from armpit to
  armpit on fitted tees. This changed the real print files too.
- Tee styles print part-covered areas as halftone dots, never see-through ink, which shirt
  printers print badly.
- Cover Studio is a personal challenge project first (the owner's view).

**Worth remembering**
- The mockup photos are AI-generated themselves, so they need an eye for warped hands and
  seams.
- The evening's work was first dated Nov 10 in the plan, by mixing up UTC and Pacific
  time; corrected on Nov 10.
- Commits shared between features were split by staging in-between versions of a file
  (`git hash-object` and `update-index`), since `git add -p` isn't available here.

---

## Nov 10: Consolidating the records

- **Commits:** 6, starting with `cb17b76`
- **Branch:** `cover-studio`
- **Transcript:** `719b7e31-d3ef-418e-bca8-191540b9f9d1` (the same as Nov 9)

**What happened**
- The session summaries and the Cover Studio record of Nov 8 were merged into this history,
  at about a third of their length, and their "left open" lists into
  `docs/open-items.md`. The two periods with no summary (the course project, and the Nov 2
  morning) were reconstructed from git.
- Facts were checked against git and the code: commit counts, the side-turn angles (28–55°,
  not 20–55°), and which fixes reached which copy of the code.
- `docs/merch-app-plan.md` was brought up to date, along with the root `readme.md`,
  `docs/merch-getting-customers.md` and `CLAUDE.md`.
