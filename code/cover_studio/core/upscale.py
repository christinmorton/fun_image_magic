# upscale: making a picture bigger on this computer, for print, with OpenCV's
# super-resolution networks (free; no AI service). Tested on a 1K artwork made 3600 px:
# FSRCNN took 0.8 s and came out clearly sharper than a plain resize; EDSR looked only
# slightly cleaner and took 3.5 minutes. So FSRCNN ('fast') is the default and EDSR
# ('best') is there if wanted. The models live in core/models/upscale/ (fetch them once
# with tools/get_upscale_models.py). The result is resized exactly to the size asked for.
from dataclasses import dataclass

import cv2

from . import MODELS_DIR

UPSCALE_DIR = MODELS_DIR / 'upscale'


@dataclass(frozen=True)
class Model:
    name: str           # what OpenCV calls the network
    scale: int          # how many times bigger it makes a picture
    file: str
    url: str


MODELS = {
    'edsr_x2': Model('edsr', 2, 'EDSR_x2.pb', 'https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x2.pb'),
    'edsr_x4': Model('edsr', 4, 'EDSR_x4.pb', 'https://github.com/Saafke/EDSR_Tensorflow/raw/master/models/EDSR_x4.pb'),
    'fsrcnn_x4': Model('fsrcnn', 4, 'FSRCNN_x4.pb',
                       'https://github.com/Saafke/FSRCNN_Tensorflow/raw/master/models/FSRCNN_x4.pb'),
}

_loaded = {}            # model key -> a ready network (loading takes a moment)


def available(key):
    return (UPSCALE_DIR / MODELS[key].file).is_file()

def network(key):
    if key not in _loaded:
        if not available(key):
            raise FileNotFoundError(f'The {key} upscaling model is missing: run tools\\get_upscale_models.py')
        net = cv2.dnn_superres.DnnSuperResImpl_create()
        net.readModel(str(UPSCALE_DIR / MODELS[key].file))
        net.setModel(MODELS[key].name, MODELS[key].scale)
        _loaded[key] = net
    return _loaded[key]

def pick_model(factor, quality='fast'):
    # the model for making a picture `factor` times bigger: EDSR x2 or x4 for 'best',
    # FSRCNN x4 for 'fast'
    if quality == 'fast':
        return 'fsrcnn_x4'
    return 'edsr_x2' if factor <= 2 else 'edsr_x4'

def upscale(img, width, height=None, quality='fast'):
    # img made `width` x `height` pixels (height: keeps the shape if left out). Only
    # enlarging uses a network; shrinking (or a tiny change) is a plain resize
    height = height or round(img.shape[0] * width / img.shape[1])
    factor = max(width / img.shape[1], height / img.shape[0])
    if factor > 1.1:
        img = network(pick_model(factor, quality)).upsample(img)
    interpolation = cv2.INTER_AREA if img.shape[1] >= width else cv2.INTER_CUBIC
    return cv2.resize(img, (width, height), interpolation=interpolation)
