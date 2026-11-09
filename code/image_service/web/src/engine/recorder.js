// recorder: video of the live preview (effects, stickers, frame and all) with the browser's
// MediaRecorder, either until it's stopped or for a set time of up to 5 minutes. The
// service doesn't take videos, so a recording is a file in the browser for the page to keep.

export const MAX_RECORDING_SECONDS = 5 * 60

// the formats to try, best first: MP4 plays almost everywhere and knows its own length;
// WebM is what older Chrome and Firefox make
const VIDEO_TYPES = [
  'video/mp4;codecs=avc1,mp4a.40.2',
  'video/mp4',
  'video/webm;codecs=vp9,opus',
  'video/webm;codecs=vp8,opus',
  'video/webm',
]

export function pickVideoType(isSupported = (type) => MediaRecorder.isTypeSupported(type)) {
  // the first format this browser can record, or '' to let it choose
  return VIDEO_TYPES.find((type) => isSupported(type)) || ''
}

export function timeLimit(seconds) {
  // a time limit in whole seconds from 1 to 5 minutes, or null for none
  if (seconds === null || seconds === undefined || seconds === '') return null
  const value = Math.round(Number(seconds))
  if (!Number.isFinite(value) || value <= 0) return null
  return Math.min(value, MAX_RECORDING_SECONDS)
}

export function formatDuration(seconds) {
  // 75.4 -> '1:15'
  const whole = Math.max(0, Math.floor(seconds))
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`
}

export function fileExtension(type) {
  return type.startsWith('video/mp4') ? 'mp4' : 'webm'
}

export class Recorder extends EventTarget {
  // Events: 'tick' (detail: { elapsed, remaining }; remaining is null without a limit),
  // 'stop' (detail: the recording, as returned by stop()), 'error' (detail: an Error)
  constructor(canvas, { frameRate = 30, videoBitsPerSecond = 4_000_000 } = {}) {
    super()
    this.canvas = canvas
    this.frameRate = frameRate
    this.videoBitsPerSecond = videoBitsPerSecond
    this._session = null
  }

  get recording() { return this._session !== null }
  get elapsed() { return this._session ? (performance.now() - this._session.started) / 1000 : 0 }
  get limit() { return this._session?.limit ?? null }

  async start({ limitSeconds = null, audio = true } = {}) {
    // starts recording; with limitSeconds it stops by itself after that long (5 minutes at
    // most). audio adds the microphone; if it's refused, the video is recorded silent and
    // the result says so (audio: false).
    if (this._session) throw new Error('Already recording')
    const stream = this.canvas.captureStream(this.frameRate)
    let microphone = null
    if (audio) {
      try {
        microphone = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        microphone.getAudioTracks().forEach((track) => stream.addTrack(track))
      } catch {
        microphone = null                  // no microphone, or it was refused
      }
    }
    const type = pickVideoType()
    const recorder = new MediaRecorder(stream, { mimeType: type || undefined, videoBitsPerSecond: this.videoBitsPerSecond })
    const limit = timeLimit(limitSeconds)
    const session = {
      recorder, stream, microphone, limit, chunks: [], stoppedBy: 'user',
      started: performance.now(), width: this.canvas.width, height: this.canvas.height,
    }
    this._session = session
    session.done = new Promise((resolve) => {
      recorder.ondataavailable = (event) => { if (event.data.size) session.chunks.push(event.data) }
      recorder.onstop = () => resolve(this._finish(session))
      recorder.onerror = (event) => {
        this.dispatchEvent(new CustomEvent('error', { detail: event.error || new Error('The recording failed') }))
      }
    })
    recorder.start(1000)                   // hand over the video every second, so little is lost if the page closes
    session.ticker = setInterval(() => this._tick(), 250)
    if (limit) session.timer = setTimeout(() => this.stop('limit'), limit * 1000)
    this._tick()
    return { type: recorder.mimeType, limit, audio: Boolean(microphone) }
  }

  stop(reason = 'user') {
    // stops recording; resolves with { blob, type, extension, duration, width, height,
    // audio, stoppedBy: 'user' | 'limit' }
    const session = this._session
    if (!session) return Promise.resolve(null)
    if (session.recorder.state !== 'inactive') {
      session.stoppedBy = reason
      session.duration = Math.min((performance.now() - session.started) / 1000, session.limit ?? Infinity)
      session.recorder.stop()
    }
    return session.done
  }

  _tick() {
    const session = this._session
    if (!session) return
    const elapsed = this.elapsed
    const remaining = session.limit ? Math.max(0, session.limit - elapsed) : null
    this.dispatchEvent(new CustomEvent('tick', { detail: { elapsed, remaining } }))
  }

  _finish(session) {
    clearInterval(session.ticker)
    clearTimeout(session.timer)
    session.stream.getTracks().forEach((track) => track.stop())   // the canvas track, and the microphone
    this._session = null
    const type = session.recorder.mimeType || session.chunks[0]?.type || 'video/webm'
    const result = {
      blob: new Blob(session.chunks, { type }),
      type,
      extension: fileExtension(type),
      duration: session.duration ?? (performance.now() - session.started) / 1000,
      width: session.width,
      height: session.height,
      audio: Boolean(session.microphone),
      stoppedBy: session.stoppedBy,
    }
    this.dispatchEvent(new CustomEvent('stop', { detail: result }))
    return result
  }
}
