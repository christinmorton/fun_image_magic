// service: talks to the image service through the page's own server. The page never has the
// service token: baseUrl is a path on the page's server that forwards each request to the
// service and adds "Authorization: Bearer <IMAGE_SERVICE_TOKEN>" (vite.config.js does this in
// development). Routes are the service's own, e.g. baseUrl + '/v1/render'.
import { toServiceLook } from './presets.js'

export class ServiceError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail))
    this.name = 'ServiceError'
    this.status = status                   // the HTTP status (0 if the service couldn't be reached)
    this.detail = detail
  }
}

export class ImageServiceClient {
  constructor({ baseUrl = '/image-service', headers = {}, fetch: fetchFn } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.headers = headers                 // extra headers for the page's own server (e.g. a CSRF token)
    this.fetch = fetchFn || globalThis.fetch.bind(globalThis)
  }

  url(path) {
    // a service path (as in the catalog's thumbnail links) -> a URL on the page's server
    return this.baseUrl + path
  }

  async health() {
    return (await this.#request('/health')).json()
  }

  async catalog() {
    return (await this.#request('/v1/catalog')).json()
  }

  async uploadPhoto(blob, filename = 'capture.jpg') {
    // upload once; the reply's photo_id can then be rendered with any number of looks
    const form = new FormData()
    form.append('image', blob, filename)
    return (await this.#request('/v1/photos', { method: 'POST', body: form })).json()
  }

  async deletePhoto(photoId) {
    await this.#request(`/v1/photos/${encodeURIComponent(photoId)}`, { method: 'DELETE' })
  }

  async render(photoId, look, { format = 'jpeg', quality = 92, maxWidth = null } = {}) {
    // the exact finished picture: { blob, ms } (ms: how long the service worked on it)
    const body = { photo_id: photoId, look: toServiceLook(look), format, quality }
    if (maxWidth) body.max_width = maxWidth
    return this.#image('/v1/render', body)
  }

  async compose(slots, { layout = 'strip', format = 'jpeg', quality = 92, maxWidth = null } = {}) {
    // up to four { photoId, look } (null for an empty slot) -> one strip or grid: { blob, ms }
    const body = {
      layout, format, quality,
      slots: slots.map((slot) => (slot ? { photo_id: slot.photoId, look: toServiceLook(slot.look) } : { photo_id: null })),
    }
    if (maxWidth) body.max_width = maxWidth
    return this.#image('/v1/compose', body)
  }

  async startAiJob(photoId, preset) {
    // AI costs money on the service's account; it refuses when its daily limit is reached
    return (await this.#request('/v1/ai/jobs', { method: 'POST', json: { photo_id: photoId, preset } })).json()
  }

  async aiJob(jobId) {
    return (await this.#request(`/v1/ai/jobs/${encodeURIComponent(jobId)}`)).json()
  }

  watchAiJob(jobId, { onProgress = () => {}, onDone = () => {}, onFailed = () => {} } = {}) {
    // live progress from the service's event stream; returns a function that stops watching
    const source = new EventSource(this.url(`/v1/ai/jobs/${encodeURIComponent(jobId)}/events`))
    const handle = (callback, last) => (event) => {
      callback(JSON.parse(event.data))
      if (last) source.close()
    }
    source.addEventListener('progress', handle(onProgress, false))
    source.addEventListener('done', handle(onDone, true))
    source.addEventListener('failed', handle(onFailed, true))
    source.onerror = () => {
      if (source.readyState === EventSource.CLOSED) onFailed({ error: 'the progress stream closed' })
    }
    return () => source.close()
  }

  async #image(path, body) {
    const response = await this.#request(path, { method: 'POST', json: body })
    return { blob: await response.blob(), ms: Number(response.headers.get('X-Processing-Time-Ms')) || null }
  }

  async #request(path, { method = 'GET', json, body } = {}) {
    const headers = { ...this.headers }
    if (json !== undefined) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(json)
    }
    let response
    try {
      response = await this.fetch(this.url(path), { method, headers, body })
    } catch (error) {
      throw new ServiceError(0, `The image service couldn't be reached (${error.message})`)
    }
    if (!response.ok) {
      // FastAPI replies {"detail": ...}; a proxy with no service behind it may reply with HTML
      let detail = `${response.status} ${response.statusText}`
      try { detail = (await response.json()).detail ?? detail } catch { /* not JSON */ }
      throw new ServiceError(response.status, detail)
    }
    return response
  }
}
