// booth-ui: the whole booth in plain JavaScript, mounted into any element on any page:
//
//   import { mountBooth } from './booth-ui.js'
//   const booth = mountBooth(document.querySelector('#booth'), {
//     serviceUrl: '/image-service',          // your server's route that forwards to the service; null = no service
//     onCapture: ({ blob, look, photoId, render }) => { ... },   // optional: e.g. save it in your app
//     onRecording: ({ blob, type, duration, stoppedBy }) => { ... },   // optional: each finished video
//     onVideoUploaded: ({ video_id, file_url }) => { ... },   // optional: a video sent to the service
//   })
//   booth.destroy()                          // stops the camera and removes the booth
//
// The live preview runs in the browser, art and all. Each capture is uploaded once, and the
// service's exact render of it is shown beside it. Videos record the preview; "Send to the
// service" uploads one, where the page's app can fetch it from file_url and pass it on (the
// service keeps videos but doesn't process them).
import { EffectRenderer, ImageServiceClient, MAX_RECORDING_SECONDS, RESOLUTIONS, WebcamBooth, builtInCatalog,
         formatDuration, listCameras } from '../src/engine/index.js'

const TIMERS = [0, 3, 5, 10]
// the time limits offered for a timed recording, in seconds (5 minutes at most)
const LIMITS = [10, 15, 30, 60, 120, 180, 300].filter((s) => s <= MAX_RECORDING_SECONDS)
const limitLabel = (s) => (s < 60 ? `${s} s` : `${s / 60} min`)
// text from the service (names, error messages) goes into HTML, so its < & " are escaped
const escape = (text) => String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
// the art pickers: catalog list and look setting (-1 = none)
const ART = [
  { list: 'stickers', key: 'sticker', label: 'Face sticker' },
  { list: 'backgrounds', key: 'background', label: 'Background' },
  { list: 'frames', key: 'frame', label: 'Frame' },
  { list: 'mascots', key: 'mascot', label: 'Mascot' },
]

const TEMPLATE = `
  <div class="booth">
    <section class="stage" aria-label="Camera">
      <div class="preview" data-ref="preview">
        <canvas class="live" data-ref="canvas"></canvas>
        <canvas class="overlay" data-ref="overlay"></canvas>
        <div class="countdown" data-ref="countdown" aria-live="assertive"></div>
        <div class="flash" data-ref="flash"></div>
        <div class="rec-badge" data-ref="recBadge" role="status" hidden></div>
        <p class="preview-message" data-ref="message">Starting the camera…</p>
      </div>
      <div class="status-bar">
        <span data-ref="fps">– fps</span>
        <span data-ref="faces">No faces</span>
        <span data-ref="tracking">Tracking: off</span>
        <span data-ref="segmenting" hidden></span>
        <span data-ref="resolution"></span>
        <span class="service-pill" data-ref="service">Service: checking…</span>
      </div>
      <div class="actions">
        <button class="capture" data-ref="capture" type="button" disabled>Capture <kbd>Space</kbd></button>
        <button class="record" data-ref="record" type="button" disabled>Record <kbd>R</kbd></button>
        <button class="record" data-ref="timedRecord" type="button" disabled>Timed record <kbd>T</kbd></button>
      </div>
      <div class="actions options">
        <label class="inline">Countdown
          <select data-ref="timer">${TIMERS.map((s) => `<option value="${s}" ${s === 3 ? 'selected' : ''}>${s ? `${s} s` : 'Off'}</option>`).join('')}</select>
        </label>
        <label class="inline">Time limit
          <select data-ref="limit">${LIMITS.map((s) => `<option value="${s}" ${s === 30 ? 'selected' : ''}>${limitLabel(s)}</option>`).join('')}</select>
        </label>
        <label class="inline check"><input type="checkbox" data-ref="sound" checked> Sound</label>
      </div>
    </section>

    <aside class="controls" aria-label="Controls">
      <details open>
        <summary>Camera</summary>
        <label>Camera <select data-ref="device"></select></label>
        <label>Resolution
          <select data-ref="resolutionPick">${RESOLUTIONS.map((r) => `<option value="${r.key}">${r.label}</option>`).join('')}</select>
        </label>
        <label class="check"><input type="checkbox" data-ref="mirror" checked> Mirror like a selfie camera</label>
        <label class="check"><input type="checkbox" data-ref="showFaces"> Show face outlines</label>
      </details>

      <details open>
        <summary>Adjust</summary>
        <label>Contrast <output data-ref="contrastOut">1.0</output>
          <input type="range" data-ref="contrast" min="0" max="3" step="0.1" value="1">
        </label>
        <label>Brightness <output data-ref="brightnessOut">50</output>
          <input type="range" data-ref="brightness" min="0" max="100" step="1" value="50">
        </label>
        <label>Filter <select data-ref="kernel"></select></label>
        <label class="check"><input type="checkbox" data-ref="grayscale"> Greyscale</label>
        <button type="button" class="link" data-ref="reset">Reset the look</button>
      </details>

      <details open>
        <summary>Preset <small><kbd>[</kbd> <kbd>]</kbd></small></summary>
        <div class="presets" data-ref="presets" role="radiogroup" aria-label="Preset"></div>
      </details>

      <details open>
        <summary>Stickers and art</summary>
        <p class="hint" data-ref="artHint" hidden>The art comes from the service, which isn't connected.</p>
        <div data-ref="art"></div>
        <label>Focus <select data-ref="focus"></select></label>
      </details>
    </aside>

    <section class="results" aria-label="Captures">
      <h2>Captures</h2>
      <p class="hint" data-ref="resultsHint">Nothing captured yet.</p>
      <ol class="captures" data-ref="captures"></ol>
    </section>
  </div>`


export function mountBooth(root, { serviceUrl = '/image-service', onCapture = null, onRecording = null,
                                   onVideoUploaded = null, mediapipe } = {}) {
  root.innerHTML = TEMPLATE
  const ref = Object.fromEntries([...root.querySelectorAll('[data-ref]')].map((el) => [el.dataset.ref, el]))
  const service = serviceUrl ? new ImageServiceClient({ baseUrl: serviceUrl }) : null
  const booth = new WebcamBooth({ canvas: ref.canvas, overlay: ref.overlay, mediapipe })
  const urls = []                              // object URLs to free on destroy
  const captures = []                          // { photoId, card } newest first
  let catalog = builtInCatalog()
  let serviceReady = false
  let busy = false                             // a countdown or upload is under way
  let recordingMode = null                     // 'free' or 'timed' while recording

  const objectUrl = (blob) => {
    const url = URL.createObjectURL(blob)
    urls.push(url)
    return url
  }
  const showMessage = (text) => {
    ref.message.textContent = text || ''
    ref.message.hidden = !text
  }

  // --- controls -------------------------------------------------------------------------
  function fillCatalog() {
    ref.kernel.innerHTML = catalog.filters.map((f) => `<option value="${f.index}">${escape(f.name)}</option>`).join('')
    ref.presets.innerHTML = catalog.presets.map((p) => {
      const live = EffectRenderer.hasShader(p.name)
      return `<button type="button" role="radio" data-preset="${p.index}" aria-checked="false"
                ${live ? '' : 'class="final-only" title="Shown in the final picture only"'}>${escape(p.name)}</button>`
    }).join('')
    // a row of thumbnails per kind of art, with None first
    ref.art.innerHTML = ART.map(({ list, key, label }) => {
      const items = catalog[list] || []
      if (!items.length) return ''
      const button = (value, inner, name) =>
        `<button type="button" role="radio" data-art="${key}" data-value="${value}" aria-checked="false"
                 title="${escape(name)}" aria-label="${escape(name)}">${inner}</button>`
      return `<fieldset class="art-picker"><legend>${label}</legend>
        <div class="thumbs" role="radiogroup" aria-label="${label}">
          ${button(-1, '<span>None</span>', 'None')}
          ${items.map((item) => button(item.index, `<img src="${escape(service.url(item.thumbnail))}" alt="" loading="lazy">`, item.name)).join('')}
        </div></fieldset>`
    }).join('')
    ref.artHint.hidden = serviceReady
    ref.focus.innerHTML = catalog.focus_modes.map((m) => `<option value="${m.index}">${escape(m.name)}</option>`).join('')
    syncControls()
  }

  function syncControls() {
    const look = booth.look
    ref.contrast.value = look.contrast
    ref.contrastOut.textContent = Number(look.contrast).toFixed(1)
    ref.brightness.value = look.brightness
    ref.brightnessOut.textContent = look.brightness
    ref.kernel.value = look.kernel
    ref.grayscale.checked = Boolean(look.grayscale)
    for (const button of ref.presets.querySelectorAll('[data-preset]')) {
      button.setAttribute('aria-checked', String(Number(button.dataset.preset) === look.preset))
    }
    for (const button of ref.art.querySelectorAll('[data-art]')) {
      button.setAttribute('aria-checked', String(Number(button.dataset.value) === look[button.dataset.art]))
    }
    ref.focus.value = look.focus
  }

  function setLook(changes) {
    booth.setLook(changes)
    syncControls()
  }

  ref.contrast.addEventListener('input', () => setLook({ contrast: Number(ref.contrast.value) }))
  ref.brightness.addEventListener('input', () => setLook({ brightness: Number(ref.brightness.value) }))
  ref.kernel.addEventListener('change', () => setLook({ kernel: Number(ref.kernel.value) }))
  ref.grayscale.addEventListener('change', () => setLook({ grayscale: ref.grayscale.checked ? 1 : 0 }))
  ref.reset.addEventListener('click', () => setLook({ ...catalog.look_defaults, props: [] }))
  ref.presets.addEventListener('click', (event) => {
    const button = event.target.closest('[data-preset]')
    if (button) setLook({ preset: Number(button.dataset.preset) })
  })
  ref.art.addEventListener('click', (event) => {
    const button = event.target.closest('[data-art]')
    if (button) setLook({ [button.dataset.art]: Number(button.dataset.value) })
  })
  ref.focus.addEventListener('change', () => setLook({ focus: Number(ref.focus.value) }))
  ref.mirror.addEventListener('change', () => { booth.mirror = ref.mirror.checked })
  ref.showFaces.addEventListener('change', () => { booth.showFaces = ref.showFaces.checked })
  ref.device.addEventListener('change', () => startCamera())
  ref.resolutionPick.addEventListener('change', () => startCamera())
  ref.capture.addEventListener('click', () => capture())
  ref.record.addEventListener('click', () => toggleRecording('free'))
  ref.timedRecord.addEventListener('click', () => toggleRecording('timed'))

  function onKey(event) {
    if (event.target.closest('input, select, textarea') || event.ctrlKey || event.metaKey || event.altKey) return
    const count = catalog.presets.length
    if (event.key === ' ') {
      event.preventDefault()
      capture()
    } else if (event.key === 'r' || event.key === 't') {
      toggleRecording(event.key === 'r' ? 'free' : 'timed')
    } else if (event.key === ']' || event.key === '[') {
      setLook({ preset: (booth.look.preset + (event.key === ']' ? 1 : count - 1)) % count })
    }
  }
  document.addEventListener('keydown', onKey)

  // --- camera and status ------------------------------------------------------------------
  booth.addEventListener('status', ({ detail }) => {
    ref.fps.textContent = `${detail.fps} fps`
    ref.faces.textContent = detail.faces === 1 ? '1 face' : detail.faces ? `${detail.faces} faces` : 'No faces'
    ref.tracking.textContent = `Tracking: ${detail.tracking}`
    // finding the person only starts once a background or focus effect is picked
    ref.segmenting.hidden = detail.segmenting === 'off'
    ref.segmenting.textContent = `Person: ${detail.segmenting}`
  })
  booth.addEventListener('error', ({ detail }) => toast(detail.message))

  async function startCamera() {
    ref.capture.disabled = true
    showMessage('Starting the camera…')
    try {
      const size = await booth.start({ deviceId: ref.device.value || null, resolution: ref.resolutionPick.value })
      ref.resolution.textContent = `${size.width} x ${size.height}`
      showMessage('')
      ref.capture.disabled = false
      updateRecordingUi()
      await fillDevices()
    } catch (error) {
      const reasons = {
        NotAllowedError: 'The camera was blocked. Allow it in the browser’s address bar, then reload.',
        NotFoundError: 'No camera was found.',
        NotReadableError: 'The camera is in use by another app.',
      }
      showMessage(reasons[error.name] || `The camera couldn't start: ${error.message}`)
    }
  }

  async function fillDevices() {
    // names only appear after the camera is allowed, so this runs after it starts
    const cameras = await listCameras()
    const current = booth.camera.deviceId
    ref.device.innerHTML = cameras.map((c) => `<option value="${escape(c.deviceId)}">${escape(c.label)}</option>`).join('')
    if (current) ref.device.value = current
  }

  async function connectService() {
    if (!service) {
      ref.service.textContent = 'No service: live preview only'
      return
    }
    try {
      const health = await service.health()
      catalog = await service.catalog()
      booth.setCatalog(catalog, { artUrl: (path) => service.url(path) })
      serviceReady = true
      ref.service.textContent = `Service ${health.version}`
      ref.service.classList.add('ok')
    } catch (error) {
      ref.service.textContent = 'Service unavailable: live preview only'
      ref.service.classList.add('down')
      ref.service.title = error.message
    }
    fillCatalog()
  }

  // --- capture ----------------------------------------------------------------------------
  async function countdown(seconds) {
    for (let s = seconds; s > 0; s--) {
      ref.countdown.textContent = s
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    ref.countdown.textContent = ''
  }

  async function capture() {
    if (busy || !booth.running) return
    busy = true
    ref.capture.disabled = true
    updateRecordingUi()
    try {
      await countdown(Number(ref.timer.value))
      ref.flash.classList.remove('go')
      void ref.flash.offsetWidth                // restart the flash animation
      ref.flash.classList.add('go')
      const shot = await booth.capture()
      const card = addCard(shot)
      if (serviceReady) {
        await sendToService(shot, card)
      } else {
        card.querySelector('.render').innerHTML = '<p class="hint">No service: only the unedited photo was kept.</p>'
        onCapture?.({ ...shot, photoId: null, render: null })
      }
    } catch (error) {
      toast(error.message)
    } finally {
      busy = false
      ref.capture.disabled = !booth.running
      updateRecordingUi()
    }
  }

  // --- video --------------------------------------------------------------------------------
  async function toggleRecording(mode) {
    // starts a recording ('free': until stopped; 'timed': up to the time limit), or stops one
    if (booth.recorder.recording) {
      booth.stopRecording()                    // the recorder's 'stop' event adds the video
      return
    }
    if (busy || !booth.running) return
    busy = true
    updateRecordingUi()
    try {
      await countdown(Number(ref.timer.value))
      const limitSeconds = mode === 'timed' ? Number(ref.limit.value) : null
      const started = await booth.startRecording({ limitSeconds, audio: ref.sound.checked })
      recordingMode = mode
      if (ref.sound.checked && !started.audio) toast('No microphone was allowed, so this video has no sound.')
    } catch (error) {
      toast(`The recording couldn't start: ${error.message}`)
    } finally {
      busy = false
      updateRecordingUi()
    }
  }

  function updateRecordingUi() {
    const on = booth.recorder.recording
    const button = (el, mode, label, key) => {
      const active = on && recordingMode === mode
      el.innerHTML = `${active ? 'Stop' : label} <kbd>${key}</kbd>`
      el.classList.toggle('recording', active)
      el.disabled = !booth.running || (busy && !on) || (on && !active)
    }
    button(ref.record, 'free', 'Record', 'R')
    button(ref.timedRecord, 'timed', 'Timed record', 'T')
    ref.recBadge.hidden = !on
    // the video keeps the preview's size, so the camera can't change while recording
    for (const el of [ref.device, ref.resolutionPick, ref.limit, ref.sound]) el.disabled = on
  }

  booth.recorder.addEventListener('tick', ({ detail }) => {
    const { elapsed, remaining } = detail
    ref.recBadge.textContent = remaining === null
      ? `REC ${formatDuration(elapsed)}`
      : `REC ${formatDuration(elapsed)} / ${formatDuration(booth.recorder.limit)} · ${formatDuration(Math.ceil(remaining))} left`
  })

  booth.recorder.addEventListener('stop', ({ detail: video }) => {
    recordingMode = null
    updateRecordingUi()
    addVideoCard(video)
    onRecording?.(video)
  })

  booth.recorder.addEventListener('error', ({ detail }) => toast(detail.message))

  function addVideoCard(video) {
    ref.resultsHint.hidden = true
    const url = objectUrl(video.blob)
    const card = document.createElement('li')
    card.className = 'capture-card video-card'
    const notes = [
      formatDuration(video.duration), `${video.width} x ${video.height}`,
      `${(video.blob.size / (1024 * 1024)).toFixed(1)} MB`, video.audio ? 'with sound' : 'no sound',
      ...(video.stoppedBy === 'limit' ? ['stopped at the time limit'] : []),
    ]
    card.innerHTML = `
      <figure>
        <video src="${url}" controls playsinline preload="metadata"></video>
        <figcaption>Video · ${notes.join(' · ')}
          · <a href="${url}" download="recording.${video.extension}">Save</a>
          ${serviceReady ? '<span data-send>· <button type="button" class="link" data-send-video>Send to the service</button></span>' : ''}
          <span class="video-upload" data-upload-status></span></figcaption>
      </figure>`
    card.querySelector('[data-send-video]')?.addEventListener('click', (event) => sendVideo(video, card, event.target))
    ref.captures.prepend(card)
  }

  async function sendVideo(video, card, button) {
    // the service keeps it for a while; the page's app fetches it from file_url and passes it on
    const status = card.querySelector('[data-upload-status]')
    button.disabled = true
    status.textContent = `· Sending ${(video.blob.size / (1024 * 1024)).toFixed(1)} MB…`
    try {
      const info = await service.uploadVideo(video.blob, { filename: `recording.${video.extension}`,
                                                           durationSeconds: video.duration })
      const expires = new Date(info.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      card.querySelector('[data-send]').remove()
      status.innerHTML = `· On the service as <code>${escape(info.video_id)}</code> until ${expires}
        · <a href="${escape(service.url(info.file_url))}" download>Download from the service</a>`
      onVideoUploaded?.(info)
    } catch (error) {
      button.disabled = false
      status.innerHTML = `· <span class="error">${escape(error.message)}</span>`
    }
  }

  function addCard(shot) {
    ref.resultsHint.hidden = true
    const card = document.createElement('li')
    card.className = 'capture-card'
    const photoUrl = objectUrl(shot.blob)
    card.innerHTML = `
      <figure>
        <img src="${photoUrl}" alt="The captured photo, unedited">
        <figcaption>Captured · ${shot.width} x ${shot.height} · ${(shot.blob.size / 1024).toFixed(0)} KB
          · <a href="${photoUrl}" download="capture.jpg">Save</a></figcaption>
      </figure>
      <figure class="render"><p class="hint">Uploading…</p></figure>`
    ref.captures.prepend(card)
    return card
  }

  async function sendToService(shot, card) {
    const info = await service.uploadPhoto(shot.blob)
    const entry = { photoId: info.photo_id, card, info }
    captures.unshift(entry)
    const render = await renderInto(entry, shot.look)
    onCapture?.({ ...shot, photoId: info.photo_id, render })
  }

  async function renderInto(entry, look) {
    const target = entry.card.querySelector('.render')
    target.classList.add('working')
    try {
      const render = await service.render(entry.photoId, look)
      const url = objectUrl(render.blob)
      const faces = entry.info.faces === 1 ? '1 face' : `${entry.info.faces} faces`
      target.innerHTML = `
        <img src="${url}" alt="The service's finished picture">
        <figcaption>Service render · ${render.ms ?? '?'} ms · ${faces} found in the still
          · <a href="${url}" download="render.jpg">Save</a>
          · <button type="button" class="link" data-rerender>Render with the current look</button></figcaption>`
      return render
    } catch (error) {
      target.innerHTML = `<p class="error">${escape(error.message)}</p>`
      return null
    } finally {
      target.classList.remove('working')
    }
  }

  ref.captures.addEventListener('click', (event) => {
    // the photo is already on the service, so a new look is just another render
    const button = event.target.closest('[data-rerender]')
    const entry = button && captures.find((c) => c.card.contains(button))
    if (entry) renderInto(entry, booth.look)
  })

  function toast(text) {
    const note = document.createElement('div')
    note.className = 'toast'
    note.setAttribute('role', 'status')
    note.textContent = text
    root.querySelector('.booth').append(note)
    setTimeout(() => note.remove(), 6000)
  }

  // --- start --------------------------------------------------------------------------------
  fillCatalog()
  connectService()
  startCamera()

  return {
    booth,
    destroy() {
      document.removeEventListener('keydown', onKey)
      booth.dispose()
      urls.forEach((url) => URL.revokeObjectURL(url))
      root.innerHTML = ''
    },
  }
}
