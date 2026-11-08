# Merch Style Guides

One guide per region, describing a look the merch app can recreate with anyone's face.
Each guide is built from the research in `resources/ghetto_asethetic_merch/`. Started
2026-11-08.

| Guide | Era | Status |
| --- | --- | --- |
| [New Orleans](new-orleans.md) | 1996–2001 | Draft |
| Memphis | 1991–2000 | Not started |
| Houston | 1990s–2005 | Not started |
| Compton and LA | late 1980s–1990s | Not started |

Atlanta, Miami, Detroit and New York follow once their covers are collected (see the TODO in
the research `notes.txt`).

---

## How a design comes together

A design is made from four separate processes:

| Process | What it is | Uses AI? | Made once per |
| --- | --- | --- | --- |
| **Style** | A region's scenes, colours, lettering looks and layouts: these guides | No (it's a description) | Region |
| **Likeness** | A person's face, from the guided scan or loaded photos | No (the scan is MediaPipe) | Person |
| **Artwork** | The person placed in a style's scene, with no text in it | **Yes**: the only paid step | Design |
| **Lettering** | The name, title, featuring list and sticker, drawn with fonts and graphic effects | No | Design |

The finished design is the artwork with the lettering laid on top, which is put together by
the app.

Keeping these apart means:

- **one scan works with every style:** a person is scanned once and can be put on a New
  Orleans cover, then a Houston one, with no new scan
- **a style can be improved without rescanning anyone**
- **crews are just several likenesses** in one style
- **AI only does what it's good at.** Image models garble words, so they never draw text.
  No money or time is spent regenerating pictures because a name came out misspelled
- **changing the words is free:** a new title, a fixed spelling or an extra crew member's
  name never needs a new AI image

The **artwork** step can work in different ways, and we don't have to pick one yet:

- **One AI request:** the style's prompt pieces plus the person's photos. Simplest.
- **Collage:** the AI makes the scene without the person, the person is made
  separately, and the app cuts them out and places them. Truest to how the original covers
  were made, and keeps each face in a crew strong.

### The lettering process

Done with traditional graphic design methods, the way a designer would in Photoshop:
real fonts plus layer effects (gradient fills, bevels, outlines, glows, shadows,
textures). Three ways to build it, which can be mixed:

| Way | How it works | Good for |
| --- | --- | --- |
| **Effects in code** | The app types the words in a font, then applies the effects in layers | Any words, fully automatic. The starting point |
| **Vector templates** | A treatment is designed once as a vector file (SVG) with its effects; the app swaps in the words and renders it | Sharp at any print size, so posters stay crisp |
| **Hand-made alphabets** | Every letter and number is designed once as a finished image (for example A–Z in diamonds), and the app spells words from them | The richest looks, such as ice and stone, where a font plus effects isn't enough |

Rules for lettering:

- **Fonts must be licensed for commercial use**, for example Google Fonts (Open Font
  Licence). Many "chrome" or "graffiti" fonts on free font sites are personal use only.
- **Lettering is drawn at print size**, or as vectors, so it never needs upscaling.
- **The artwork leaves room for it:** every prompt keeps the top and bottom of the picture
  clear.

The likeness test in `docs/merch-app-plan.md` will show which way works best.

---

## What every guide contains

1. **The look in one paragraph**
2. **Palette**: colours, with hex values as starting points
3. **Scenes**: the settings a design can use
4. **The person**: pose, lighting, clothing and jewellery options
5. **Lettering**: the treatments the lettering engine needs to draw
6. **Layouts**: where the person, title and names go on the square cover
7. **Finish**: the texture and effects that make it look like the era
8. **Prompt pieces**: ready-to-use text for the AI, one per scene
9. **Product notes**: how the square cover adapts to tees, hoodies, posters and phone cases
10. **Avoid**: what must never appear

## Rules for every guide

- **Describe the style, never a cover.** Covers are named in the research section of each
  guide only, to show where an idea came from.
- **Prompt pieces never name** an artist, album, label or design studio. They describe
  colours, objects, light and layout instead.
- **The AI never adds text.** Every prompt asks for no text, letters, logos or stickers.
- **The album covers are never sent to the AI**, traced or trained on.
