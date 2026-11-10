# Photo Checks

Guidelines for checking a buyer's photos before any design is made, so the shop never puts
a celebrity, public figure or someone who didn't agree on a product. Written 2026-11-09.

Do these checks **before** loading the photos into Cover Studio. They're free, and they
come before the AI is paid for.

## Why it matters

- **A person's likeness is protected.** Selling merch with a famous person's face on it can
  bring legal claims, and Etsy takes listings down over it.
- **Everyone has a say over their own face,** not just celebrities. That's why every listing
  asks the buyer to confirm that everyone pictured is an adult who agreed.
- **Lookalikes are fine.** A buyer who resembles someone famous is putting their own face
  on the shirt.

## The checklist (every photo order)

1. **Are they real selfies?** Three photos of the same person, straight on and turned each
   way, in the same light and place. Phone-camera quality, everyday background.
2. **Reverse image search the front photo.** Upload it to [Google Lens](https://lens.google.com)
   or [TinEye](https://tineye.com). If it turns up online with a famous person's name, stop.
   About 30 seconds per order.
3. **Check the words.** Read the name, title and featuring list in the personalization.
   A famous artist's name, a record label or a brand means asking the buyer about it.
   Cover Studio also refuses real artist, label and brand names typed into the scene
   details (`check_user_text` in `core/styles.py`).
4. **Is everyone an adult?** Anyone who looks under 18 means asking. No minors on designs.
5. **Crew orders: does everyone know?** Each person on a crew cover should have agreed.
   When one buyer sends photos of several people, ask them to confirm it.

Only once all five pass, load the photos into Cover Studio (scan screen, P).

## Red flags

Ask for new photos, or decline, when you see:

- **Professional-looking photos:** studio lighting, a stage, a red carpet, a magazine-style
  crop, a watermark, or a press or event backdrop.
- **Only one photo,** with excuses for why the others can't be sent, when the face looks
  familiar.
- **Photos that don't match:** different ages, hairstyles or lighting that suggest they came
  from different places online.
- **A screenshot,** with phone or app bars, or a blurry, low-resolution face cropped from a
  bigger picture.
- **Words that point to a real artist:** a famous rapper's name or album title, or "make it
  look like ___'s cover."
- **Someone who seems to be under 18.**

## What to say

**Asking for real selfies:**

> Thanks for the photos! For the best likeness I need 3 fresh selfies taken on your phone:
> one looking straight at the camera, and one with your head turned a little each way.
> Good light on your face, no sunglasses or hats. Professional or downloaded photos don't
> work as well for the design.

**When a photo is a public figure:**

> Sorry, I can't make designs of celebrities or public figures, so I'm not able to fill this
> one. I've cancelled the order and you'll get a full refund. I'd love to make one of you
> instead if you'd like!

**When the words name a real artist, label or brand:**

> I can't use real artist, label or brand names on designs. Could you pick a different name
> or title? Anything original works great.

**Asking about age:**

> Just checking: is everyone in the photos 18 or older? I can only make designs of adults.

Cancel through Etsy so the refund is handled properly, and keep the messages in case Etsy
asks about the order.

## After the order

- Delete the buyer's photos (the subject folder in `subjects/`) once the order ships, as
  the listings promise.
- Keep the order's messages in Etsy, not copies of the photos.

## Later: automatic checks

At hand-made scale the checklist is enough. If orders grow, the reverse image search and
face checks could be automated:

- **Amazon Rekognition** can recognise celebrities' faces, for a fraction of a cent per
  photo. Google's and Microsoft's versions are only open to approved customers.
- **The catches:** every buyer's face would go to another company (the privacy policy must
  say so), some places, such as Illinois, have strict laws on processing face data, and it
  needs an AWS account and some code.
- **A guided video** instead of selfies (the scanner picking frames from a short head-turn
  video) would make faked photos much harder to send.

Google's image model also has its own filters for well-known people, but don't rely on
them: they're not a check, just a backstop.
