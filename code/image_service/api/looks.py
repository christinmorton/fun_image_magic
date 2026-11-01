# looks: the JSON form of a look (all the settings for one photo), checked before use, and
# turning a finished picture into PNG/JPEG bytes for the response.
from typing import Literal

import cv2
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.filters import KERNELS, PRESETS
from core.look import Look
from core.masks import FOCUS_MODES
from core.props import MAX_SIZE, MIN_SIZE, PlacedProp


class PropIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    prop: int = Field(ge=0, description='Catalog "props" index')
    x: float = Field(0.5, ge=0, le=1, description='Centre, as a fraction of the photo width (0 = left)')
    y: float = Field(0.5, ge=0, le=1, description='Centre, as a fraction of the photo height (0 = top)')
    size: float = Field(0.5, ge=MIN_SIZE, le=MAX_SIZE, description='Height, as a fraction of the photo height')

class LookIn(BaseModel):
    # the same settings as the desktop sliders; anything left out keeps its default
    model_config = ConfigDict(extra='forbid')      # a misspelt setting is an error, not ignored
    contrast: float = Field(1.0, ge=0, le=3, description='1.0 = no change')
    brightness: int = Field(50, ge=0, le=100, description='50 = no change')
    kernel: int = Field(0, ge=0, lt=len(KERNELS), description='Catalog "filters" index')
    grayscale: int = Field(0, ge=0, le=1)
    preset: int = Field(0, ge=0, lt=len(PRESETS), description='Catalog "presets" index')
    sticker: int = Field(-1, ge=-1, description='Catalog "stickers" index, -1 = off')
    background: int = Field(-1, ge=-1, description='Catalog "backgrounds" index, -1 = off')
    mascot: int = Field(-1, ge=-1, description='Catalog "mascots" index (Cody poses), -1 = off')
    frame: int = Field(-1, ge=-1, description='Catalog "frames" index, -1 = off')
    focus: int = Field(0, ge=0, lt=len(FOCUS_MODES), description='Catalog "focus_modes" index, 0 = off')
    props: list[PropIn] = Field(default_factory=list, max_length=20, description='Last one is on top')


class ImageOptions(BaseModel):
    format: Literal['png', 'jpeg'] = 'png'
    quality: int = Field(90, ge=40, le=100, description='JPEG quality')
    max_width: int | None = Field(None, ge=64, le=4096, description='Shrink the result to this width (never enlarges)')


def to_core_look(look, art):
    # check the numbers that depend on the art library, then build the core Look
    def check(name, value, count):
        if value >= count:
            raise HTTPException(422, f'look.{name} is {value}, but there are only {count} '
                                     f'(use 0-{count - 1}, or -1 for off)')
    check('sticker', look.sticker, len(art.stickers))
    check('background', look.background, len(art.backgrounds))
    check('mascot', look.mascot, len(art.mascots))
    check('frame', look.frame, len(art.frames))
    for i, placed in enumerate(look.props):
        if placed.prop >= len(art.props):
            raise HTTPException(422, f'look.props[{i}].prop is {placed.prop}, but there are only {len(art.props)} props')
    return Look(contrast=look.contrast, brightness=look.brightness, kernel=look.kernel,
                grayscale=look.grayscale, preset=look.preset, sticker=look.sticker,
                background=look.background, mascot=look.mascot, frame=look.frame, focus=look.focus,
                props=tuple(PlacedProp(p.prop, p.x, p.y, p.size) for p in look.props))

def encode_image(img, options):
    # a finished picture -> (bytes, media type), shrunk to max_width if asked
    if options.max_width and img.shape[1] > options.max_width:
        scale = options.max_width / img.shape[1]
        img = cv2.resize(img, (options.max_width, max(round(img.shape[0] * scale), 1)), interpolation=cv2.INTER_AREA)
    if options.format == 'jpeg':
        ok, data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, options.quality])
        return data.tobytes(), 'image/jpeg'
    ok, data = cv2.imencode('.png', img)
    return data.tobytes(), 'image/png'
