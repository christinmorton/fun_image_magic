# AI API Costs: Overview

What the CSN photo booth (`code/course_project_enhanced/`) would spend on paid AI APIs, and
how to keep that under control. Prices were checked on **2026-11-01** and change often;
re-check the providers' pricing pages before an event. Per-provider detail:
`docs/ai-api-pricing.md`.

---

## The short version

- **Everything except AI is free.** Presets, stickers, background swap, masks, props and the
  editor all run on the laptop.
- **AI costs a few cents per image, and only when someone presses the AI key.** There are no
  subscriptions or monthly fees with the recommended providers.
- **Expected event cost with Google Nano Banana 2.1:** about **$15–25 for 200 students**
  (2 AI images each, plus retries).
- **One-time costs** (testing and a cartoon Cody pose set): about **$5–15**.
- **Set a spending cap** at the provider and in the app (see "Keeping costs under control").

---

## What the system would use paid APIs for

| Use | When | Provider (plan) | Typical cost |
| --- | --- | --- | --- |
| **AI styles**: restyle a slot photo (comic, anime, poster…) | At the event, per press | Google Nano Banana 2.1 | ~$0.035–0.04 per image |
| **AI backgrounds**: new scene, original person put back on top | At the event, per press | Google Nano Banana 2.1 | ~$0.035–0.04 per image |
| **Cartoon Cody pose set**: made once, saved as props | Before the event | Google (or OpenAI / Recraft) | ~$1–5 for the whole set |
| **Checking outputs** *(optional)*: e.g. "is this image appropriate?" | At the event, per AI image | Anthropic Claude Haiku 5.5 | ~$0.0002 per check |
| **Testing and tuning prompts** | During development | Google | ~$0.10–0.15 per trial run |

Claude reads images but doesn't create them, so it can only play a supporting role (checks,
captions, writing prompt presets). OpenAI and Google both create and edit images.

---

## Cost per AI image, side by side (1K / 1024 px images)

| Provider and model | Cost per image | Notes |
| --- | --- | --- |
| **Google Nano Banana 2.1** | **$0.0336** + small input cost | Recommended start. Up to 14 reference images |
| Google Nano Banana 2 Lite | $0.0336 | Not suited to editing with references |
| Google Nano Banana Pro | $0.134 | Higher quality, 4× the price |
| OpenAI GPT Image 2 (medium) | $0.053 + input-image cost | Supports masks and transparent backgrounds |
| OpenAI GPT Image 2 (high) | $0.211 | Best OpenAI quality |
| OpenAI GPT Image 1 Mini (medium) | $0.011 | Cheapest; check it's still offered |
| Recraft V4.1 (raster / vector SVG) | $0.035 / $0.08 | Best fit for cartoon / vector Cody |
| FLUX (Black Forest Labs) editing | ~$0.04–0.10 *(unconfirmed)* | Check the official calculator |
| Midjourney | Subscription $10–120/month | **No official API**; not recommended |

"Input cost" is what the photo you send costs to read: well under a cent per request for
Google, and up to a few cents for OpenAI, which reads input images at high fidelity.

---

## Event scenarios (Google Nano Banana 2.1)

Assumes about $0.037 per AI image (output plus input) and a **1.5× retry factor**, because
some results get regenerated.

| Scenario | AI images | Estimated cost |
| --- | --- | --- |
| Small test event: 30 people × 2 AI images | 60 × 1.5 = 90 | **~$3.50** |
| Club event: 100 people × 2 | 300 | **~$11** |
| Campus event: 200 people × 2 | 600 | **~$22** |
| Big day: 500 people × 3 | 2,250 | **~$83** |

Same 200-person campus event with other providers (600 images):

| Provider | Estimated cost |
| --- | --- |
| Google Nano Banana 2.1 | ~$22 |
| OpenAI GPT Image 1 Mini (medium) | ~$7–10 |
| Recraft V4.1 raster | ~$21–25 |
| OpenAI GPT Image 2 (medium) | ~$35–42 |
| Google Nano Banana Pro | ~$80–85 |
| OpenAI GPT Image 2 (high) | ~$130–140 |

Optional Claude Haiku 5.5 check on each AI image: about **$0.12** for all 600.

### One-time costs

| Item | Estimate |
| --- | --- |
| Development and trial runs (about 50–100 test images) | $2–5 |
| Cartoon Cody pose set (about 40 attempts → 6–8 keepers) | $1.50 (Google) to $3.50 (Recraft vector) |
| Batch generation for pre-made art (half price, takes hours) | Halves the above |

---

## Keeping costs under control

1. **A provider spending limit:** a budget alert in Google Cloud billing (and in OpenAI's
   dashboard, if used). This is the hard safety net.
2. **An app-level cap** (to build with the AI step): count AI images per session and per
   day, and stop with a friendly message at a set number (for example 600 per event).
3. **AI only on request:** never on live video; only when someone presses the AI key in the
   editor.
4. **Cache results:** switching back to a slot never regenerates; only a new request costs.
5. **1K images:** enough for a photo booth. 2K costs about 50% more; 4K about 3×.
6. **Pre-make what can be pre-made:** cartoon Cody and other art are generated once (with the
   half-price batch API) and reused as free props.
7. **A fallback:** if the internet or budget runs out, the non-AI booth keeps working.

---

## Other things to plan for

- **Billing:** Google's image models have **no free tier**, so a paid key is required.
- **Privacy:** photos are sent to the provider. Google's paid tier doesn't use them to
  improve its products. Use a consent sign at the booth and delete photos after the event.
- **Watermarks:** Google and OpenAI images carry invisible provenance watermarks (SynthID /
  C2PA). That's normal and harmless for a photo booth.
- **Brand permission:** ask CSN before making AI versions of Cody and the CSN marks.
- **Prices change:** these figures are a snapshot (2026-11-01).
