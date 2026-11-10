# Open Items

Everything left to do, decide or check across the project, in one place. Gathered on
2026-11-10 from every session's "left open" list (see `docs/project-history.md`), with
duplicates merged and finished items removed.

**Keeping it current:** when something here is done, delete it, and record it in the
plan it belongs to and the session's entry in the history. Add new open items here, in the
right group. Dates say when an item was found.

Nothing here is urgent: Cover Studio is a personal challenge project first, and selling is
optional.

---

## Housekeeping

- **Back up the gitignored files.** The code has been on GitHub (private) since
  2026-11-10, but the gitignored files aren't in git: Cover Studio's scans, designs and
  exports, the bought mockup photos, the listing mockups and `resources/`. Keep a separate
  backup of them (an external drive or a private cloud folder), and never push them.
- **Template release 0.3.0** hasn't been cut. Everything since 0.2.0 is under
  "Unreleased" in `code/image_service/CHANGELOG.md` (the browser webcam, video uploads,
  full-size art, the frame cache fix). The steps are in `CLAUDE.md`. Afterwards, merge
  `image-service` into `cover-studio` again; the template's `web/` needs `npm install` once.
- **Test warnings,** not looked into: a `ResourceWarning` for an unclosed `tee.png` in an
  export test, and a Starlette deprecation warning about `httpx`.
- **The AI cost estimate** in the code is $0.037 per image; real billing runs about
  $0.044–0.05 (2026-11-01). Raise the number, or track real token use.

## The image service (`code/image_service/`)

Found in the reviews of 2026-11-02 and 2026-11-09. Cover Studio and the template carry the
same code, but Cover Studio doesn't use its API yet, so fix these in `image_service` first.

**Could lose data or take down the server** (the suggested first fixes, one commit each):
- **Request bodies are read in full before the token check,** so someone without the
  token can fill the disk or memory with one huge upload.
- **Starting the service deletes every file in the video folder** (`api/videos.py`).
  Running the tests while the dev service is up wipes its videos, and apps made from the
  template share the same temp folder by default.
- **Uploads sent at the same time get past the 3 GB video limit:** the space used is
  counted once, before each copy starts.

**Known, smaller or parked:**
- **"Delete everything" doesn't stop queued or running AI jobs** (`api/ai_jobs.py`). They
  still call the AI, which costs money, and save their results afterwards.
- **A small upload can decode to a huge image** (a 442 KB PNG became 432 MB) before it's
  shrunk.
- **Memory:** stored photos can use about 5.6 GB at the 200-photo limit, and fitted frames
  (capped at 32 since 2026-11-08) can still hold about 2 GB at 4096 px.
- **The frame cache fix** (`2db0d5e`) is only in `image_service`. Cover Studio's copy and
  template 0.2.0 still grow without limit.
- **The dev proxy example** passes every route on with the token. An app that copies it
  would let any page visitor delete photos or start paid AI jobs.
- **Smaller:** expired items are only removed on the next request; every booth behind one
  app server shares one rate limit; uploads block renders; webhooks slow jobs down; Comic
  Dots crashes on tiny images; a comment in `web/src/engine/recorder.js` is out of date.

**The browser webcam (`web/`):**
- **Phase 4:** the React and Vue versions over the same engine.
- **Leaks:** switching camera twice quickly leaves the camera on; a failed recording start
  leaves the microphone on; on an all-day kiosk, videos pile up in memory.
- **Limits:** background-swap edges are softer than the service's; face outlines and the
  VHS preset's "REC" aren't in videos; a recording with no time limit is held in memory
  (about 33 MB a minute); recording in a hidden tab wasn't tried; there's no progress bar
  for sending a large video.
- **Video hand-off:** an app's forwarding route must accept uploads of around 150 MB;
  `DELETE /v1/photos` doesn't delete videos; a setting to keep videos in a folder of the
  owner's choosing was offered but not added.

## Cover Studio (`code/cover_studio/`)

**To try (needs the owner):**
- **A crew with a real second person.** Every saved subject is the owner, so it isn't
  known whether different faces blend in one AI request. If they do, build the collage
  approach (plan, step 30).
- **The new regions' artwork** (Memphis, Houston, Compton and LA) hasn't been tried. Start
  with Houston *Slab parade* and Compton and LA *Lowrider*.
- **The 2K final** hasn't been compared with the local upscaler on real runs.
- **After a scan of someone with bangs, watch for** "Keep your eyes open" (half-hidden eyes
  may read as closed) and side shots that won't settle (hair over the temples upsets the
  turn reading).

**Bugs from the 2026-11-09 review:**
- **A finished AI result can be lost:** in `poll()` in `desktop/artwork.py`,
  `done, self._done = self._done, None` can wipe out a result if the job finishes at the
  wrong moment. The screen then waits forever, though the paid previews are saved. Rare;
  a two-line fix.
- **Quitting during an AI job** kills its thread: Google may still bill for the images, but
  they're never saved or logged in `spending.json`, so the daily limit undercounts.
- **The banned-words check** lets hyphenated spellings through ("cash-money") and blocks
  ordinary words ("supreme", "marvel at", "a juvenile tiger"). Best-effort by design.
- **A missing angle photo** in a subject's folder causes an unclear OpenCV crash at the
  artwork step.
- **Sharpness is measured on the whole face box,** so hair texture can make a slightly
  blurred face pass as sharp.

**To build, when wanted:**
- **Stage 2 of the new regions:** their own lettering, layouts and finishes (listed in each
  guide in `docs/merch-styles/`).
- **Exports the Etsy listings need:** a 3000 x 3000 digital cover, and the lettering alone
  for the name-only tee.
- **For orders by hand:** quality checks on loaded photos (the live scan's checks, so a bad
  selfie is caught before paying for AI), a scan from a short head-turn video, order
  folders with a checklist (Phase 7), and watermarked proofs.
- **Tee styles (Phase 9):** the cutout collage, which light shirts need, and a tee style
  choice in the lettering screen and exports once a look is settled.
- **The owner's "small prompt tweaks"** were never described, and a better name than
  "Block at dusk" is open.
- **Unused template code:** the booth in `desktop/app.py` and the `api/` folder came with
  the template and aren't used.

## Selling (optional, low pressure)

- **Before any Etsy listing** (`docs/etsy-listings/README.md`): choose a print-on-demand
  provider and check its blanks, print sizes (including the 12 in covers) and base prices
  against the drafts; set personalised orders to wait for the design; make the sample
  gallery (the one AI cost before any sale).
- **Check Etsy's current rules** on production partners, AI disclosure and custom digital
  items. The photo rules said to start on 22 October 2026 came from seller blogs, not
  Etsy's own pages.
- **Check the tags against real searches:** a ProfitTree keyword check was offered, not run.
- **Mayella's cover** shows a plant that looks like a cannabis leaf; remake it before using
  it in a main listing photo.
- **Events:** someone in events said this sells best in person, made on the spot. One small
  event would test that. An "event mode" (one AI image, automatic lettering, a QR code)
  would make it quick enough.
- **Phase 7, the order flow,** isn't built.

## Research and ideas

- **Covers to collect:** Atlanta, Miami, Detroit and New York (the plan is in
  `resources/ghetto_asethetic_merch/notes.txt`, with the Cover Art Archive as the
  fallback); the Bay Area, St. Louis, Baton Rouge and Chicago are lower priority. Renaming
  the misspelt `ghetto_asethetic_merch` folder was offered; `resources/` is the owner's.
- **Event branding:** what event hosts want on a souvenir (name, date, logo, hashtag,
  sponsor, a printed border). Covers and shirts can't carry any of it yet.
- **Style packs beyond 90s rap:** movie, fight and magazine posters, and others.
- **360 booth software:** ffmpeg speed ramps, slow motion by filling in frames, sharing by
  QR code, and a spin that ends on the guest's cover. Only discussed (2026-11-09).
- **AI versions of Cody at CSN events:** the owner was talking with coworkers (2026-11-01).
