# Fun Image Magic

A photo booth that started as a course project on image processing (OpenCV). It grew into
a desktop booth, then an image service with AI styles. The image service is now a
**brand-neutral base**, meant to be copied into future apps.

## Where things are (2026-11-02)

| Folder | Branch | What it is |
| --- | --- | --- |
| `code/course_project/` | `master` | The original course app: sliders, kernels, greyscale |
| `code/course_project_extended/` | `photo-booth-extended` | The first photo booth, built for a college event |
| `code/course_project_enhanced/` | `photo-booth-enhanced` | The modular desktop booth: four-slot editor, masks, props, mascot poses, an AI trial |
| `code/image_service/` | `image-service` | **The reusable base.** The engine (`core/`), an HTTP API that any app can call (`api/`), and the desktop booth (`desktop/`) |
| `code/image_service_template/` | `image-service` | **Frozen template** for starting new apps: a copy of one release of the image service (see `docs/template-plan.md`) |
| `code/cover_studio/` | `cover-studio` | **Current work.** A desktop app, copied from template 0.2.0, that puts a person into 90s Southern rap album-cover art (see `docs/merch-app-plan.md`) |
| `docs/` | | Plans, reviews, pricing notes, lessons and archived records |

Each branch builds on the one before it, so `cover-studio` contains them all.

### The image service

- **Rebranding a copy:** edit `core/brand.py` (name, cheer, colours), then run
  `tools\make_assets.py`.
- **Callers:** an app's API calls it server to server, with a shared token.
- **Running it** (from `code/image_service/`):
  - Tests: `.\.venv\Scripts\python.exe -m unittest discover tests`
  - API: `.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000`, with docs at
    `/docs`
  - Desktop booth: `.\.venv\Scripts\python.exe desktop\app.py`

### The archived version (v0.1.0)

The first, college-branded version of the image service was handed to a separate web app
on 2026-11-01. It's kept, unchanged, as the git tag **`image-service-v0.1.0`** (commit
`e7602fc`).

- **To get it back:** run `git checkout image-service-v0.1.0`, then
  `git switch image-service` to return.
- **More:** `docs/desktop-to-api-lessons.md` has other ways to get it back, what changed
  after it, and what we learned from turning the desktop booth into an API service.

---

## The original idea (2026-10-30)

I want to create a fun image filter feature for a local college event. The main idea is that the students could pose with a version of their mascot or just funny picture ideas that they have at the time. I would like to get into augmented reality and 3d image manipulation as well. This is more of a fun experiement for me but it may be fun for the students too. But this is my ultimate goal of taking this course and putting the knowledge to use.

traditional image processing, filters, contrast, saturation and a few other features. This course does not cover inserting cartoon characters, 3d characters, or any generative AI.
What options are available to me to allow the students fun features and good engagement?

Your course covers more of a fun photo booth than you might expect. Here are the options, starting with what the course alone gets you.

**Tier 1: What your course covers directly**
- **Themed photo filters.** "Vintage yearbook," "neon Vegas night," "noir detective," a filter in the school's colors. These are all combinations of contrast, saturation, tint, grain and vignette, which is exactly what you're learning.
- **Branded frames and overlays.** A static border with the mascot, the event name and the date, laid over the photo. Mascot art in the corner works with simple layering and doesn't need tracking.
- **Comic and art effects.** Cartoon/posterize effects, pencil sketch, pop-art grids (four copies of the photo in different color treatments, Warhol style). Students tend to love these, and they're mostly edge detection and color reduction.
- **Photo strips.** The classic booth format: three or four shots in a row with a countdown, assembled into one strip.

**Tier 2: Small add-ons beyond the course** (pre-built tools, no AI development)
- **Face-tracked stickers.** Mascot ears, hats, glasses or face paint that follow the student's face live, like Snapchat lenses. Free face-tracking tools do the hard part.
- **Background swap.** Cut out the student and put them on the field, in front of a campus landmark, in space, or on the Strip, with no green screen needed.
- **"Pose with the mascot."** Pre-made mascot art standing on one side of the frame, so students pose next to it as if it's really there.

**Tier 3: Generative AI** (the "whatever idea they have" feature)
- **Prompt-based transformations.** A student types or picks "make me a superhero," "anime style," "medieval knight," and gets back a stylized version of their photo. This usually runs through an image-generation API or a GPU machine, and takes a few seconds per image.
- **Style presets.** A safer version of the above: a menu of 6–10 pre-tested styles, with no free typing. This matters at a college event, because free-text prompts will get tested by students looking for something inappropriate. Use presets, or put a content filter in front of free text.
- **Mascot fine-tune.** Train an AI model on your mascot so it can draw the mascot into scenes with students. More work, but it's the "wow" version.

**Tier 4: 3D and AR**
- **3D mascot in the scene.** A 3D model (which you could make in Blender) that appears next to the student, waves, or reacts.
- **AR from phones.** Students scan a QR code and the mascot appears in their own camera view, so there's no line at a single booth.

**Engagement features that matter as much as the effects:**
- **Easy sharing.** A QR code on screen so students can get their photo on their phone right away. This is probably the most important feature, because the photos end up on social media.
- **Printed photos or strips** as a physical takeaway.
- **A live gallery** or slideshow on a big screen showing photos as they're taken. It draws a crowd.
- **Contests.** "Best mascot pose" or "funniest filter," voted on by students, with a small prize.
- **Physical props.** Real hats, signs and mascot cutouts next to the digital filters. You could 3D print a few mascot-themed props yourself.

**A realistic plan:** Build Tier 1 and the sharing QR code from what you're learning now. That alone makes a solid photo booth. Add face-tracked stickers and background swap as the next step, then add AI style presets once the basic booth has worked at an event. Each tier is usable at an event on its own, so you're never stuck waiting for the hardest part.