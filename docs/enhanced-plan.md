# Enhanced App: Update Plan

Work list for `code/course_project_enhanced/`, which started as a copy of the extended photo
booth (`docs/extended-app.md`). `course_project_extended` stays as it is. Branch:
`photo-booth-enhanced`. Agreed 2026-10-31.

## Decisions

| Topic | Decision |
| --- | --- |
| Scope | Module split, bug fixes, then a four-slot editor |
| Stickers with presets | Restyled only by presets that move pixels (Pop Art, Mirror) |
| Tests | A small `tests/` folder using Python's built-in `unittest` |
| Image library | Four slots, not an open-ended gallery |
| Choosing a slot | Keys and a Slot slider first; clickable thumbnails later |
| Layouts | Vertical strip and 2×2 grid |
| Face stickers (2026-11-01) | Stay as they are: tracked to faces, not movable |
| Movable items (2026-11-01) | A new **scene props** system: plain assets, not face-tracked, placed and moved by hand |
| AI backend (2026-11-01) | Cloud APIs first (larger models), not local; see `docs/ai-image-generation-plan.md` |

## 0. Environment

- [x] Fix the enhanced venv: it has `opencv-python` but no MediaPipe. Uninstall
      `opencv-python`, then install `mediapipe`, which brings `opencv-contrib-python`.
- [x] Add `requirements.txt` with pinned versions.

## 1. Split into modules (no visible changes)

- [x] `filters.py`: kernels and presets
- [x] `overlays.py`: frames, stickers, Cody, background swap
- [x] `tracking.py`: MediaPipe face and person detection
- [x] `sources.py`: webcam / uploaded image
- [x] `booth.py`: photo strip countdown and saving
- [x] `asset_library.py`: loads frames, stickers, backgrounds, mascot
- [x] `look.py`: one function that takes an image and its settings (a "look") and returns
      the finished picture. The four-slot editor (step 4) builds on it.
- [x] `app.py`: windows, sliders, keys and the main loop only
- [x] Check that the output matches the extended version screen for screen
      (all 73 test screens and both saved files are pixel-identical)
- [x] `tests/test_core.py`: run with `.\.venv\Scripts\python.exe -m unittest discover tests`

## 2. Bug fixes (one commit each)

- [x] Gaussian blurs only blur up and down: build proper 2D kernels
- [x] Contrast slider jumps in whole steps: steps of 0.1 (slider 0–30 divided by 10)
- [x] Closing a window with the X doesn't exit: quit cleanly when either window closes
- [x] Both colour and grey versions are processed every frame: process only the one on screen
- [x] Frames are stretched on non-4:3 pictures: scale evenly, then stretch only the plain
      border sections, so corners and captions keep their shape. (Lines are repeated only
      inside long plain stretches. The film strip has none along its sides, so its holes
      still stretch on very tall pictures.)
- [x] Stickers don't line up with Pop Art and Mirror: add them before those presets
- [x] Comic Dots is slow on large photos: make the dot size grow with the image size
      (960×720: 42 ms → 20 ms; webcam size unchanged)

## 3. Cody cut-outs (after the bugs)

Photoshop cut-outs in `resources/csn_assets/`: `mascot-2025_cutout.png`,
`cody-3-2_cutout.png`, `cody-4-2_cutout.png`. They are much cleaner than the automatic one.

- [x] Crop each cut-out tight to Cody (remove the empty transparent space) and save it in
      `assets/mascot/`, one file per pose (`1_basketball`, `2_cheering`, `3_peekaboo`).
      The originals in `resources/` stay as they are.
- [x] Also trim any leftover padding when loading, so future art doesn't need cropping first
- [x] Keep Cody anchored to the bottom-right. `cody-4-2` is cut off at the right edge, so it
      must sit flush with the right side.
- [x] Cody slider: 0 = off, then one setting per pose (`M` cycles through them)
- [x] Stop `make_assets.py` from overwriting the Cody art (it no longer makes Cody at all)
- [x] Size Cody by height (3/4 of the picture) and width (45%), whichever is smaller, so the
      wide half-body poses don't cover the people in the photo
- [ ] Later: `3_peekaboo` is also cut off at the top (ear tips), which shows as a flat edge

## 4. Four-slot editor

- [x] Four slots, filled by the photo strip (all four, then the editor opens), by `A` (the
      camera picture goes into the selected slot), or by `U` in the editor (upload into
      the selected slot). `E` switches between the camera and the editor.
- [x] Each slot keeps its unedited image and its own look; the sliders show the selected
      slot's look. The camera's settings come back when leaving the editor.
- [x] Live preview as a vertical strip or a 2×2 grid (`L` or the Layout slider); `S` saves
      either layout (`edited-strip-…` / `edited-grid-…`). `X` clears a slot.
- [x] Choose slots with `Tab` and a Slot slider (the selected slot is outlined in gold)
- [x] Slot photos are analysed once with image-mode MediaPipe models (video mode expects
      each frame to follow on from the last)
- [x] Click a slot in the editor to choose it (added with scene props, step 6)

## 5. Masking (Roadmap Part 2, Step 10)

The person mask (MediaPipe selfie segmenter) is currently used raw, only for background swap.

- [x] Mask clean-up (`masks.refine_mask`, about 3 ms per frame): firm up the uncertain edge,
      remove specks and pinholes, pull the edge in by 1 px, soften slightly. Background
      swap uses it too; the pale halo of the old background is gone. (A guided filter was
      tried and made the halo *wider* on plain backdrops, so it was dropped.)
- [x] A "Focus" setting (slider + `P`): off, color pop (person in colour, background
      grey), portrait blur (background blurred), mask preview (shows what counts as the
      person). The on-screen label shows it, e.g. "Original + Color Pop".
- [x] The camera loop asks MediaPipe for the mask whenever Focus is on, not only for
      background swap (`Look.needs_person_mask()`)
- [x] Tests, a visual check, and screens without background swap or Focus unchanged pixel
      for pixel (57 of 72); the other 15 are the expected background-swap changes and the
      help panel

## 6. Scene props (movable assets)

Plain transparent PNGs that are **not** tracked to faces: inserted into a photo and moved
by hand. Face stickers stay as they are.

- [x] `assets/props/`, loaded in name order and trimmed like the Cody poses: five placeholder
      props from `make_assets.py` ("GO CSN!" sign, foam finger, trophy, speech bubble,
      pennant), followed by the three Cody poses. Later: cartoon Cody (step 7).
- [x] Each slot's look keeps its own props (`props.PlacedProp`: which prop, centre and size as
      fractions of the photo, so they stay put at any size). Saved strips/grids include them.
- [x] Editor: the Prop slider picks a prop and `I` adds it to the middle of the photo. Click a
      prop to select it (outlined in light blue, brought to the front, name in the title).
      Drag to move it, use the mouse wheel or `+`/`-` to resize it, and `D` to delete it.
      Clicking see-through corners selects what's behind. Clicking another slot selects
      that slot.
- [x] Decided: the Cody slider stays as it is, and the Cody poses are *also* props
- [x] Decided: props in the editor only, for now
- Note: the selection outline can be one frame (about 1/30 s) ahead of the picture while
  dragging, because mouse events arrive after the frame is drawn

## 7. AI image generation (cloud APIs first)

See `docs/ai-image-generation-plan.md`: AI styles, AI backgrounds (using the step 5 mask),
and a **cartoon Cody** made with AI that can be used as a prop (step 6), so students can
pose with a cartoon Cody as well as the photo cut-outs.
