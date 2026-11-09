# products: turning a saved design into a print file for each product - a poster, a
# t-shirt, a hoodie and a phone case. The artwork is upscaled for print (core/upscale.py)
# and the lettering redrawn at full size from the design's recipe, so nothing is
# stretched. Files go to exports/<design>/ (kept on this machine) as 300 dpi PNGs, with a
# sheet of mockups. The print sizes are common print-on-demand sizes, to confirm with
# whichever provider is chosen.
from dataclasses import dataclass, replace

import cv2
import numpy as np
from PIL import Image

from . import CORE_DIR
from .cover_layout import CoverLayout, Spot, apply_lettering, draw_cover_lettering, placeholder, square_crop
from .designs import load_recipe
from .finish import age
from .framing import Framing, blurred_fill, frame_artwork
from .mockups import mockup_sheet
from .upscale import upscale

EXPORTS_DIR = CORE_DIR.parent / 'exports'
DPI = 300


@dataclass(frozen=True)
class Product:
    key: str                # also the file name
    name: str
    width: int              # the print file, in pixels at DPI
    height: int
    kind: str               # 'poster' (filled edge to edge), 'garment' (see-through around the
                            # cover) or 'case' (its own tall layout)


PRODUCTS = [
    Product('poster', 'Poster, 18 x 24 in', 5400, 7200, 'poster'),
    Product('tee', 'T-shirt front, 15 x 18 in', 4500, 5400, 'garment'),
    Product('hoodie', 'Hoodie front, 14 x 12 in (above the pocket)', 4200, 3600, 'garment'),
    Product('phone', 'Phone case, tall', 1500, 3000, 'case'),
]
PRODUCTS_BY_KEY = {p.key: p for p in PRODUCTS}

# the phone case's tall layout. The top fifth is kept for the camera (top left on most
# phones), so the name sits below it, then the artwork, then the title; no featuring list
# or presents line (too small to read on a case)
CASE_CAMERA = 0.21                  # the top part of the case the camera covers
CASE_ART_TOP = 0.33                 # where the artwork starts (it's as tall as the case is wide)
CASE_LAYOUT = CoverLayout('case', 'Phone case', {
    'name': Spot(0.05, 0.215, 0.9, 0.11),
    'sticker': Spot(0.06, 0.745, 0.4, 0.06, align='left'),
    'title': Spot(0.05, 0.84, 0.9, 0.13),
}, {'name': 'gold', 'title': 'ice'})


@dataclass
class Design:
    folder: object
    recipe: dict
    artwork: object         # BGR, or None (the placeholder)


def load_design(folder):
    art = cv2.imread(str(folder / 'artwork.png')) if (folder / 'artwork.png').exists() else None
    return Design(folder, load_recipe(folder), art)

def artwork_at(design, side, quality='fast', framed=True):
    # the design's artwork, upscaled to side x side, moved and zoomed as the design says
    # (framed=False: as the AI made it) and aged with its finish
    r = design.recipe
    if design.artwork is None:
        art = placeholder(side, 4 if r['layout'] == 'crew_row' else 1)
    elif framed:
        art = frame_artwork(design.artwork, side, Framing(**r['framing']), quality)
    else:
        art = upscale(square_crop(design.artwork), side, side, quality)
    return age(art, r['finishes'].get('artwork', 'clean'), r['strength'], r['seed'], unit_size=side)

def cover_at(design, side, quality='fast'):
    # the whole cover, side x side: aged artwork with the lettering redrawn at that size
    r = design.recipe
    lettering = draw_cover_lettering(r['words'], r['layout'], side, r['styles'], r['seed'], r['finishes'], r['strength'])
    return apply_lettering(artwork_at(design, side, quality), lettering)

def make_product(product, design, quality='fast'):
    # the print file for one product: BGR (poster, case) or BGRA (garments, see-through
    # around the cover)
    w, h = product.width, product.height
    if product.kind == 'garment':
        side = min(w, h)
        out = np.zeros((h, w, 4), np.uint8)
        x = (w - side) // 2
        out[:side, x:x + side, :3] = cover_at(design, side, quality)
        out[:side, x:x + side, 3] = 255
        return out
    if product.kind == 'poster':
        cover = cover_at(design, w, quality)
        out = blurred_fill(cover, w, h)
        y = (h - w) // 2
        out[y:y + w] = cover
        return out
    # case: the artwork in the middle over its own blurred fill, then the tall layout's
    # lettering (its name sits above the artwork, so the artwork isn't moved)
    r = design.recipe
    art = artwork_at(design, w, quality, framed=False)
    out = blurred_fill(art, w, h)
    y = int(h * CASE_ART_TOP)
    out[y:y + w] = art
    words = replace(r['words'], featuring=(), presents='')
    layout = replace(CASE_LAYOUT, styles={**CASE_LAYOUT.styles, **{k: v for k, v in r['styles'].items() if k in ('name', 'title')}})
    lettering = draw_cover_lettering(words, layout, (w, h), r['styles'], r['seed'], r['finishes'], r['strength'])
    return apply_lettering(out, lettering)

def save_png(path, img, dpi=DPI):
    # a PNG that says it's `dpi` dots per inch, so print services size it right
    if img.shape[2] == 4:
        picture = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGRA2RGBA))
    else:
        picture = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    picture.save(str(path), dpi=(dpi, dpi))

def export_products(design_folder, keys=None, exports_dir=EXPORTS_DIR, quality='fast', progress=None):
    # every product's print file (or those in `keys`) and a mockup sheet, in
    # exports/<design>/; returns that folder. progress(text) hears about each step
    design = load_design(design_folder)
    out = exports_dir / design_folder.name
    out.mkdir(parents=True, exist_ok=True)
    made = {}
    for product in PRODUCTS:
        if keys and product.key not in keys:
            continue
        if progress:
            progress(f'Making the {product.name.split(",")[0].lower()}...')
        made[product.key] = make_product(product, design, quality)
        save_png(out / f'{product.key}.png', made[product.key])
    cv2.imwrite(str(out / 'mockups.jpg'), mockup_sheet(made), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return out
