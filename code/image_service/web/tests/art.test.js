// run with: npm test
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { fullQuad, mascotQuad, stickerQuad } from '../src/engine/art.js'

function face(left, right) {
  // a face with only the outer eye corners set (x, y from 0 to 1)
  const points = Array.from({ length: 478 }, () => ({ x: 0.5, y: 0.5 }))
  points[33] = { x: left[0], y: left[1] }
  points[263] = { x: right[0], y: right[1] }
  return points
}

const close = (actual, expected) => {
  actual.flat().forEach((v, i) => assert.ok(Math.abs(v - expected.flat()[i]) < 1e-9, `${actual} != ${expected}`))
}
const centre = (quad) => [(quad[0][0] + quad[2][0]) / 2, (quad[0][1] + quad[2][1]) / 2]

test('a level sticker is centred between the eyes, widthFactor times their distance', () => {
  // eyes 100 px apart at y = 100, on a 1000 x 1000 picture, no mirroring
  const quad = stickerQuad(face([0.1, 0.1], [0.2, 0.1]), { width: 1000, height: 1000, mirror: false,
                                                          widthFactor: 1.9, liftFactor: 0, aspect: 0.5 })
  close(quad, [[55, 52.5], [245, 52.5], [245, 147.5], [55, 147.5]])
})

test('lift moves the sticker up from the eyes, by eye distances', () => {
  const quad = stickerQuad(face([0.1, 0.5], [0.2, 0.5]), { width: 1000, height: 1000, mirror: false,
                                                          widthFactor: 1, liftFactor: 1.65, aspect: 1 })
  close([centre(quad)], [[150, 500 - 165]])
})

test('a tilted head tilts the sticker and lifts it along the tilt', () => {
  // eyes one above the other (head on its side): 90 degrees, so "up" points to +x
  const quad = stickerQuad(face([0.1, 0.1], [0.1, 0.2]), { width: 1000, height: 1000, mirror: false,
                                                          widthFactor: 1, liftFactor: 1, aspect: 1 })
  close([centre(quad)], [[200, 150]])
  // its top points right and its left points up, so its top left corner is up and to the right
  close([quad[0]], [[250, 100]])
})

test('mirroring keeps the sticker upright', () => {
  // same eyes as the level test: mirrored, the centre moves across, and the sticker isn't flipped over
  const quad = stickerQuad(face([0.1, 0.1], [0.2, 0.1]), { width: 1000, height: 1000, mirror: true,
                                                          widthFactor: 1.9, liftFactor: 0, aspect: 0.5 })
  close(quad, [[755, 52.5], [945, 52.5], [945, 147.5], [755, 147.5]])
})

test('stickers on tiny faces are skipped', () => {
  const options = { width: 100, height: 100, mirror: false, widthFactor: 1, liftFactor: 0, aspect: 1 }
  assert.equal(stickerQuad(face([0.5, 0.5], [0.55, 0.5]), options), null)          // 5 px wide
  assert.equal(stickerQuad(face([0.5, 0.5], [0.55, 0.5]), { ...options, minWidth: 4 }).length, 4)
})

test('the mascot stands in the bottom-right corner, at most 3/4 high and 45% wide', () => {
  // a tall mascot is limited by the height
  close(mascotQuad({ width: 1280, height: 720, imageWidth: 400, imageHeight: 800 }), [[1010, 180], [1280, 180], [1280, 720], [1010, 720]])
  // a wide one by the width
  close(mascotQuad({ width: 1000, height: 1000, imageWidth: 900, imageHeight: 300 }), [[550, 850], [1000, 850], [1000, 1000], [550, 1000]])
})

test('a fitted frame covers the whole picture', () => {
  close(fullQuad({ width: 640, height: 480 }), [[0, 0], [640, 0], [640, 480], [0, 480]])
})
