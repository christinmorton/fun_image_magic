# Changelog

The image service's releases, newest first. Each entry says what changed, whether apps
made from an older template should take it, and which files it touches. The version is
`SERVICE_VERSION` in `api/settings.py`, and `/health` reports it.

## Unreleased

**For apps:** take `web/` if your app needs the live camera in a browser. Nothing else
changed, and the API is the same.

- **Web webcam (`web/`):** a Vite project with the booth's live camera in the browser. It
  runs the camera, live effects for every preset (WebGL) and face tracking in video mode,
  then sends the captured photo to the service for the exact render. The engine
  (`web/src/engine/`) has no UI, and a vanilla HTML, CSS and JavaScript booth is built on it.
  The page's server forwards requests and adds the token, so the browser never has it.
  See `web/README.md` and `docs/web-webcam-plan.md`.
- **`tests/test_web.py`** checks that the browser's presets, filters, look defaults and
  brand colours still match `core/`.
- **Fixed: fitted frames no longer pile up in memory.** `fit_frame` remembered every
  photo size it had fitted a frame to, forever. It now keeps the 32 most recent
  (`core/overlays.py`). Apps should take this.

## 0.2.0 (2026-11-02): the first template

**For apps:** this is the starting point, so there's nothing to update from.

- **Brand-neutral.** `core/brand.py` holds the name, cheer and colours. To rebrand, edit
  it and run `tools/make_assets.py`.
- **Placeholder art drawn from the brand:** frames, stickers, backgrounds and props. Long
  text shrinks to fit.
- **A placeholder mascot** in three poses (waving, cheering, peekaboo). It's only drawn
  into an empty `core/assets/mascot/`, so real mascot art is never overwritten.
- **Art changes from 0.1.0:**
  - a cheer frame, a spotlights background, a cheer sign and cat ears replace the old
    event-specific art
  - background numbers changed: `space` is now 3 and `spotlights` is 4
- **AI presets:** the court background's key is now `basketball_court`, and no prompt
  names particular colours.
- **Callers:** written for any app's API, called server to server with the shared token.
- The API is titled "Image Service".

**Known issues:**

- `DELETE /v1/photos` doesn't cancel AI jobs that are queued or running. They still call
  the AI provider, which costs money, and they save their result afterwards
  (`api/ai_jobs.py`).
- Photos, AI jobs and counters live in memory: run a single process, and expect a
  restart to lose them.
- The cost in `GET /v1/ai/usage` is an estimate (`COST_PER_IMAGE_USD` in `core/ai.py`).
- Face tracking works best on faces turned towards the camera. Uploaded stills are
  analysed one at a time, so faces at an angle are often missed.
- Tested on Windows 11 with Python 3.15 only.

## 0.1.0 (2026-11-01)

The first version, built for one event and one web app. It isn't a template. It's
archived as the git tag `image-service-v0.1.0` in the `fun_image_magic` repo.
