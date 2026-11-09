// effects: the live preview, drawn on the GPU with WebGL 2 so it keeps up with the camera.
// It follows core/look.py's order: greyscale, the course filter, contrast and brightness
// (pass 1), then the preset (pass 2). Each preset is a shader written to look like its
// OpenCV version in core/filters.py; a few are close approximations, because OpenCV does
// things a shader can't do in one pass (median blurs, histograms, painting). The service's
// render of the captured photo is always the exact one.
import { BRAND, KERNELS, hexToRgb } from './presets.js'

const VERTEX = `#version 300 es
in vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }`

// pass 1: the camera frame (mirrored if asked) -> greyscale -> filter -> contrast/brightness.
// Positions are in pixels with y up (gl_FragCoord), and frames are uploaded flipped to match.
const ADJUST = `#version 300 es
precision highp float;
uniform sampler2D u_video;
uniform vec2 u_size;
uniform bool u_mirror;
uniform bool u_gray;
uniform float u_kernel[25];
uniform float u_contrast;
uniform float u_brightness;     // -50 to 50, on the 0-255 scale (core: brightness - 50)
out vec4 outColor;

vec3 src(vec2 p) {
  p = clamp(p, vec2(0.5), u_size - 0.5);
  if (u_mirror) p.x = u_size.x - p.x;
  vec3 c = texture(u_video, p / u_size).rgb;
  return u_gray ? vec3(dot(c, vec3(0.299, 0.587, 0.114))) : c;
}

void main() {
  vec2 p = gl_FragCoord.xy;
  vec3 acc = vec3(0.0);
  // row 0 of the kernel is the top row, which is +2 in y-up pixels
  for (int j = 0; j < 5; j++) for (int i = 0; i < 5; i++) {
    float k = u_kernel[j * 5 + i];
    if (k != 0.0) acc += k * src(p + vec2(float(i - 2), float(2 - j)));
  }
  vec3 c = clamp(acc, 0.0, 1.0);
  outColor = vec4(clamp(c * u_contrast + u_brightness / 255.0, 0.0, 1.0), 1.0);
}`

// shared by every preset shader
const PRESET_HEADER = `#version 300 es
precision highp float;
uniform sampler2D u_image;
uniform vec2 u_size;
uniform float u_scale;     // preview pixels per pixel of the service's photo
uniform float u_time;
uniform vec3 u_dark;       // duotone colours
uniform vec3 u_light;
out vec4 outColor;

vec3 px(vec2 p) { return texture(u_image, clamp(p, vec2(0.5), u_size - 0.5) / u_size).rgb; }
float luma(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }
// y-up pixels <-> pixels from the top left, as OpenCV counts them
vec2 imagePx(vec2 p) { return vec2(p.x, u_size.y - p.y); }
vec2 glPx(vec2 q) { return vec2(q.x, u_size.y - q.y); }
// filters.py vignette(): two Gaussians with sigma = size / strength, 1 in the middle
float vignette(vec2 p, float strength) { vec2 d = (p / u_size - 0.5) * strength; return exp(-0.5 * dot(d, d)); }
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233)) + u_time * 61.7) * 43758.5453); }
vec3 hue(float h) { return clamp(abs(mod(h * 6.0 + vec3(0.0, 4.0, 2.0), 6.0) - 3.0) - 1.0, 0.0, 1.0); }
vec3 jet(float t) { return clamp(vec3(1.5 - abs(4.0 * t - 3.0), 1.5 - abs(4.0 * t - 2.0), 1.5 - abs(4.0 * t - 1.0)), 0.0, 1.0); }
// the average colour of a cell, from four samples (OpenCV's INTER_AREA shrink averages it)
vec3 cellColor(vec2 corner, vec2 cell) {
  return (px(glPx(corner + cell * vec2(0.25, 0.25))) + px(glPx(corner + cell * vec2(0.75, 0.25)))
        + px(glPx(corner + cell * vec2(0.25, 0.75))) + px(glPx(corner + cell * vec2(0.75, 0.75)))) / 4.0;
}
`

const DUOTONE = `outColor = vec4(mix(u_dark, u_light, luma(px(gl_FragCoord.xy))), 1.0);`

// how strong the edge through q is: Sobel on the grey picture (|gx| + |gy|, as Canny
// measures it), sampling s pixels apart; a wider s also smooths away fine texture
const SOBEL = `
float sobel(vec2 q, float s) {
  float tl = luma(px(q + vec2(-s, s))), t = luma(px(q + vec2(0.0, s))), tr = luma(px(q + vec2(s, s)));
  float l = luma(px(q + vec2(-s, 0.0))), r = luma(px(q + vec2(s, 0.0)));
  float bl = luma(px(q + vec2(-s, -s))), b = luma(px(q + vec2(0.0, -s))), br = luma(px(q + vec2(s, -s)));
  return abs((tr + 2.0 * r + br) - (tl + 2.0 * l + bl)) + abs((tl + 2.0 * t + tr) - (bl + 2.0 * b + br));
}`

// name (as in core/filters.py PRESETS) -> { functions, main }
const PRESET_SHADERS = {
  'Original': { main: `outColor = vec4(px(gl_FragCoord.xy), 1.0);` },

  'Vintage': { main: `
    vec2 p = gl_FragCoord.xy;
    vec3 c = px(p);
    // the SEPIA matrix, in RGB order
    vec3 s = clamp(vec3(dot(c, vec3(0.393, 0.769, 0.189)), dot(c, vec3(0.349, 0.686, 0.168)),
                        dot(c, vec3(0.272, 0.534, 0.131))), 0.0, 1.0);
    outColor = vec4(s * vignette(p, 1.5), 1.0);` },

  'Sketch': { main: `
    // grey divided by a blurred, inverted grey (a colour dodge); the blur is 21 x 21, sigma 3.5
    vec2 p = gl_FragCoord.xy;
    float sigma = 3.5 * u_scale, spacing = max(sigma * 0.75, 1.0), sum = 0.0, total = 0.0;
    for (int j = -4; j <= 4; j++) for (int i = -4; i <= 4; i++) {
      vec2 o = vec2(float(i), float(j)) * spacing;
      float w = exp(-dot(o, o) / (2.0 * sigma * sigma));
      sum += w * (1.0 - luma(px(p + o)));
      total += w;
    }
    float v = luma(px(p)) * (256.0 / 255.0) / max(1.0 - sum / total, 1.0 / 255.0);
    outColor = vec4(vec3(clamp(v, 0.0, 1.0)), 1.0);` },

  'Cartoon': { main: `
    // black lines where a pixel is darker than its 9 x 9 neighbourhood (adaptive threshold,
    // C = 9), over colours smoothed across a 9 px circle (the bilateral filter, very loose)
    vec2 p = gl_FragCoord.xy;
    float s = max(u_scale, 0.5), mean = 0.0, n = 0.0;
    vec3 color = vec3(0.0);
    for (int j = -4; j <= 4; j++) for (int i = -4; i <= 4; i++) {
      vec3 c = px(p + vec2(float(i), float(j)) * s);
      mean += luma(c);
      if (i * i + j * j <= 16) { color += c; n += 1.0; }
    }
    float g = 0.0;
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) g += luma(px(p + vec2(float(i), float(j)) * s));
    float edge = g / 9.0 > mean / 81.0 - 9.0 / 255.0 ? 1.0 : 0.0;
    outColor = vec4(color / n * edge, 1.0);` },

  'Pop Art': { main: `
    // four tinted copies at half size: blue, green / red, cyan (the BGR tints, in RGB)
    vec2 uv = gl_FragCoord.xy / u_size;
    bool top = uv.y >= 0.5, left = uv.x < 0.5;
    vec3 tint = top ? (left ? vec3(0.3, 0.3, 1.0) : vec3(0.3, 1.0, 0.3))
                    : (left ? vec3(1.0, 0.3, 0.3) : vec3(0.2, 1.0, 1.0));
    outColor = vec4(texture(u_image, fract(uv * 2.0)).rgb * tint, 1.0);` },

  'Noir': { main: `
    vec2 p = gl_FragCoord.xy;
    float g = clamp(luma(px(p)) * 1.6 - 60.0 / 255.0, 0.0, 1.0);
    outColor = vec4(vec3(g) * vignette(p, 1.2), 1.0);` },

  'School Colors': { main: DUOTONE },

  'Neon': {
    functions: SOBEL,
    main: `
    // glowing outlines on black, coloured by brightness around the colour wheel: thin lines
    // where the edge is strong (Canny 50-150 on a blurred grey; the wider Sobel spacing
    // stands in for the blur), plus a soft glow around them (the 15 x 15 blur of the lines)
    vec2 p = gl_FragCoord.xy;
    float s = max(u_scale, 0.5);
    float line = smoothstep(0.4, 0.7, sobel(p, 1.5 * s));
    float glow = 0.0, total = 0.0;
    for (int j = -2; j <= 2; j++) for (int i = -2; i <= 2; i++) {
      float w = exp(-float(i * i + j * j) / 4.0);
      glow += w * smoothstep(0.4, 0.7, sobel(p + vec2(float(i), float(j)) * 2.5 * s, 1.5 * s));
      total += w;
    }
    outColor = vec4(hue(luma(px(p))) * max(line, 1.2 * glow / total), 1.0);`,
  },

  'Heat Vision': { main: `outColor = vec4(jet(luma(px(gl_FragCoord.xy))), 1.0);` },

  'X-Ray': { main: `
    // inverted grey, stretched (OpenCV evens out the histogram), tinted blue-white
    float g = clamp((1.0 - luma(px(gl_FragCoord.xy)) - 0.1) / 0.8, 0.0, 1.0);
    outColor = vec4(0.6 * g, 0.85 * g, g, 1.0);` },

  'Pixel Art': { main: `
    // 12 px blocks of the service's photo, each colour rounded to 4 levels per channel
    vec2 q = imagePx(gl_FragCoord.xy);
    vec2 cells = max(floor(u_size / (12.0 * u_scale)), 1.0);
    vec2 cell = u_size / cells;
    vec3 c = cellColor(floor(q / cell) * cell, cell);
    outColor = vec4((floor(c * 255.0 / 64.0) * 64.0 + 32.0) / 255.0, 1.0);` },

  'Comic Dots': { main: `
    // a dot per cell (8 px, or width / 80), bigger where the photo is darker, on white
    vec2 q = imagePx(gl_FragCoord.xy);
    float cell = max(8.0, floor(u_size.x / u_scale / 80.0)) * u_scale;
    vec2 index = floor(q / cell);
    if (any(greaterThanEqual(index, floor(u_size / cell)))) { outColor = vec4(1.0); return; }
    vec3 c = cellColor(index * cell, vec2(cell));
    float r = floor(cell / u_scale * (0.25 + 0.5 * (1.0 - luma(c)))) * u_scale;
    float a = clamp(r - distance(q, index * cell + cell * 0.5) + 0.5, 0.0, 1.0);
    outColor = vec4(mix(vec3(1.0), c, a), 1.0);` },

  'Night Vision': { main: `
    vec2 p = gl_FragCoord.xy;
    float g = clamp((luma(px(p)) - 0.08) / 0.84, 0.0, 1.0);          // evened-out grey
    g = min(g + floor(hash(p) * 40.0) / 255.0, 1.0);                   // grain, new each frame
    vec3 c = vec3(g / 4.0, g, g / 4.0);
    if (mod(floor(imagePx(p).y), 3.0) < 0.5) c *= 0.6;                 // every third row darker
    outColor = vec4(c * vignette(p, 1.0), 1.0);` },

  'VHS': { main: `
    // red from 6 px to the left, blue from 6 px to the right, softened, darker even rows,
    // and the REC light (the page draws the word REC next to it)
    vec2 p = gl_FragCoord.xy;
    vec2 shift = vec2(6.0 * u_scale, 0.0);
    vec3 c = vec3(0.0);
    for (int j = -1; j <= 1; j++) for (int i = -1; i <= 1; i++) {
      vec2 o = vec2(float(i), float(j));
      float w = (2.0 - abs(o.x)) * (2.0 - abs(o.y));
      c += w * vec3(px(p + o - shift).r, px(p + o).g, px(p + o + shift).b);
    }
    c /= 16.0;
    vec2 q = imagePx(p);
    if (mod(floor(q.y), 2.0) < 0.5) c *= 0.75;
    vec2 light = vec2(u_size.x - 110.0 * u_scale, 62.0 * u_scale);
    c = mix(c, vec3(1.0, 0.0, 0.0), clamp(9.0 * u_scale - distance(q, light) + 0.5, 0.0, 1.0));
    outColor = vec4(c, 1.0);` },

  'Watercolor': { functions: SOBEL, main: `
    // OpenCV's stylization (at half size) flattens colour and inks the outlines. Here a
    // Kuwahara filter does the flattening: each pixel takes the average of the calmest of
    // four corners around it. Strong edges are then drawn dark and thick.
    vec2 p = gl_FragCoord.xy;
    float s = max(u_scale * 2.0, 1.0);
    vec3 m[4] = vec3[4](vec3(0.0), vec3(0.0), vec3(0.0), vec3(0.0));
    vec3 v[4] = vec3[4](vec3(0.0), vec3(0.0), vec3(0.0), vec3(0.0));
    for (int j = 0; j <= 4; j++) for (int i = 0; i <= 4; i++) {
      vec2 o = vec2(float(i), float(j)) * s;
      vec3 c0 = px(p + vec2(-o.x, -o.y)), c1 = px(p + vec2(o.x, -o.y));
      vec3 c2 = px(p + vec2(-o.x, o.y)), c3 = px(p + o);
      m[0] += c0; v[0] += c0 * c0; m[1] += c1; v[1] += c1 * c1;
      m[2] += c2; v[2] += c2 * c2; m[3] += c3; v[3] += c3 * c3;
    }
    vec3 best = m[0] / 25.0;
    float lowest = 1e9;
    for (int k = 0; k < 4; k++) {
      vec3 mean = m[k] / 25.0;
      vec3 variance = abs(v[k] / 25.0 - mean * mean);
      float total = variance.r + variance.g + variance.b;
      if (total < lowest) { lowest = total; best = mean; }
    }
    float ink = smoothstep(0.25, 0.6, sobel(p, 1.5 * s));
    outColor = vec4(best * (1.0 - 0.85 * ink), 1.0);` },

  'Mirror': { main: `
    // the left half reflected onto the right half
    vec2 p = gl_FragCoord.xy;
    if (p.x >= u_size.x * 0.5) p.x = u_size.x - p.x;
    outColor = vec4(px(p), 1.0);` },

  'Desert Sunset': { main: DUOTONE },
}

// the duotone colours: the brand's for School Colors, deep purple to orange for Desert Sunset
const DUOTONES = {
  'School Colors': () => [hexToRgb(BRAND.primary), hexToRgb(BRAND.accent)],
  'Desert Sunset': () => [hexToRgb('#312F8A'), hexToRgb('#FFA03C')],
}

// presets drawn live; any other name shows the picture unchanged until it's captured
export const LIVE_PRESETS = Object.keys(PRESET_SHADERS)


export class EffectRenderer {
  constructor(canvas) {
    this.canvas = canvas
    // preserveDrawingBuffer lets the page save what's on screen (snapshot())
    const gl = canvas.getContext('webgl2', { alpha: false, antialias: false, preserveDrawingBuffer: true })
    if (!gl) throw new Error('This browser has no WebGL 2, which the live preview needs')
    this.gl = gl
    this.programs = new Map()                  // shader source -> { program, uniforms }

    const quad = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, quad)
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW)
    this.quad = quad

    this.videoTexture = this.#texture()
    this.adjustedTexture = this.#texture()     // pass 1's result, which pass 2 reads
    this.framebuffer = gl.createFramebuffer()
    this.width = 0
    this.height = 0
  }

  static hasShader(presetName) {
    return presetName in PRESET_SHADERS
  }

  resize(width, height) {
    if (width === this.width && height === this.height) return
    const gl = this.gl
    this.canvas.width = this.width = width
    this.canvas.height = this.height = height
    gl.bindTexture(gl.TEXTURE_2D, this.adjustedTexture)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, width, height, 0, gl.RGBA, gl.UNSIGNED_BYTE, null)
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer)
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, this.adjustedTexture, 0)
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
  }

  render(source, { look, presetName = 'Original', mirror = true, scale = 1, time = 0 }) {
    // draws one frame of source (a playing <video>, or any image) with the look
    const gl = this.gl
    gl.bindTexture(gl.TEXTURE_2D, this.videoTexture)
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true)
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, source)
    gl.viewport(0, 0, this.width, this.height)

    // pass 1, into the framebuffer
    const adjust = this.#program(ADJUST)
    gl.useProgram(adjust.program)
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.framebuffer)
    gl.uniform1i(adjust.uniform('u_video'), 0)
    gl.uniform2f(adjust.uniform('u_size'), this.width, this.height)
    gl.uniform1i(adjust.uniform('u_mirror'), mirror ? 1 : 0)
    gl.uniform1i(adjust.uniform('u_gray'), look.grayscale ? 1 : 0)
    gl.uniform1fv(adjust.uniform('u_kernel'), (KERNELS[look.kernel] || KERNELS[0]).weights)
    gl.uniform1f(adjust.uniform('u_contrast'), look.contrast)
    gl.uniform1f(adjust.uniform('u_brightness'), look.brightness - 50)
    this.#draw()

    // pass 2, onto the canvas
    const shader = PRESET_SHADERS[presetName] || PRESET_SHADERS.Original
    const preset = this.#program(PRESET_HEADER + (shader.functions || '') + `\nvoid main() {${shader.main}\n}`)
    gl.useProgram(preset.program)
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.bindTexture(gl.TEXTURE_2D, this.adjustedTexture)
    gl.uniform1i(preset.uniform('u_image'), 0)
    gl.uniform2f(preset.uniform('u_size'), this.width, this.height)
    gl.uniform1f(preset.uniform('u_scale'), scale)
    gl.uniform1f(preset.uniform('u_time'), time % 1000)
    const [dark, light] = (DUOTONES[presetName] || (() => [[0, 0, 0], [1, 1, 1]]))()
    gl.uniform3fv(preset.uniform('u_dark'), dark)
    gl.uniform3fv(preset.uniform('u_light'), light)
    this.#draw()
  }

  snapshot(type = 'image/jpeg', quality = 0.92) {
    // what's on screen now, as a file (the live approximation, not the service's render)
    return new Promise((resolve) => this.canvas.toBlob(resolve, type, quality))
  }

  dispose() {
    const gl = this.gl
    for (const { program } of this.programs.values()) gl.deleteProgram(program)
    gl.deleteTexture(this.videoTexture)
    gl.deleteTexture(this.adjustedTexture)
    gl.deleteFramebuffer(this.framebuffer)
    gl.deleteBuffer(this.quad)
    this.programs.clear()
  }

  #texture() {
    const gl = this.gl
    const texture = gl.createTexture()
    gl.bindTexture(gl.TEXTURE_2D, texture)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)
    return texture
  }

  #program(fragmentSource) {
    // compiled the first time each shader is used, then kept
    if (this.programs.has(fragmentSource)) return this.programs.get(fragmentSource)
    const gl = this.gl
    const compile = (type, source) => {
      const shader = gl.createShader(type)
      gl.shaderSource(shader, source)
      gl.compileShader(shader)
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        throw new Error(`A live effect failed to compile: ${gl.getShaderInfoLog(shader)}`)
      }
      return shader
    }
    const program = gl.createProgram()
    gl.attachShader(program, compile(gl.VERTEX_SHADER, VERTEX))
    gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource))
    gl.bindAttribLocation(program, 0, 'a_pos')
    gl.linkProgram(program)
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(`A live effect failed to link: ${gl.getProgramInfoLog(program)}`)
    }
    const locations = new Map()
    const entry = {
      program,
      uniform: (name) => {
        if (!locations.has(name)) locations.set(name, gl.getUniformLocation(program, name))
        return locations.get(name)
      },
    }
    this.programs.set(fragmentSource, entry)
    return entry
  }

  #draw() {
    const gl = this.gl
    gl.activeTexture(gl.TEXTURE0)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad)
    gl.enableVertexAttribArray(0)
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }
}
