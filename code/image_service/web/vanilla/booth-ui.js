// booth-ui: the whole booth in plain JavaScript, mounted into any element on any page:
//
//   import { mountBooth } from './booth-ui.js'
//   const booth = mountBooth(document.querySelector('#booth'), {
//     serviceUrl: '/image-service',          // your server's route that forwards to the service; null = no service
//     onCapture: ({ blob, look, photoId, render }) => { ... },   // optional: e.g. save it in your app
//   })
//   booth.destroy()                          // stops the camera and removes the booth
//
// The live preview runs in the browser. Each capture is uploaded once, and the service's
// exact render of it is shown beside it, re-rendered when the look changes.
import { EffectRenderer, ImageServiceClient, RESOLUTIONS, WebcamBooth, builtInCatalog, listCameras } from '../src/engine/index.js'

const TIMERS = [0, 3, 5, 10]
// text from the service (names, error messages) goes into HTML, so its < & " are escaped
const escape = (text) => String(text).replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`)
// the final-render extras: catalog list, look setting, and the value for off
const EXTRAS = [
  { list: 'stickers', key: 'sticker', label: 'Face sticker', off: -1 },
  { list: 'backgrounds', key: 'background', label: 'Background', off: -1 },
  { list: 'frames', key: 'frame', label: 'Frame', off: -1 },
  { list: 'mascots', key: 'mascot', label: 'Mascot', off: -1 },
  { list: 'focus_modes', key: 'focus', label: 'Focus', off: 0, skipFirst: true },
]

const TEMPLATE = `
  <div class="booth">
    <section class="stage" aria-label="Camera">
      <div class="preview" data-ref="preview">
        <canvas class="live" data-ref="canvas"></canvas>
        <canvas class="overlay" data-ref="overlay"></canvas>
        <div class="countdown" data-ref="countdown" aria-live="assertive"></div>
        <div class="flash" data-ref="flash"></div>
        <p class="preview-message" data-ref="message">Starting the camera…</p>
      </div>
      <div class="status-bar">
        <span data-ref="fps">– fps</span>
        <span data-ref="faces">No faces</span>
        <span data-ref="tracking">Tracking: off</span>
        <span data-ref="resolution"></span>
        <span class="service-pill" data-ref="service">Service: checking…</span>
      </div>
      <div class="actions">
        <button class="capture" data-ref="capture" type="button" disabled>Capture <kbd>Space</kbd></button>
        <label class="inline">Timer
          <select data-ref="timer">${TIMERS.map((s) => `<option value="${s}" ${s === 3 ? 'selected' : ''}>${s ? `${s} s` : 'Off'}</option>`).join('')}</select>
        </label>
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
        <label class="check"><input type="checkbox" data-ref="showFaces" checked> Show face outlines</label>
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
        <summary>In the final picture</summary>
        <p class="hint">Added by the service when it renders a capture.</p>
        <div data-ref="extras"></div>
      </details>
    </aside>

    <section class="results" aria-label="Captures">
      <h2>Captures</h2>
      <p class="hint" data-ref="resultsHint">Nothing captured yet.</p>
      <ol class="captures" data-ref="captures"></ol>
    </section>
  </div>`


export function mountBooth(root, { serviceUrl = '/image-service', onCapture = null, mediapipe } = {}) {
  root.innerHTML = TEMPLATE
  const ref = Object.fromEntries([...root.querySelectorAll('[data-ref]')].map((el) => [el.dataset.ref, el]))
  const service = serviceUrl ? new ImageServiceClient({ baseUrl: serviceUrl }) : null
  const booth = new WebcamBooth({ canvas: ref.canvas, overlay: ref.overlay, mediapipe })
  const urls = []                              // object URLs to free on destroy
  const captures = []                          // { photoId, card } newest first
  let catalog = builtInCatalog()
  let serviceReady = false
  let busy = false

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
    ref.extras.innerHTML = EXTRAS.map((extra) => {
      const items = (catalog[extra.list] || []).filter((item) => !(extra.skipFirst && item.index === 0))
      const disabled = !serviceReady || !items.length ? 'disabled' : ''
      return `<label>${extra.label}
        <select data-extra="${extra.key}" ${disabled}>
          <option value="${extra.off}">None</option>
          ${items.map((item) => `<option value="${item.index}">${escape(item.name)}</option>`).join('')}
        </select></label>`
    }).join('')
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
    for (const select of ref.extras.querySelectorAll('[data-extra]')) select.value = look[select.dataset.extra]
  }

  function setLook(changes, { rerender = false } = {}) {
    booth.setLook(changes)
    syncControls()
    if (rerender) rerenderLatest()
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
  ref.extras.addEventListener('change', (event) => {
    // extras only show in the service's render, so the latest capture is rendered again
    const select = event.target.closest('[data-extra]')
    if (select) setLook({ [select.dataset.extra]: Number(select.value) }, { rerender: true })
  })
  ref.mirror.addEventListener('change', () => { booth.mirror = ref.mirror.checked })
  ref.showFaces.addEventListener('change', () => { booth.showFaces = ref.showFaces.checked })
  ref.device.addEventListener('change', () => startCamera())
  ref.resolutionPick.addEventListener('change', () => startCamera())
  ref.capture.addEventListener('click', () => capture())

  function onKey(event) {
    if (event.target.closest('input, select, textarea') || event.ctrlKey || event.metaKey || event.altKey) return
    const count = catalog.presets.length
    if (event.key === ' ') {
      event.preventDefault()
      capture()
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
      booth.setCatalog(catalog)
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
          · <a href="${url}" download="render.jpg">Save</a></figcaption>`
      return render
    } catch (error) {
      target.innerHTML = `<p class="error">${escape(error.message)}</p>`
      return null
    } finally {
      target.classList.remove('working')
    }
  }

  function rerenderLatest() {
    if (captures.length && serviceReady) renderInto(captures[0], booth.look)
  }

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
