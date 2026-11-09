// tracker: MediaPipe's face landmarker in the browser, in video mode like the desktop booth
// (core/tracking.py), so a face found once is followed from frame to frame as it turns.
// The service only sees single stills, where faces at an angle are hardest to find.
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'

// where the page loads MediaPipe's files from (vite.config.js serves them in development)
export const DEFAULT_MEDIAPIPE = {
  wasmBaseUrl: '/mediapipe/wasm',
  faceModelUrl: '/mediapipe/models/face_landmarker.task',
}

export class FaceTracker {
  static async create({ wasmBaseUrl = DEFAULT_MEDIAPIPE.wasmBaseUrl, faceModelUrl = DEFAULT_MEDIAPIPE.faceModelUrl,
                        numFaces = 4 } = {}) {
    const fileset = await FilesetResolver.forVisionTasks(wasmBaseUrl)
    const options = (delegate) => ({
      baseOptions: { modelAssetPath: faceModelUrl, delegate },
      runningMode: 'VIDEO',
      numFaces,                          // the same as core/tracking.py
    })
    // the GPU is much faster; some browsers and machines can't use it, so fall back
    let landmarker, delegate
    try {
      landmarker = await FaceLandmarker.createFromOptions(fileset, options('GPU'))
      delegate = 'GPU'
    } catch {
      landmarker = await FaceLandmarker.createFromOptions(fileset, options('CPU'))
      delegate = 'CPU'
    }
    return new FaceTracker(landmarker, delegate)
  }

  constructor(landmarker, delegate) {
    this.landmarker = landmarker
    this.delegate = delegate               // 'GPU' or 'CPU', for showing on the page
    this.lastTimestamp = -1
  }

  detect(video, now = performance.now()) {
    // the faces in this frame: one list of 478 points per face, x and y from 0 to 1 of the
    // camera's own (unmirrored) picture. Video mode needs timestamps that always go up.
    const timestamp = Math.max(Math.round(now), this.lastTimestamp + 1)
    this.lastTimestamp = timestamp
    return this.landmarker.detectForVideo(video, timestamp).faceLandmarks
  }

  close() {
    this.landmarker.close()
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
