// presets: the look settings the browser knows about, in the same order and with the same
// defaults as core/ (core/look.py, core/filters.py). The service's catalog is the real list;
// these are used until it loads, or when the page runs without a service.

// a look with nothing changed (core/look.py Look)
export const DEFAULT_LOOK = Object.freeze({
  contrast: 1.0,       // 1.0 = no change
  brightness: 50,      // 50 = no change
  kernel: 0,           // index into the filters
  grayscale: 0,        // 0 = colour, 1 = grey
  preset: 0,           // index into the presets
  sticker: -1,         // -1 = off (stickers, backgrounds, mascots and frames)
  background: -1,
  mascot: -1,
  frame: -1,
  focus: 0,            // 0 = off
  props: [],
})

// core/filters.py PRESETS, by name: the live preview finds each preset's shader by its name,
// so a renamed or new preset on the service simply shows unchanged until it gets a shader
export const PRESET_NAMES = [
  'Original', 'Vintage', 'Sketch', 'Cartoon', 'Pop Art', 'Noir', 'School Colors', 'Neon',
  'Heat Vision', 'X-Ray', 'Pixel Art', 'Comic Dots', 'Night Vision', 'VHS', 'Watercolor',
  'Mirror', 'Desert Sunset',
]

// core/masks.py FOCUS_MODES: what happens to the background behind the person
export const FOCUS_MODES = ['Off', 'Color Pop', 'Portrait Blur', 'Mask Preview']

// presets that move parts of the picture around (core/filters.py MOVES_PIXELS): face
// outlines would float where the face was, so the preview leaves them off
export const MOVES_PIXELS = ['Pop Art', 'Mirror']

// core/filters.py KERNELS, as 5 x 5 grids (3 x 3 ones padded with zeros) for the shader.
// OpenCV's filter2D doesn't flip the kernel, so neither does the shader.
const pad3 = (k) => [0, 0, 0, 0, 0, 0, ...k.slice(0, 3), 0, 0, ...k.slice(3, 6), 0, 0, ...k.slice(6, 9), 0, 0, 0, 0, 0, 0]
const outer = (v) => v.flatMap((a) => v.map((b) => a * b))
// cv2.getGaussianKernel(n, 0) uses fixed tables for small sizes
const GAUSS3 = [0.25, 0.5, 0.25]
const GAUSS5 = [0.0625, 0.25, 0.375, 0.25, 0.0625]

export const KERNELS = [
  { name: 'None', weights: pad3([0, 0, 0, 0, 1, 0, 0, 0, 0]) },
  { name: 'Sharpen', weights: pad3([0, -1, 0, -1, 5, -1, 0, -1, 0]) },
  { name: 'Blur (light)', weights: pad3(outer(GAUSS3)) },
  { name: 'Blur (strong)', weights: outer(GAUSS5) },
  { name: 'Box blur', weights: pad3(Array(9).fill(1 / 9)) },
  { name: 'Emboss', weights: pad3([-2, -1, 0, -1, 1, 1, 0, 1, 2]) },
  { name: 'Edges', weights: pad3([-1, -1, -1, -1, 8, -1, -1, -1, -1]) },
]

// core/brand.py PRIMARY and ACCENT, for the School Colors preset (as '#RRGGBB')
export const BRAND = Object.freeze({ primary: '#0F766E', accent: '#FFD166' })

// the service shrinks photos to this on their long side (api/photos.py MAX_SIDE)
export const SERVICE_MAX_SIDE = 2048

// the built-in catalog, shaped like GET /v1/catalog's lists, for running without a service
export function builtInCatalog() {
  const items = (names) => names.map((name, index) => ({ index, name, thumbnail: null }))
  return {
    presets: items(PRESET_NAMES),
    filters: items(KERNELS.map((k) => k.name)),
    focus_modes: items(FOCUS_MODES),
    layouts: [], stickers: [], backgrounds: [], frames: [], mascots: [], props: [],
    ai_presets: [], off: -1, look_defaults: { ...DEFAULT_LOOK },
  }
}

// a look with every setting the service accepts, and nothing else: keys it doesn't know are
// dropped (the service refuses them), numbers are made whole where it wants whole numbers
export function toServiceLook(look) {
  const merged = { ...DEFAULT_LOOK, ...look }
  return {
    contrast: Number(merged.contrast),
    brightness: Math.round(merged.brightness),
    kernel: Math.round(merged.kernel),
    grayscale: merged.grayscale ? 1 : 0,
    preset: Math.round(merged.preset),
    sticker: Math.round(merged.sticker),
    background: Math.round(merged.background),
    mascot: Math.round(merged.mascot),
    frame: Math.round(merged.frame),
    focus: Math.round(merged.focus),
    props: (merged.props || []).map(({ prop, x = 0.5, y = 0.5, size = 0.5 }) => ({ prop, x, y, size })),
  }
}

// '#RRGGBB' -> [r, g, b] from 0 to 1, for shaders
export function hexToRgb(hex) {
  const value = hex.replace('#', '')
  return [0, 2, 4].map((i) => parseInt(value.slice(i, i + 2), 16) / 255)
}

// how the photo the service will render compares with the preview: the preview is drawn
// smaller, so effects measured in pixels (pixel art blocks, comic dots, VHS shift) are scaled
// by this to look the same as in the final picture
export function previewScale(previewWidth, captureWidth, captureHeight) {
  const serviceWidth = captureWidth * Math.min(1, SERVICE_MAX_SIDE / Math.max(captureWidth, captureHeight))
  return serviceWidth > 0 ? previewWidth / serviceWidth : 1
}
