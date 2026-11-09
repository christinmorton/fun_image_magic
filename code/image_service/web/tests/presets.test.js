// run with: npm test
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { DEFAULT_LOOK, KERNELS, PRESET_NAMES, builtInCatalog, hexToRgb, previewScale, toServiceLook } from '../src/engine/presets.js'

test('every kernel is a 5 x 5 grid', () => {
  for (const kernel of KERNELS) assert.equal(kernel.weights.length, 25, kernel.name)
})

test('blurs keep the brightness the same (their weights add up to 1)', () => {
  for (const name of ['Blur (light)', 'Blur (strong)', 'Box blur']) {
    const sum = KERNELS.find((k) => k.name === name).weights.reduce((a, b) => a + b, 0)
    assert.ok(Math.abs(sum - 1) < 1e-9, `${name} adds up to ${sum}`)
  }
})

test('3 x 3 kernels sit in the middle of the 5 x 5 grid', () => {
  const sharpen = KERNELS.find((k) => k.name === 'Sharpen').weights
  assert.equal(sharpen[12], 5)                         // the centre
  assert.deepEqual([sharpen[7], sharpen[11], sharpen[13], sharpen[17]], [-1, -1, -1, -1])
  assert.equal(sharpen.filter((w) => w !== 0).length, 5)
})

test('a service look has every setting and nothing else', () => {
  const look = toServiceLook({ preset: 4, contrast: '1.5', grayscale: true, extra: 'dropped' })
  assert.deepEqual(Object.keys(look).sort(), Object.keys(DEFAULT_LOOK).sort())
  assert.equal(look.preset, 4)
  assert.equal(look.contrast, 1.5)
  assert.equal(look.grayscale, 1)
  assert.equal(look.sticker, -1)
})

test('service looks use whole numbers where the service wants them', () => {
  const look = toServiceLook({ brightness: 61.6, kernel: 2.2 })
  assert.equal(look.brightness, 62)
  assert.equal(look.kernel, 2)
})

test('props keep only the fields the service accepts, with its defaults', () => {
  const look = toServiceLook({ props: [{ prop: 3, x: 0.2, selected: true }] })
  assert.deepEqual(look.props, [{ prop: 3, x: 0.2, y: 0.5, size: 0.5 }])
})

test('the built-in catalog numbers presets in order', () => {
  const catalog = builtInCatalog()
  assert.equal(catalog.presets.length, PRESET_NAMES.length)
  catalog.presets.forEach((p, i) => assert.equal(p.index, i))
  assert.equal(catalog.filters[0].name, 'None')
})

test('hex colours become 0-1 RGB', () => {
  assert.deepEqual(hexToRgb('#FF0000'), [1, 0, 0])
  assert.deepEqual(hexToRgb('00ff00'), [0, 1, 0])
})

test('preview scale compares the preview with the photo the service keeps', () => {
  assert.equal(previewScale(1280, 1280, 720), 1)
  assert.equal(previewScale(640, 1280, 720), 0.5)
  // a 4K capture is shrunk to 2048 wide by the service
  assert.equal(previewScale(1024, 3840, 2160), 0.5)
})
