# Checks that the browser booth (web/) still matches core/: the same presets, filters, look
# defaults and brand colours, and a live shader for every preset. The JavaScript copies are
# kept by hand, so this catches a preset added here but not there.
# Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import re
import sys
import unittest
from dataclasses import asdict
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from api.photos import MAX_SIDE                                   # noqa: E402
from core.brand import ACCENT, PRIMARY, bgr                       # noqa: E402
from core.filters import KERNEL_NAMES, MOVES_PIXELS, PRESETS      # noqa: E402
from core.look import Look                                        # noqa: E402

ENGINE_DIR = SERVICE_DIR / 'web' / 'src' / 'engine'


def block(source, start):
    # the text from `start` to the first closing bracket or brace on a line of its own
    begin = source.index(start)
    return source[begin:re.compile(r'^[\]}]', re.MULTILINE).search(source, begin).end()]


class WebPresetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.presets_js = (ENGINE_DIR / 'presets.js').read_text(encoding='utf-8')
        cls.effects_js = (ENGINE_DIR / 'effects.js').read_text(encoding='utf-8')

    def test_preset_names_match(self):
        names = re.findall(r"'([^']+)'", block(self.presets_js, 'export const PRESET_NAMES'))
        self.assertEqual(names, [name for name, _ in PRESETS])

    def test_presets_that_move_pixels_match(self):
        line = re.search(r'export const MOVES_PIXELS = \[(.*)\]', self.presets_js).group(1)
        self.assertEqual(set(re.findall(r"'([^']+)'", line)), MOVES_PIXELS)

    def test_filter_names_match(self):
        names = re.findall(r"name: '([^']+)'", block(self.presets_js, 'export const KERNELS'))
        self.assertEqual(names, KERNEL_NAMES)

    def test_every_preset_has_a_live_shader(self):
        shaders = re.findall(r"^  '([^']+)': \{", block(self.effects_js, 'const PRESET_SHADERS'), re.MULTILINE)
        self.assertEqual(sorted(shaders), sorted(name for name, _ in PRESETS))

    def test_look_defaults_match(self):
        pairs = re.findall(r'^\s+(\w+): ([-\d.]+|\[\]),', block(self.presets_js, 'export const DEFAULT_LOOK'), re.MULTILINE)
        defaults = {key: [] if value == '[]' else float(value) for key, value in pairs}
        expected = {key: [] if key == 'props' else float(value) for key, value in asdict(Look()).items()}
        self.assertEqual(defaults, expected)

    def test_brand_colours_match(self):
        colours = dict(re.findall(r"(primary|accent): '(#[0-9A-Fa-f]{6})'", self.presets_js))
        self.assertEqual(bgr(colours['primary']), PRIMARY)
        self.assertEqual(bgr(colours['accent']), ACCENT)

    def test_service_photo_size_matches(self):
        self.assertIn(f'SERVICE_MAX_SIDE = {MAX_SIDE}', self.presets_js)


if __name__ == '__main__':
    unittest.main()
