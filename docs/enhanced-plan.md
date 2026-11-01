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
- [ ] Frames are stretched on non-4:3 pictures: scale evenly, then stretch only the plain
      border sections, so corners and captions keep their shape
- [ ] Stickers don't line up with Pop Art and Mirror: add them before those presets
- [x] Comic Dots is slow on large photos: make the dot size grow with the image size
      (960×720: 42 ms → 20 ms; webcam size unchanged)

## 3. Cody cut-outs (after the bugs)

Photoshop cut-outs in `resources/csn_assets/`: `mascot-2025_cutout.png`,
`cody-3-2_cutout.png`, `cody-4-2_cutout.png`. They are much cleaner than the automatic one.

- [ ] Crop each cut-out tight to Cody (remove the empty transparent space) and save it in
      `assets/mascot/`, one file per pose. The originals in `resources/` stay as they are.
- [ ] Also trim any leftover padding when loading, so future art doesn't need cropping first
- [ ] Keep Cody anchored to the bottom-right. `cody-4-2` is cut off at the right edge, so it
      must sit flush with the right side.
- [ ] Cody slider: 0 = off, then one setting per pose
- [ ] Stop `make_assets.py` from overwriting the Cody art

## 4. Four-slot editor

- [ ] Four slots, filled by the photo strip, by `S`, or by uploading into the selected slot
- [ ] Each slot keeps its unedited image and its own look; the sliders show the selected
      slot's look
- [ ] Live preview as a vertical strip or a 2×2 grid; save either layout
- [ ] Choose slots with keys and a Slot slider
- [ ] Later: click thumbnails to choose a slot
