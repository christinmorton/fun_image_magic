// booth: the live loop, like the desktop booth's main loop. Each camera frame is drawn with
// the current look on the GPU: faces are tracked and given their stickers, the person is
// found for background swap and focus, and the mascot and frame go on top. Face outlines go
// on a second canvas laid over the first. No buttons or layout here: the vanilla, React and
// Vue pages each build their own controls around one WebcamBooth.
//
//   const booth = new WebcamBooth({ canvas, overlay })
//   booth.setCatalog(catalog, { artUrl })            // the service's catalog, for the art
//   await booth.start()
//   booth.setLook({ preset: 4, sticker: 0 })
//   const { blob, look } = await booth.capture()     // the unedited photo + the look to render
//   await booth.startRecording({ limitSeconds: 30 }) // video of the preview (no limit: until stopped)
//   const video = await booth.stopRecording()        // or it stops by itself at the limit
//
// Events (booth.addEventListener): 'status' (detail: { fps, faces, tracking, segmenting }),
// 'error' (detail: an Error; the camera keeps running if only tracking or art failed).
// booth.recorder has its own 'tick' and 'stop' events (recorder.js).
import { fullQuad, mascotQuad, stickerQuad } from './art.js'
import { Camera } from './camera.js'
import { EffectRenderer } from './effects.js'
import { DEFAULT_LOOK, MOVES_PIXELS, builtInCatalog, previewScale } from './presets.js'
import { Recorder } from './recorder.js'
import { DEFAULT_MEDIAPIPE, FaceTracker, PersonSegmenter, drawFaceOutlines } from './tracker.js'

export class WebcamBooth extends EventTarget {
  constructor({ canvas, overlay = null, mirror = true, track = true, showFaces = false,
                previewMaxWidth = 1280, mediapipe = DEFAULT_MEDIAPIPE } = {}) {
    super()
    this.camera = new Camera()
    this.renderer = new EffectRenderer(canvas)
    this.recorder = new Recorder(canvas)   // records the preview canvas, so effects and art are in the video
    this.overlay = overlay                // an optional 2D canvas on top of the preview
    this.mirror = mirror                   // like a selfie camera, and like the desktop booth
    this.track = track
    this.showFaces = showFaces             // outlines round tracked faces (stickers show them too)
    this.previewMaxWidth = previewMaxWidth // bigger cameras are previewed at this width (captures stay full size)
    this.mediapipe = { ...DEFAULT_MEDIAPIPE, ...mediapipe }
    this.catalog = builtInCatalog()
    this.presetNames = this.catalog.presets.map((p) => p.name)
    this.artUrl = (path) => path           // a catalog link (/v1/...) -> a URL the page can load
    this.faces = []
    this.tracking = 'off'                  // the face tracker: 'off', 'loading', 'GPU', 'CPU' or 'failed'
    this.segmenting = 'off'                // the person segmenter, the same
    this._look = { ...DEFAULT_LOOK }
    this._tracker = null
    this._segmenter = null
    this._frameHandle = null
    this._fps = { frames: 0, since: 0, value: 0 }
  }

  get running() { return this.camera.running }
  get look() { return { ...this._look } }
  get presetName() { return this.presetNames[this._look.preset] ?? 'Original' }
  get focusName() { return this.catalog.focus_modes[this._look.focus]?.name ?? 'Off' }

  setLook(changes) {
    this._look = { ...this._look, ...changes }
  }

  setCatalog(catalog, { artUrl } = {}) {
    // the service's catalog, so look numbers mean the same on both sides, and the art can be
    // loaded; artUrl turns its /v1/... links into URLs on the page's server
    if (!catalog?.presets?.length) return
    this.catalog = catalog
    this.presetNames = catalog.presets.map((p) => p.name)
    if (artUrl) this.artUrl = artUrl
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

  startRecording({ limitSeconds = null, audio = true } = {}) {
    // video of the preview as it's drawn, with the microphone if audio and allowed;
    // limitSeconds (up to 5 minutes) stops it by itself
    if (!this.running) return Promise.reject(new Error('Start the camera before recording'))
    return this.recorder.start({ limitSeconds, audio })
  }

  stopRecording() {
    // resolves with the video: { blob, type, extension, duration, width, height, audio, stoppedBy }
    return this.recorder.stop()
  }

  dispose() {
    this.recorder.stop()
    this.stop()
    this._tracker?.close()
    this._segmenter?.close()
    this._tracker = this._segmenter = null
    this.renderer.dispose()
  }

  async _loadTracker() {
    this.tracking = 'loading'
    try {
      this._tracker = await FaceTracker.create(this.mediapipe)
      this.tracking = this._tracker.delegate
    } catch (error) {
      this.tracking = 'failed'
      this._report(new Error(`Face tracking couldn't start: ${error.message}`))
    }
  }

  async _loadSegmenter() {
    this.segmenting = 'loading'
    try {
      this._segmenter = await PersonSegmenter.create(this.mediapipe)
      this.segmenting = this._segmenter.delegate
    } catch (error) {
      this.segmenting = 'failed'
      this._report(new Error(`Finding the person couldn't start: ${error.message}`))
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
    this.faces = this._tracker && this.track ? this._tracker.detect(video, now) : []
    try {
      this.renderer.render(video, { look: this._look, presetName: this.presetName, mirror: this.mirror,
                                    scale: this._scale, time: now / 1000, ...this._art(video, now) })
    } catch (error) {
      // a shader that won't compile on this GPU: show the picture plainly rather than stop
      this._report(error)
      this.presetNames[this._look.preset] = 'Original'
    }
    this._drawOverlay()

    const fps = this._fps
    fps.frames += 1
    if (now - fps.since >= 1000) {
      fps.value = Math.round(fps.frames * 1000 / (now - fps.since))
      fps.frames = 0
      fps.since = now
      this.dispatchEvent(new CustomEvent('status', { detail: {
        fps: fps.value, faces: this.faces.length, tracking: this.tracking, segmenting: this.segmenting } }))
    }
  }

  _art(video, now) {
    // this frame's person mask, background, stickers, mascot and frame, from the look
    const look = this._look
    const { width, height } = this.renderer
    const picture = (item, query = '') => {
      // a catalog item's picture once it has loaded (it starts loading the first time)
      if (!item) return null
      const entry = this.renderer.art(this.artUrl(item.image) + query)
      if (entry.failed && !entry.reported) {
        entry.reported = true
        this._report(new Error(`The picture for "${item.name}" couldn't be loaded`))
      }
      return entry.ready ? entry : null
    }

    let mask = null
    if (look.background >= 0 || this.focusName !== 'Off') {
      if (this._segmenter) mask = this._segmenter.segment(video, now)
      else if (this.segmenting === 'off') this._loadSegmenter()
    }

    const stickers = []
    const stickerItem = this.catalog.stickers[look.sticker]
    const sticker = picture(stickerItem)
    if (sticker) {
      for (const face of this.faces) {
        const quad = stickerQuad(face, { width, height, mirror: this.mirror, widthFactor: stickerItem.width_factor,
                                         liftFactor: stickerItem.lift_factor, aspect: sticker.height / sticker.width,
                                         minWidth: 10 * this._scale })
        if (quad) stickers.push({ texture: sticker.texture, quad })
      }
    }

    const overlays = []
    const mascot = picture(this.catalog.mascots[look.mascot])
    if (mascot) {
      overlays.push({ texture: mascot.texture,
                      quad: mascotQuad({ width, height, imageWidth: mascot.width, imageHeight: mascot.height }) })
    }
    // the service fits the frame to this size, exactly as a render would
    const frame = picture(this.catalog.frames[look.frame], `?width=${width}&height=${height}`)
    if (frame) overlays.push({ texture: frame.texture, quad: fullQuad({ width, height }) })

    return {
      mask,
      background: picture(this.catalog.backgrounds[look.background]),
      focus: this.focusName,
      stickers,
      stickersFirst: MOVES_PIXELS.includes(this.presetName),
      overlays,
    }
  }

  _report(error) {
    this.dispatchEvent(new CustomEvent('error', { detail: error }))
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
