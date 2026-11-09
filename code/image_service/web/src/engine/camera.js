// camera: the webcam in the browser (the desktop booth's desktop/sources.py). Pages need
// https or localhost for the browser to allow the camera.

// what the resolution picker offers; "best" asks for 4K and the camera gives its nearest
export const RESOLUTIONS = [
  { key: 'best', label: 'Best available', width: 3840, height: 2160 },
  { key: '1080p', label: '1920 x 1080', width: 1920, height: 1080 },
  { key: '720p', label: '1280 x 720', width: 1280, height: 720 },
  { key: '480p', label: '640 x 480', width: 640, height: 480 },
]

export async function listCameras() {
  // the cameras on this device; their names only appear once the page may use the camera
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices
    .filter((d) => d.kind === 'videoinput')
    .map((d, i) => ({ deviceId: d.deviceId, label: d.label || `Camera ${i + 1}` }))
}

export class Camera {
  constructor(video = document.createElement('video')) {
    this.video = video
    this.video.muted = true
    this.video.playsInline = true
    this.stream = null
  }

  get running() { return this.stream !== null }
  get width() { return this.video.videoWidth }
  get height() { return this.video.videoHeight }
  get deviceId() { return this.stream?.getVideoTracks()[0]?.getSettings().deviceId ?? null }

  async start({ deviceId = null, resolution = 'best' } = {}) {
    // starts (or switches) the camera; throws the browser's error if it's refused or missing
    this.stop()
    const size = RESOLUTIONS.find((r) => r.key === resolution) || RESOLUTIONS[0]
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        width: { ideal: size.width },
        height: { ideal: size.height },
        frameRate: { ideal: 30 },
      },
    })
    this.video.srcObject = this.stream
    await this.video.play()
    return { width: this.width, height: this.height }
  }

  stop() {
    this.stream?.getTracks().forEach((track) => track.stop())
    this.stream = null
    this.video.srcObject = null
  }

  captureCanvas({ mirror = true } = {}) {
    // the current frame at the camera's full resolution, unedited, mirrored like the preview
    // (the desktop booth mirrors its frames too, so captures match)
    const canvas = document.createElement('canvas')
    canvas.width = this.width
    canvas.height = this.height
    const ctx = canvas.getContext('2d')
    if (mirror) {
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height)
    return canvas
  }

  async capture({ mirror = true, type = 'image/jpeg', quality = 0.95 } = {}) {
    // the current frame as a file to upload. JPEG at 0.95 keeps the detail and stays well
    // under the service's 15 MB upload limit even at 4K; PNG is lossless but much bigger.
    const canvas = this.captureCanvas({ mirror })
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, type, quality))
    return { blob, width: canvas.width, height: canvas.height }
  }
}
