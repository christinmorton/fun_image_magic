# catalog: everything a user can choose (presets, filters, art...), described for the calling
# app, plus small PNG thumbnails of the art so the app can show picker buttons.
from dataclasses import asdict

import cv2
from pydantic import BaseModel

from core.ai import AI_PRESETS
from core.filters import KERNEL_NAMES, PRESETS
from core.look import Look
from core.masks import FOCUS_MODES
from core.slots import LAYOUTS

THUMBNAIL_SIZE = 200          # thumbnails fit inside 200 x 200, keeping their shape
ART_KINDS = ['stickers', 'backgrounds', 'frames', 'mascots', 'props']


class CatalogItem(BaseModel):
    index: int                         # the number to put in a look (e.g. "preset": 4)
    name: str
    thumbnail: str | None = None       # a /v1/... URL for the picture, when there is one

class ArtItem(CatalogItem):
    image: str                         # a /v1/... URL for the full-size picture (frames: add ?width=&height=)

class StickerItem(ArtItem):
    # where a face sticker goes, so an app can place it on faces it tracks itself
    # (core/overlays.py add_face_sticker): measured from the outer eye corners
    width_factor: float                # the sticker's width, compared to the distance between them
    lift_factor: float                 # how far above them its centre is, in the same units (negative = below)

class AiPresetItem(BaseModel):
    key: str                           # what to send to POST /v1/ai/jobs, e.g. "comic"
    name: str
    kind: str                          # "style" or "background"

class Catalog(BaseModel):
    presets: list[CatalogItem]
    filters: list[CatalogItem]         # the course's convolution kernels (look "kernel")
    focus_modes: list[CatalogItem]     # look "focus"; 0 = off
    layouts: list[CatalogItem]         # for strips and grids
    stickers: list[StickerItem]        # look "sticker"; -1 = off
    backgrounds: list[ArtItem]         # look "background"; -1 = off
    frames: list[ArtItem]              # look "frame"; -1 = off
    mascots: list[ArtItem]             # look "mascot" (mascot poses); -1 = off
    props: list[ArtItem]               # "prop" inside each entry of look "props"
    ai_presets: list[AiPresetItem]     # for POST /v1/ai/jobs
    off: int = -1                      # the value that switches a sticker, background, frame or mascot off
    look_defaults: dict                # a look with nothing changed


def art_images(art, kind):
    # the pictures behind one kind of art, in catalog order
    return {
        'stickers': [img for img, _, _ in art.stickers],
        'backgrounds': art.backgrounds,
        'frames': art.frames,
        'mascots': art.mascots,
        'props': art.props,
    }[kind]

def build_catalog(art):
    def items(names):
        return [CatalogItem(index=i, name=name) for i, name in enumerate(names)]
    def art_items(names, kind, item=ArtItem, extra=lambda i: {}):
        return [item(index=i, name=name, thumbnail=f'/v1/catalog/{kind}/{i}/thumbnail.png',
                     image=f'/v1/catalog/{kind}/{i}/image.png', **extra(i))
                for i, name in enumerate(names)]
    def placement(i):
        _, width_factor, lift_factor = art.stickers[i]
        return {'width_factor': width_factor, 'lift_factor': lift_factor}
    return Catalog(
        presets=items([name for name, _ in PRESETS]),
        filters=items(KERNEL_NAMES),
        focus_modes=items(FOCUS_MODES),
        layouts=items([layout.lower() for layout in LAYOUTS]),
        stickers=art_items(art.sticker_names, 'stickers', StickerItem, placement),
        backgrounds=art_items(art.background_names, 'backgrounds'),
        frames=art_items(art.frame_names, 'frames'),
        mascots=art_items(art.mascot_names, 'mascots'),
        props=art_items(art.prop_names, 'props'),
        ai_presets=[AiPresetItem(key=p.key, name=p.name, kind=p.kind) for p in AI_PRESETS],
        look_defaults={**asdict(Look()), 'props': []},
    )

def full_png(img):
    # the picture at full size, as PNG, keeping transparency
    ok, png = cv2.imencode('.png', img)
    return png.tobytes()

def thumbnail_png(img):
    # shrink to fit THUMBNAIL_SIZE (never enlarge) and encode as PNG, keeping transparency
    scale = min(1.0, THUMBNAIL_SIZE / max(img.shape[:2]))
    small = cv2.resize(img, (max(round(img.shape[1] * scale), 1), max(round(img.shape[0] * scale), 1)),
                       interpolation=cv2.INTER_AREA)
    ok, png = cv2.imencode('.png', small)
    return png.tobytes()
