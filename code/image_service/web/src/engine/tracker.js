// tracker: MediaPipe in the browser, in video mode like the desktop booth (core/tracking.py):
// the face landmarker, so a face found once is followed from frame to frame as it turns
// (the service only sees single stills, where faces at an angle are hardest to find), and
// the person segmenter, for background swap and the focus effects.
import { FaceLandmarker, FilesetResolver, ImageSegmenter } from '@mediapipe/tasks-vision'

// where the page loads MediaPipe's files from (vite.config.js serves them in development)
export const DEFAULT_MEDIAPIPE = {
  wasmBaseUrl: '/mediapipe/wasm',
  faceModelUrl: '/mediapipe/models/face_landmarker.task',
  personModelUrl: '/mediapipe/models/selfie_segmenter.tflite',
}

const filesets = new Map()                 // wasmBaseUrl -> the loaded WASM, shared by both models

async function createTask(Task, wasmBaseUrl, modelUrl, options) {
  // a MediaPipe task on the GPU, which is much faster, or on the CPU where the GPU can't be used
  if (!filesets.has(wasmBaseUrl)) filesets.set(wasmBaseUrl, FilesetResolver.forVisionTasks(wasmBaseUrl))
  const fileset = await filesets.get(wasmBaseUrl)
  for (const delegate of ['GPU', 'CPU']) {
    try {
      const task = await Task.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: modelUrl, delegate }, runningMode: 'VIDEO', ...options })
      return { task, delegate }
    } catch (error) {
      if (delegate === 'CPU') throw error
    }
  }
}

class VideoClock {
  // video mode needs timestamps that always go up
  constructor() { this.last = -1 }
  next(now) {
    this.last = Math.max(Math.round(now), this.last + 1)
    return this.last
  }
}

export class FaceTracker {
  static async create({ wasmBaseUrl = DEFAULT_MEDIAPIPE.wasmBaseUrl, faceModelUrl = DEFAULT_MEDIAPIPE.faceModelUrl,
                        numFaces = 4 } = {}) {
    // numFaces is the same as core/tracking.py
    const { task, delegate } = await createTask(FaceLandmarker, wasmBaseUrl, faceModelUrl, { numFaces })
    return new FaceTracker(task, delegate)
  }

  constructor(landmarker, delegate) {
    this.landmarker = landmarker
    this.delegate = delegate               // 'GPU' or 'CPU', for showing on the page
    this.clock = new VideoClock()
  }

  detect(video, now = performance.now()) {
    // the faces in this frame: one list of 478 points per face, x and y from 0 to 1 of the
    // camera's own (unmirrored) picture
    return this.landmarker.detectForVideo(video, this.clock.next(now)).faceLandmarks
  }

  close() {
    this.landmarker.close()
  }
}

export class PersonSegmenter {
  static async create({ wasmBaseUrl = DEFAULT_MEDIAPIPE.wasmBaseUrl, personModelUrl = DEFAULT_MEDIAPIPE.personModelUrl,
                        width = 256 } = {}) {
    const { task, delegate } = await createTask(ImageSegmenter, wasmBaseUrl, personModelUrl,
                                                { outputConfidenceMasks: true, outputCategoryMask: false })
    return new PersonSegmenter(task, delegate, width)
  }

  constructor(segmenter, delegate, width) {
    this.segmenter = segmenter
    this.delegate = delegate
    this.width = width                     // the model works at 256 px, so it's given a small copy
    this.small = document.createElement('canvas')
    this.clock = new VideoClock()
    this.mask = { data: new Uint8Array(0), width: 0, height: 0, version: 0 }
  }

  segment(video, now = performance.now()) {
    // the person mask of this frame, small: data is 0 (background) to 255 (person), one byte
    // per pixel, bottom row first as WebGL expects; it follows the unmirrored camera picture
    const w = this.width
    const h = Math.max(1, Math.round(video.videoHeight * w / video.videoWidth))
    if (this.small.width !== w || this.small.height !== h) Object.assign(this.small, { width: w, height: h })
    this.small.getContext('2d', { willReadFrequently: false }).drawImage(video, 0, 0, w, h)
    const result = this.segmenter.segmentForVideo(this.small, this.clock.next(now))
    try {
      const confidence = result.confidenceMasks[0]
      const values = confidence.getAsFloat32Array()
      const { width, height } = confidence
      const mask = this.mask
      if (mask.data.length !== width * height) mask.data = new Uint8Array(width * height)
      for (let y = 0; y < height; y++) {
        const from = y * width
        const to = (height - 1 - y) * width
        for (let x = 0; x < width; x++) mask.data[to + x] = values[from + x] * 255
      }
      Object.assign(mask, { width, height, version: mask.version + 1 })
      return mask
    } finally {
      result.close()                       // the masks live in MediaPipe's memory until closed
    }
  }

  close() {
    this.segmenter.close()
  }
}

export function faceBox(face, { mirror = true } = {}) {
  // a face's box as fractions of the picture: { x, y, width, height }
  const xs = face.map((p) => (mirror ? 1 - p.x : p.x))
  const ys = face.map((p) => p.y)
  const x = Math.min(...xs), y = Math.min(...ys)
  return { x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y }
}

export function drawFaceOutlines(ctx, faces, { mirror = true, color = '#2dd4bf' } = {}) {
  // the outline of each face, with its number, on a 2D canvas the size of the preview
  const { width, height } = ctx.canvas
  const point = (p) => [(mirror ? 1 - p.x : p.x) * width, p.y * height]
  ctx.save()
  ctx.strokeStyle = ctx.fillStyle = color
  ctx.lineWidth = Math.max(2, width / 400)
  ctx.font = `600 ${Math.max(14, width / 50)}px system-ui, sans-serif`
  faces.forEach((face, i) => {
    ctx.beginPath()
    for (const { start, end } of FaceLandmarker.FACE_LANDMARKS_FACE_OVAL) {
      ctx.moveTo(...point(face[start]))
      ctx.lineTo(...point(face[end]))
    }
    ctx.stroke()
    const box = faceBox(face, { mirror })
    ctx.fillText(String(i + 1), box.x * width, box.y * height - 6)
  })
  ctx.restore()
}
