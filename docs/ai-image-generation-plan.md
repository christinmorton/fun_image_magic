# AI Image Generation: Exploration Notes

Notes for adding AI image generation to the enhanced photo booth
(`code/course_project_enhanced/`). This is Roadmap Part 2, Step 13 (`docs/expansion-roadmap-part-2.md`).
Written 2026-10-31 to pick up in a later session. **No code has been written yet.**

Current position: **both local and cloud options are still open.**

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

Start **local** (free, private, works offline), but write the code so **cloud can be
added behind the same keys and menu**. Both stay open. Decide after the speed and
quality trial (step 1 below).

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

1. **Speed and quality trial (no app changes):** a stand-alone script that runs two or
   three candidate models on the test portrait
   (`storage.googleapis.com/mediapipe-assets/business-person.png`). Record seconds per
   image, graphics memory used, and how well the person stays recognisable. Pick the
   models.
2. **`ai.py` + AI styles in the editor.**
3. **AI backgrounds** with the person mask.
4. *(Optional)* **Cloud version** behind the same interface, for comparison or as a
   higher-quality mode.
5. **Docs and tests:** update `docs/enhanced-plan.md`, and add unit tests that use a fake
   generator so they don't need the GPU.

---

## Open decisions

| # | Question | Leaning |
| --- | --- | --- |
| 1 | Local, cloud, or both? | Both open; start local, keep cloud possible |
| 2 | AI styles, AI backgrounds, or both? | Both, styles first |
| 3 | Is a 5–10 GB install acceptable? | To confirm |
| 4 | Editor only, or also camera mode? | Editor only |
| 5 | Which cloud provider, if any? | Decide after checking current official pricing and data terms |
| 6 | Same venv, or a separate one for AI? | Same venv looks possible (CUDA builds exist for 3.15) |

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
