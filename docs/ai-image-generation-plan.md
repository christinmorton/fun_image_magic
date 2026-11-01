# AI Image Generation: Exploration Notes

Notes for adding AI image generation to the enhanced photo booth
(`code/course_project_enhanced/`). This is Roadmap Part 2, Step 13 (`docs/expansion-roadmap-part-2.md`).
Written 2026-10-31 to pick up in a later session. **No code has been written yet.**

**Decision (2026-11-01): start with cloud APIs (larger models), not a local install.**
The local notes below stay for reference. Before AI, the plan is masking and scene props
(`docs/enhanced-plan.md`, steps 5–6).

## Provider chosen: Google Nano Banana 2.1 (from Google's docs, 2026-11-01)

- **Model** `gemini-nano-banana-2.1` (stable, updated Oct 2026). Text, image or PDF in;
  image and text out. Up to 14 reference images, with character consistency.
- **Price** $0.0336 per 1K image ($0.0504 at 2K); input $1.50 per 1M tokens. Batch costs
  about half. **No free tier** for image models, so the key needs billing. On the paid tier,
  Google does **not** use content to improve its products.
- **Python** library `google-genai` (2.34.0, in `requirements.txt`). Uses
  `client.interactions.create(model=..., input=[text and base64 images],
  response_format={'type': 'image', 'aspect_ratio': ..., 'image_size': '1K'})`; the image
  comes back base64 in `interaction.output_image.data`.
- **No mask input:** edits are described in words ("change only the background"). Plan:
  ask for the background, then put the **original person back on top** with our own mask
  (step 5), so faces are never altered.
- **No transparent output:** cartoon Cody is drawn on bright green, then the green is removed
  (a chroma key), giving a transparent prop.
- Every output carries an invisible **SynthID** watermark.
- **Trial ready:** `experiments/ai_trial.py photo.jpg` makes a comic style, a Vegas
  background (plus a person-kept version) and a cartoon Cody. About $0.10–0.15 per run.
  Checked offline with a fake client. Outputs go to `experiments/output/` (ignored by git).
- **First real run (2026-11-01, about 1 minute, about $0.10):** comic style excellent, with
  likeness, layout and text kept. Cartoon Cody excellent and on-brand; the green edges were
  fixed by adding a "despill" step. The AI background was photo-realistic, **but the model
  reframed the picture**, so putting the original person back made ghost copies. In the app:
  send only the unedited **slot photo** (frames and props go on afterwards, so branding stays
  exact), and only put the person back when the AI kept them in the same place (check that the
  two person masks overlap); otherwise use the AI image as it is.

---

## Starting point

- The enhanced app is split into modules (`look.py`, `slots.py`, `tracking.py`, …) and
  has a four-slot editor (`docs/enhanced-plan.md`, step 4). Branch: `photo-booth-enhanced`.
- The app already makes a **person mask** with MediaPipe's selfie segmenter
  (`tracking.py`, `Tracker.analyse_still()` for slot photos). AI backgrounds can reuse it.
- Event rules from `readme.md`: **preset prompts only (no free typing)**, consent at the booth,
  and a plan for deleting photos.

---

## The laptop (checked 2026-10-31)

| Part | Value |
| --- | --- |
| Graphics card | NVIDIA GeForce RTX 4060 Laptop GPU, **8 GB** graphics memory (VRAM) |
| CPU | AMD Ryzen 7 7435HS, 8 cores |
| RAM | 64 GB |
| Python (app venv) | 3.15.2 |

**What 8 GB means:** the mid-size open models (Stable Diffusion 1.5 / SDXL family) run,
SDXL with memory-saving options (half-precision weights, moving parts of the model to RAM
when not in use). The newest large models (e.g. FLUX.2 dev, 19 GB+) are not practical here.

### PyTorch availability (checked with `pip index versions`)

| Build | Python 3.15 | Python 3.14 |
| --- | --- | --- |
| PyPI default (on Windows, usually CPU-only: too slow) | 2.15.0 | 2.15.0 |
| CUDA 12.6 index (`/whl/cu126`) | 2.14.1 | 2.14.1 |
| CUDA 13.0 index (`/whl/cu130`) | 2.14.1 | 2.14.1 |
| CUDA 13.2 index (`/whl/cu132`) | **2.15.0** | 2.15.0 |
| CUDA 12.8 / 12.9 / 13.1 | none | older versions only |

`diffusers` (the Hugging Face library for these models) is at **0.42.1** for Python 3.15.
So local generation can live in the app's own venv. Check which CUDA version the
graphics driver supports (`nvidia-smi`) before picking the index.

Download size: about 3 GB for PyTorch with CUDA, plus 2–7 GB per model.

---

## Option A: local (on the RTX 4060)

- **Cost:** free after the downloads.
- **Privacy:** students' photos never leave the laptop.
- **Internet:** not needed at the event.
- **Quality:** good, but not the newest models.
- **Speed:** to be measured. Estimated at a few seconds per image with the faster
  (few-step) models.
- **Setup:** big install; some tuning of memory and steps.
- **Licences:** check each model's licence. Some fast models allow only non-commercial use,
  which is probably fine for a college event but needs confirming.

Model families to try (verify current names, licences and memory needs on the
Hugging Face model cards first):

- **Image-to-image (styles):** a fast few-step model (SD-Turbo / SDXL-Turbo type) and
  a standard SD 1.5 or SDXL model.
- **Inpainting (backgrounds):** an SD 1.5 inpainting model, or SDXL inpainting with
  memory-saving options.

## Option B: cloud API (OpenAI, Google, Stability, …)

- **Cost:** per image. Reported prices range from about **$0.04 to $0.15** per generated
  or edited image, but sources disagree. **Check each provider's official pricing page.**
- **Privacy:** photos are sent to the provider. Needs a consent sign, and a check of
  the provider's data-retention terms.
- **Internet:** required at the event, so keep the non-AI booth as a fallback.
- **Quality:** the best available.
- **Setup:** an API key and a few lines of code.
- **Watch for:** model retirements. One source reports Google retiring Imagen 4 on the
  Gemini API on 2026-08-17, replaced by the "Nano Banana" line. Verify before choosing.

## Recommendation so far

*Superseded on 2026-11-01:* cloud APIs first. The original recommendation was to start
local (free, private, works offline), with cloud added behind the same keys and menu.
That design (one interface, either backend) still applies, so local can be added later.

Cloud-first adds these to-dos:

- **API key:** kept out of git (an environment variable, or an ignored `.env` file).
- **Cost:** a per-image cost, so set a spending limit with the provider.
- **Privacy:** photos leave the laptop. Needs a consent sign and a check of the provider's
  data terms.
- **Internet:** needed at the event, so keep the non-AI booth as a fallback.

---

## How AI fits the app

AI takes seconds per image, so it can't run on every live video frame like the
presets. It belongs in the **four-slot editor**:

- Pick a slot, press a key (for example `G`), and choose an AI preset.
- A "Generating…" message shows while it runs in the background, so the window doesn't
  freeze.
- The result **replaces that slot's photo**. The original is kept, so it can be undone.

### Feature 1: AI styles (image-to-image)

Restyle the whole photo but keep the person recognisable. Preset menu ideas:
comic book, anime, oil painting, superhero, Las Vegas neon, CSN Coyotes poster.
Likeness depends on the "strength" setting (how far the result moves from the photo):
tune it in the trial.

### Feature 2: AI backgrounds (inpainting)

Keep the person exactly as they are and let AI paint a new scene around them. Preset
ideas: on the Las Vegas Strip at night, on the CSN basketball court, in outer space,
at Red Rock Canyon. The mask comes from the existing selfie segmenter, inverted so
the AI paints only the background.

### Feature 3: cartoon Cody (added 2026-11-01)

A cartoon or vector-style Cody made with AI, so students can "pose with Cody" even
without a photo cut-out. The Photoshop cut-outs stay, and more can be added later.

Ways to do it, roughly simplest first:

1. **Make a cartoon Cody pose set once, ahead of time (recommended start).** Give a cloud
   model the Cody photos or cut-outs as **reference images**, with a style prompt (for
   example "flat vector cartoon mascot, the same coyote, CSN blue jersey"). Generate a
   handful of poses (waving, cheering, thumbs up, holding a "GO CSN!" sign). Keep the best
   ones, remove their backgrounds, and save them as transparent PNGs in `assets/props/`.
   They then work like any other **scene prop** (`docs/enhanced-plan.md`, step 6): placed
   and moved by hand, free to use, instant, and checked for quality before the event.
2. **Generate cartoon Cody live, per photo.** Ask the API to add cartoon Cody into a
   student's photo (reference images + the photo, with a mask for where he goes). More
   magical, but it costs per image, is slower, and is less predictable.
3. **A "trained" Cody model.** Fine-tune an image model on Cody images (for example a
   LoRA trained on a cloud service), so it can draw Cody in any pose on demand. This gives
   the most consistent character, but it's the most work and cost, and it needs a good
   set of training images. Worth it only if options 1–2 aren't consistent enough.

Things to check:

- **Brand permission:** Cody and the CSN marks belong to the college. Get permission for
  AI-made versions, and for uploading Cody images to a provider.
- **Provider terms:** whether reference images may be used for consistent characters, and
  who owns the outputs.
- **Consistency:** compare the generated poses side by side; a character that drifts
  between poses looks off-brand.

### Design notes

- A new `ai.py` module, **imported only when AI is first used**, so the booth starts fast
  and still works without the AI install.
- One small interface (for example `generate(image, preset, mask=None) -> image`), with a
  local version first and a cloud version possibly later.
- Run generation in a background thread; show progress and "Generating…".
- Keep presets in one list (name + prompt + strength), like `STICKERS` and `PRESETS`.
- Cache results per slot and preset, so switching back doesn't regenerate.
- Never free-text prompts at the event. Consider a safety checker on the output.

---

## Proposed order of work

Updated 2026-11-01 for cloud first:

0. **Before AI:** masking and scene props (`docs/enhanced-plan.md`, steps 5–6).
1. **Choose a provider:** compare current official pricing, image-editing and
   reference-image support, and data terms. Set up an API key and a spending limit.
2. **Trial script (no app changes):** send the test portrait
   (`storage.googleapis.com/mediapipe-assets/business-person.png`) with a few style
   prompts, plus one masked background edit. Record cost, time and likeness.
3. **Cartoon Cody pose set:** generate a set with reference images, pick the best, remove
   backgrounds, and add them to `assets/props/`.
4. **`ai.py` + AI styles in the editor** (background thread, "Generating…", undo).
5. **AI backgrounds** with the cleaned-up person mask.
6. *(Later)* live cartoon Cody per photo, a trained Cody model, or a local backend.
7. **Docs and tests:** update the plans, and add unit tests that use a fake generator,
   so they need no internet or API key.

---

## Open decisions

| # | Question | Leaning |
| --- | --- | --- |
| 1 | Local, cloud, or both? | **Decided: cloud first** (local possible later) |
| 2 | AI styles, AI backgrounds, or both? | Both, styles first |
| 3 | Is a 5–10 GB install acceptable? | Not needed for cloud |
| 4 | Editor only, or also camera mode? | Editor only |
| 5 | Which cloud provider? | Decide after checking current official pricing, reference-image support and data terms |
| 6 | Cartoon Cody: pre-made set, live, or trained? | Pre-made set first (as scene props) |
| 7 | Permission to make AI versions of Cody | To ask CSN |

---

## Sources

Search results were thin and partly unreliable; verify before relying on any number.

- [Fooocus 2026 guide: hardware requirements](https://www.promptzone.com/sofia_tahir/fooocus-2026-the-complete-guide-to-ai-image-generation-355l.md)
- [AI inpainting hardware guide](https://jisaku.com/posts/ai-image-inpainting-guide)
- [SDXL inpainting model on Hugging Face](https://huggingface.co/diffusers/stable-diffusion-xl-1.0-inpainting-0.1/tree/main)
- [ComfyUI DiffusersImageOutpaint: memory-saving data point](https://comfyonline.app/comfyui-nodes/ComfyUI-DiffusersImageOutpaint)
- [AI image model pricing, August 2026 (invideo)](https://invideo.io/blog/ai-image-model-pricing/)
- [AI image API pricing 2026 (apiframe)](https://apiframe.ai/blog/ai-image-api-pricing-2026)
- [AI image generation API pricing (tkmxai; many near-duplicate pages, low reliability)](https://www.tkmxai.it.com/ai-image-generation-api-pricing-in-2026)
