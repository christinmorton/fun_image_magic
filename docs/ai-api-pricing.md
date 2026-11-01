# AI API Pricing and Cost Analysis, by Provider

Detailed pricing for each AI API the photo booth might use, what each would do for us, and
estimated costs per use. Summary and event budgets: `docs/ai-costs-overview.md`.
Checked **2026-11-01**. Confidence for each price:
**(official)** from the provider's pricing page or docs; **(3rd-party)** from other sites,
treat as a lead; **(estimate)** our own calculation.

Booth units used below: one **AI image** = one 1K (about 1024 px) image made from one photo.

---

## 1. Google: Gemini "Nano Banana" image models (chosen first)

| Model (ID) | Output per image | Input | Batch output |
| --- | --- | --- | --- |
| **Nano Banana 2.1** (`gemini-nano-banana-2.1`) | **$0.0336** (1K), $0.0504 (2K), $0.113 (4K) | $1.50 / 1M tokens | $0.0168 (1K) |
| Nano Banana 2 (`gemini-3.1-flash-image`) | $0.067 (1K), $0.045 (0.5K) | $0.50 / 1M tokens | $0.034 (1K) |
| Nano Banana Pro (`gemini-3-pro-image`) | $0.134 (1K/2K), $0.24 (4K) | $2.00 / 1M tokens (~$0.0011 per input image) | $0.067 |
| Nano Banana 2 Lite (`gemini-3.1-flash-lite-image`) | $0.0336 (1K only) | $0.25 / 1M tokens | $0.0168 |

All **(official)**, from the Gemini API pricing page. Output is billed per token ($30 per 1M
image tokens for 2.1 and Lite); the per-image figures are Google's conversions.

- **Free tier:** none for these image models; the key needs billing.
- **Data:** paid-tier content is **not** used to improve Google's products **(official)**.
- **Abilities:** text and photos in, image out; up to **14 reference images**, with
  character consistency; editing over several turns; 1K/2K/4K sizes; SynthID watermark.
- **Missing:** no mask input (edits are described in words) and no transparent output.
  Our workarounds: put the original person back with our own mask, and draw cartoon Cody on
  green and remove the green.
- **Booth cost (estimate):** about **$0.035–0.04 per AI image**. A photo sent as input is a
  few hundred to about 2,000 tokens, so $0.0005–0.003.
- **Best for:** AI styles, AI backgrounds, cartoon Cody from reference photos.

---

## 2. OpenAI: GPT Image models

**Token rates (official)**, per 1M tokens:

| Model | Image input | Image output | Text input | Batch |
| --- | --- | --- | --- | --- |
| `gpt-image-2.5-sunburst` / `-flare` (current) | $8.00 | $30.00 | $5.00 | half price |
| `gpt-image-2` | $8.00 | $30.00 | $5.00 | half price |
| `gpt-image-1.5` | $8.00 | $32.00 | $5.00 | half price |
| `gpt-image-1-mini` | $2.50 | $8.00 | $2.00 | half price |

**Price per image (official legacy table**; OpenAI doesn't publish per-image prices for 2.5
yet, only "equal token rates don't mean equal cost per image"):

| Model | Size | Low | Medium | High |
| --- | --- | --- | --- | --- |
| GPT Image 2 | 1024×1024 | $0.006 | $0.053 | $0.211 |
| GPT Image 2 | 1024×1536 / 1536×1024 | $0.005 | $0.041 | $0.165 |
| GPT Image 1.5 | 1024×1024 | $0.009 | $0.034 | $0.133 |
| GPT Image 1 Mini | 1024×1024 | $0.005 | $0.011 | $0.036 |

- **Edits cost more than they look:** the photo you send is billed as image input, and
  `gpt-image-2` always reads inputs at high fidelity. Expect roughly **+$0.01–0.03 per
  edit** **(estimate)**; measure it in a trial.
- **Abilities (official guide):** real **mask** support (inpainting; it applies to the first
  image), **multiple reference images**, and **transparent backgrounds**
  (`background="transparent"`, PNG/WebP, named for the 2.5 models). Blocked requests return
  `moderation_blocked`.
- **Retirements:** `gpt-image-1` was shut down 2026-10-23 **(official)**. One site says
  `gpt-image-1-mini` retires 2026-12-01 **(3rd-party)**, so check before relying on it.
- **Booth cost (estimate):** medium **~$0.06–0.08**, high **~$0.22–0.24** per AI image;
  mini medium **~$0.012–0.016**.
- **Best for:** cartoon Cody **straight to a transparent PNG**, and precise masked edits.
  It's the natural second provider if Google's no-mask approach falls short.

---

## 3. Anthropic: Claude (supporting role only)

Claude **reads** images and writes text; it does **not** generate images. Prices from
Anthropic's current model reference (cached 2026-10-06), per 1M tokens:

| Model | Input | Output | Fit for the booth |
| --- | --- | --- | --- |
| Claude Haiku 5.5 | $0.10 | $0.50 | Fast, cheap checks on each AI image |
| Claude Sonnet 5.5 | $2.00 | $10.00 | Writing or refining prompt presets |
| Claude Opus 5.5 | $4.00 | $20.00 | Not needed at the event |

(Haiku 5.5 prices apply to prompts up to 100K tokens.)

- **Possible uses:** a safety and quality check on each AI result before it's shown ("is
  this appropriate for a college event? Does it still look like the person?"); short
  captions; drafting new style presets.
- **Booth cost (estimate):** an image of about 1,000 tokens plus a short prompt and answer
  on Haiku 5.5 is roughly **$0.0001–0.0002 per check**, or **about $0.10 for 600 images**.
- **Optional:** the booth works without it. Google and OpenAI already filter content
  themselves.

---

## 4. Candidates for a fourth, graphics-focused API

### Recraft (recommended if a fourth is added)

Official per-image API prices **(official, docs pricing page)**:

| Model | Raster | Vector (SVG) | Pro raster (2K) | Pro vector |
| --- | --- | --- | --- | --- |
| V4.1 Flash | $0.007 | n/a | n/a | n/a |
| V4.1 / V4.1 Utility | $0.035 | $0.08 | $0.21 | $0.30 |
| V4 Styles | $0.035 | $0.05 | $0.10 | $0.12 |

Tools: remove background **$0.01**, vectorize an image **$0.01**, crisp upscale $0.004,
inpainting or replace background $0.04 raster / $0.08 vector (V3 models).

- **Why it fits:** built for design work. **True vector (SVG) output**, brand **styles**
  (lock a CSN look), cheap background removal and vectorizing. Ideal for a clean
  **cartoon / vector Cody** and branded props that stay sharp at any size.
- **Booth cost (estimate):** cartoon Cody set of 40 vector attempts **≈ $3.20**, plus
  background removal $0.40. Per-photo styling **≈ $0.035–0.04**.
- **Check:** whether its style and reference features can keep Cody consistent from our
  photos (test with a few images first).

### Black Forest Labs: FLUX

- **Billing (official):** credits, 1 credit = $0.01, priced per image; FLUX 3 Image is
  priced by resolution (768², 1K, 1.5K, 2K, 4K), and FLUX.2 by megapixel. The per-model
  numbers didn't load from the official page.
- **Prices (3rd-party, unconfirmed):** FLUX 3 Image about $0.041 (768²) to $0.048
  (default); Kontext editing about $0.04–0.10 per image; one tracker reports a top-tier rise
  from $0.08 to $0.10 (May 2026).
- **Fit:** strong photo editing (Kontext / FLUX.2 edit, Fill inpainting). It overlaps with
  Google and OpenAI rather than adding something new. Check the official calculator at
  bfl.ai before choosing.

### Midjourney (not recommended)

- **No official public API** as of October 2026. Access is only through Discord or the
  website, with subscriptions of about **$10 / $30 / $60 / $120 per month** **(3rd-party)**.
- Third-party "Midjourney APIs" (about $9–49/month on top of a Midjourney plan, or about
  $0.04/request) automate an account, which Midjourney's terms reportedly prohibit, so
  there's a **risk of a banned account at the event**.
- **Verdict:** great art style, but unsuitable for an app until an official API exists.
  Use Recraft or OpenAI for the "graphics" role.

---

## Choosing, at a glance

| Need | First choice | Backup |
| --- | --- | --- |
| AI styles on student photos | Google Nano Banana 2.1 | OpenAI GPT Image 2 (medium) |
| AI backgrounds (person kept) | Google + our mask | OpenAI (real masks) |
| Cartoon / vector Cody (one-time) | Recraft (vector) or Google | OpenAI (transparent PNG) |
| Content and quality checks | Claude Haiku 5.5 (optional) | Provider's built-in filters |
| Lowest cost per image | OpenAI GPT Image 1 Mini (if still offered) | Google Nano Banana 2 Lite |
| Highest quality | OpenAI GPT Image 2 (high) | Google Nano Banana Pro |

## Sources

- [Google: Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing),
  [Nano Banana 2.1 model page](https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1),
  [image generation guide](https://ai.google.dev/gemini-api/docs/image-generation)
- [OpenAI: API pricing](https://developers.openai.com/api/docs/pricing),
  [image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- Anthropic: model pricing from the bundled Claude API reference (cached 2026-10-06)
- [Recraft: API pricing (docs)](https://www.recraft.ai/docs/api-reference/pricing)
- [Black Forest Labs: pricing docs](https://docs.bfl.ai/quick_start/pricing),
  [pricing page](https://bfl.ai/pricing),
  [costbench price change note](https://costbench.com/changelog/black-forest-labs-price-increase-2026-05/),
  [pricepertoken FLUX](https://pricepertoken.com/flux-pricing)
- Midjourney: [Wikipedia](https://en.wikipedia.org/wiki/Midjourney),
  [unifically: why there's no official API](https://unifically.com/blogs/midjourney-api),
  [apiframe alternatives](https://apiframe.ai/blog/best-midjourney-apis)
- OpenAI third-party: [aifreeapi GPT Image 1.5 pricing](https://www.aifreeapi.com/en/posts/gpt-image-1-5-pricing),
  [developersdigest OpenAI image pricing](https://www.developersdigest.tech/models/image-generation/openai)
