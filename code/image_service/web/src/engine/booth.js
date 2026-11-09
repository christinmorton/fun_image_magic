// booth: the live loop, like the desktop booth's main loop. Each camera frame is drawn with
// the current look on the GPU, faces are tracked, and outlines are drawn on a second canvas
// laid over the first. No buttons or layout here: the vanilla, React and Vue pages each
// build their own controls around one WebcamBooth.
//
//   const booth = new WebcamBooth({ canvas, overlay })
//   await booth.start()
//   booth.setLook({ preset: 4, contrast: 1.2 })
//   const { blob, look } = await booth.capture()     // the unedited photo + the look to render
//
// Events (booth.addEventListener): 'status' (detail: { fps, faces, tracking }),
// 'error' (detail: an Error; the camera keeps running if only tracking failed).
import { Camera } from './camera.js'
import { EffectRenderer } from './effects.js'
import { DEFAULT_LOOK, MOVES_PIXELS, PRESET_NAMES, previewScale } from './presets.js'
import { DEFAULT_MEDIAPIPE, FaceTracker, drawFaceOutlines } from './tracker.js'

export class WebcamBooth extends EventTarget {
  constructor({ canvas, overlay = null, mirror = true, track = true, showFaces = true,
                previewMaxWidth = 1280, mediapipe = DEFAULT_MEDIAPIPE } = {}) {
    super()
    this.camera = new Camera()
    this.renderer = new EffectRenderer(canvas)
    this.overlay = overlay                 // an optional 2D canvas on top of the preview
    this.mirror = mirror                   // like a selfie camera, and like the desktop booth
    this.track = track
    this.showFaces = showFaces
    this.previewMaxWidth = previewMaxWidth // bigger cameras are previewed at this width (captures stay full size)
    this.mediapipe = { ...DEFAULT_MEDIAPIPE, ...mediapipe }
    this.presetNames = [...PRESET_NAMES]
    this.faces = []
    this.tracking = 'off'                  // 'off', 'loading', 'GPU', 'CPU' or 'failed'
    this._look = { ...DEFAULT_LOOK }
    this._tracker = null
    this._frameHandle = null
    this._fps = { frames: 0, since: 0, value: 0 }
  }

  get running() { return this.camera.running }
  get look() { return { ...this._look } }
  get presetName() { return this.presetNames[this._look.preset] ?? 'Original' }

  setLook(changes) {
    this._look = { ...this._look, ...changes }
  }

  setCatalog(catalog) {
    // use the service's preset list, so look.preset numbers mean the same on both sides
    if (catalog?.presets?.length) this.presetNames = catalog.presets.map((p) => p.name)
  }

  async start({ deviceId = null, resolution = 'best' } = {}) {
    const size = await this.camera.start({ deviceId, resolution })
    const width = Math.min(size.width, this.previewMaxWidth)
    const height = Math.round(size.height * width / size.width)
    this.renderer.resize(width, height)
    if (this.overlay) {
      this.overlay.width = width
      this.overlay.height = height
    }
    this._scale = previewScale(width, size.width, size.height)
    this._loop()
    if (this.track && !this._tracker) this._loadTracker()  // the camera shows while the model loads
    return size
  }

  stop() {
    this._cancelFrame()
    this.camera.stop()
  }

  async capture(options = {}) {
    // the unedited frame at full resolution, mirrored like the preview, with the look and
    // faces at that moment: send blob and look to the service for the exact render
    const shot = await this.camera.capture({ mirror: this.mirror, ...options })
    return { ...shot, look: this.look, faces: this.faces.length }
  }

  snapshot() {
    // the live preview as it looks now (an approximation; for use without a service)
    return this.renderer.snapshot()
  }

  dispose() {
    this.stop()
    this._tracker?.close()
    this._tracker = null
    this.renderer.dispose()
  }

  async _loadTracker() {
    this.tracking = 'loading'
    try {
      this._tracker = await FaceTracker.create(this.mediapipe)
      this.tracking = this._tracker.delegate
    } catch (error) {
      this.tracking = 'failed'
      this.dispatchEvent(new CustomEvent('error', { detail: new Error(`Face tracking couldn't start: ${error.message}`) }))
    }
  }

  _loop() {
    // one step per new camera frame where the browser can say when one arrives, else per screen refresh
    this._cancelFrame()
    const video = this.camera.video
    const step = (now) => {
      if (!this.camera.running) return
      this._frame(now)
      this._frameHandle = video.requestVideoFrameCallback
        ? { video: video.requestVideoFrameCallback(step) }
        : { animation: requestAnimationFrame(step) }
    }
    step(performance.now())
  }

  _cancelFrame() {
    const handle = this._frameHandle
    if (handle?.video !== undefined) this.camera.video.cancelVideoFrameCallback(handle.video)
    if (handle?.animation !== undefined) cancelAnimationFrame(handle.animation)
    this._frameHandle = null
  }

  _frame(now) {
    const video = this.camera.video
    if (video.readyState < 2) return
    try {
      this.renderer.render(video, { look: this._look, presetName: this.presetName, mirror: this.mirror,
                                    scale: this._scale, time: now / 1000 })
    } catch (error) {
      // a shader that won't compile on this GPU: show the picture plainly rather than stop
      this.dispatchEvent(new CustomEvent('error', { detail: error }))
      this.presetNames[this._look.preset] = 'Original'
    }
    this.faces = this._tracker && this.track ? this._tracker.detect(video, now) : []
    this._drawOverlay()

    const fps = this._fps
    fps.frames += 1
    if (now - fps.since >= 1000) {
      fps.value = Math.round(fps.frames * 1000 / (now - fps.since))
      fps.frames = 0
      fps.since = now
      this.dispatchEvent(new CustomEvent('status', { detail: { fps: fps.value, faces: this.faces.length, tracking: this.tracking } }))
    }
  }

  _drawOverlay() {
    if (!this.overlay) return
    const ctx = this.overlay.getContext('2d')
    ctx.clearRect(0, 0, this.overlay.width, this.overlay.height)
    if (this.showFaces && this.faces.length && !MOVES_PIXELS.includes(this.presetName)) {
      drawFaceOutlines(ctx, this.faces, { mirror: this.mirror })
    }
    if (this.presetName === 'VHS') {
      // the word next to the VHS shader's REC light (filters.py draws both with OpenCV)
      const s = this._scale
      ctx.save()
      ctx.fillStyle = '#fff'
      ctx.font = `600 ${Math.round(27 * s)}px system-ui, sans-serif`
      ctx.fillText('REC', this.overlay.width - 95 * s, 72 * s)
      ctx.restore()
    }
  }
}
