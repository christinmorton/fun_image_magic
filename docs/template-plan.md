# Image Service Template: Plan

How the frozen template is kept, released and fixed. Written 2026-11-02.
**Status: in use** since release 0.2.0 (2026-11-02).

---

## The pieces

| Where | Role | How it changes |
| --- | --- | --- |
| `code/image_service/` | **The working base.** All development and every fix happens here | Freely, commit by commit |
| `code/image_service_template/` | **The frozen template:** an exact copy of one release, for starting new apps | Only by being replaced with a newer release ("cutting" one) |
| New apps | Copies of the template in their own projects, rebranded in `core/brand.py` | By their owners; fixes arrive as described below |

## Rules

1. **Never edit the template by hand.** It only changes when a new release is cut from
   `image_service`. So "what's in template X" always has one answer.
2. **Every fix starts in `image_service`.** That includes general fixes found while
   building an app. Brand-only changes stay in that app.
3. **Every release has a version number, a changelog entry and a git tag.**
4. **Keep app-specific changes in `core/brand.py` and `core/assets/`.** The fewer other
   files an app changes, the more cleanly later fixes apply to it.

---

## Versions

The version lives in `api/settings.py` (`SERVICE_VERSION`), and `/health` and `/docs` both
report it.

| Version | What it is |
| --- | --- |
| 0.1.0 | The archived CSN version (tag `image-service-v0.1.0`) |
| **0.2.0** | **The first template:** brand-neutral and caller-neutral |

How the numbers move:

| Change | Example | Should apps take it? |
| --- | --- | --- |
| **Patch:** bug fixes only | 0.2.0 → 0.2.1 | Yes |
| **Minor:** new features, or changes to the look JSON, catalog or API | 0.2.x → 0.3.0 | If they want them |

Each cut is tagged `image-service-template-v<version>`, e.g.
`image-service-template-v0.2.0`.

## Changelog

- `code/image_service/CHANGELOG.md`, newest first.
- An **Unreleased** section collects changes as they're made. At release time it becomes
  "0.2.1 (date)".
- Each entry says **what changed**, **whether apps should take it**, and **which files** it
  touches.
- The template carries its own release's changelog, so every app knows what it started
  with.

---

## Cutting a release

1. In `code/image_service/`:
   - "Unreleased" in the changelog becomes the new version, e.g. "## 0.2.1 (date)"
   - `SERVICE_VERSION` is set to match
   - the tests pass
   - commit ("Release image service 0.2.1")
2. From the repo root, run `py tools\cut_template.py`. It:
   - refuses if `code/image_service/` has uncommitted changes, or if the changelog has no
     entry for the version
   - makes the template an exact copy of the files git tracks in `image_service`
   - leaves the files git ignores alone (`.venv`, `.env`, `__pycache__`, output folders)
   - checks every file byte for byte

   The script lives outside both folders, so it's never copied into apps.
3. Run the template's own tests, using the `image_service` virtual environment, from
   `code/image_service_template/`:
   `..\image_service\.venv\Scripts\python.exe -m unittest discover tests`
   This proves the copy works on its own.
4. Commit only the template ("Cut image service template 0.2.1"), and tag that commit
   `image-service-template-v0.2.1`.

## Getting fixes into apps made from an older template

- **When an app is created:** write in its README which template version it came from.
- **To update the app:**
  1. Read the changelog entries after that version.
  2. Make a patch of the template's changes between the two versions, from this repo:
     `git diff image-service-template-v0.2.0 image-service-template-v0.2.1 -- code/image_service_template > fix.patch`
  3. In the app's service folder, check that it applies, leaving out the branding:
     `git apply --check -p3 --exclude=core/brand.py --exclude="core/assets/*" fix.patch`
     Then run the same command without `--check`, and run the app's tests.
- **A fix found in an app:** if it's general, make it in `image_service` (under
  Unreleased). It reaches every app with the next release.

## Urgent fixes

Security, privacy or cost fixes get a patch release straight away instead of waiting.
One is known, and **parked for now**. It's listed under the changelog's known issues:

- `DELETE /v1/photos` ("delete everything") doesn't cancel AI jobs that are queued or
  running. They still call Gemini, which costs money, and they save their result
  afterwards.

---

## First release (0.2.0): steps

1. ✅ Rename the copy to `code/image_service_template/`, ignore its output folders, and
   add it (and the "never edit by hand" rule) to CLAUDE.md and the readme.
2. ⏸ Parked: fix the "delete everything" gap. 0.2.0 ships with it as a known issue.
3. ✅ Add `CHANGELOG.md`, set `SERVICE_VERSION = '0.2.0'`, and write `tools/cut_template.py`.
4. ✅ Cut the template, run its tests, commit, and tag `image-service-template-v0.2.0`.
5. ✅ Add the release steps to CLAUDE.md, and mark this plan as in use.

## Decisions

| Question | Decided |
| --- | --- |
| Fix the "delete everything" gap before 0.2.0? | No, it's parked. It's listed as a known issue, to fix in a later patch release |
| Where does the cut script live? | `tools/` at the repo root, so it isn't copied into apps |
