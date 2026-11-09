// run with: npm test
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { ImageServiceClient, ServiceError } from '../src/engine/service.js'

function fakeFetch(reply) {
  // records each request, and answers with reply(url, options) -> Response
  const calls = []
  const fetch = async (url, options) => {
    calls.push({ url, ...options })
    return reply(url, options)
  }
  return { fetch, calls }
}

test('requests go to the page server path, with no token', async () => {
  const { fetch, calls } = fakeFetch(() => Response.json({ status: 'ok', version: '0.2.0' }))
  const client = new ImageServiceClient({ baseUrl: '/image-service/', fetch })
  assert.deepEqual(await client.health(), { status: 'ok', version: '0.2.0' })
  assert.equal(calls[0].url, '/image-service/health')
  assert.equal(calls[0].headers.Authorization, undefined)
})

test('extra headers for the page server are sent', async () => {
  const { fetch, calls } = fakeFetch(() => Response.json({}))
  await new ImageServiceClient({ headers: { 'X-CSRF-Token': 'abc' }, fetch }).catalog()
  assert.equal(calls[0].url, '/image-service/v1/catalog')
  assert.equal(calls[0].headers['X-CSRF-Token'], 'abc')
})

test('a photo is uploaded as the "image" form field', async () => {
  const { fetch, calls } = fakeFetch(() => Response.json({ photo_id: 'p1', faces: 1 }, { status: 201 }))
  const info = await new ImageServiceClient({ fetch }).uploadPhoto(new Blob(['jpeg bytes'], { type: 'image/jpeg' }))
  assert.equal(info.photo_id, 'p1')
  assert.equal(calls[0].method, 'POST')
  assert.ok(calls[0].body instanceof FormData)
  assert.equal(calls[0].body.get('image').name, 'capture.jpg')
})

test('a video is uploaded as the "video" form field, with its length', async () => {
  const { fetch, calls } = fakeFetch(() => Response.json({ video_id: 'v1', file_url: '/v1/videos/v1/file' }, { status: 201 }))
  const info = await new ImageServiceClient({ fetch }).uploadVideo(new Blob(['mp4 bytes'], { type: 'video/mp4' }),
                                                                     { filename: 'clip.mp4', durationSeconds: 12.3456 })
  assert.equal(info.video_id, 'v1')
  assert.equal(calls[0].url, '/image-service/v1/videos')
  assert.equal(calls[0].method, 'POST')
  assert.equal(calls[0].body.get('video').name, 'clip.mp4')
  assert.equal(calls[0].body.get('duration_seconds'), '12.35')
})

test('a video can be deleted once the app has it', async () => {
  const { fetch, calls } = fakeFetch(() => new Response(null, { status: 204 }))
  await new ImageServiceClient({ fetch }).deleteVideo('v 1')
  assert.equal(calls[0].url, '/image-service/v1/videos/v%201')
  assert.equal(calls[0].method, 'DELETE')
})

test('render sends a cleaned look and returns the image and the service time', async () => {
  const { fetch, calls } = fakeFetch(() => new Response(new Blob(['img']), { headers: { 'X-Processing-Time-Ms': '68.4' } }))
  const result = await new ImageServiceClient({ fetch }).render('p1', { preset: 4, notALookSetting: 1 }, { maxWidth: 800 })
  const body = JSON.parse(calls[0].body)
  assert.equal(calls[0].url, '/image-service/v1/render')
  assert.equal(calls[0].headers['Content-Type'], 'application/json')
  assert.equal(body.photo_id, 'p1')
  assert.equal(body.look.preset, 4)
  assert.equal(body.look.notALookSetting, undefined)
  assert.equal(body.max_width, 800)
  assert.equal(result.ms, 68.4)
  assert.equal(await result.blob.text(), 'img')
})

test('compose keeps empty slots as null photos', async () => {
  const { fetch, calls } = fakeFetch(() => new Response(new Blob(['img'])))
  await new ImageServiceClient({ fetch }).compose([{ photoId: 'a', look: {} }, null], { layout: 'grid' })
  const body = JSON.parse(calls[0].body)
  assert.equal(body.layout, 'grid')
  assert.equal(body.slots[0].photo_id, 'a')
  assert.deepEqual(body.slots[1], { photo_id: null })
})

test("the service's error detail becomes the error message", async () => {
  const { fetch } = fakeFetch(() => Response.json({ detail: 'Photo "x" not found' }, { status: 404 }))
  await assert.rejects(new ImageServiceClient({ fetch }).render('x', {}), (error) => {
    assert.ok(error instanceof ServiceError)
    assert.equal(error.status, 404)
    assert.equal(error.message, 'Photo "x" not found')
    return true
  })
})

test('a reply that is not JSON still gives a useful error', async () => {
  const { fetch } = fakeFetch(() => new Response('<html>Bad gateway</html>', { status: 502, statusText: 'Bad Gateway' }))
  await assert.rejects(new ImageServiceClient({ fetch }).health(), { status: 502, message: '502 Bad Gateway' })
})

test('a service that cannot be reached gives status 0', async () => {
  const fetch = async () => { throw new TypeError('fetch failed') }
  await assert.rejects(new ImageServiceClient({ fetch }).health(), { status: 0 })
})
