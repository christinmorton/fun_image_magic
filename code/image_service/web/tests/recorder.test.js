// run with: npm test (MediaRecorder itself needs a browser; these check the rules around it)
import assert from 'node:assert/strict'
import { test } from 'node:test'

import { MAX_RECORDING_SECONDS, fileExtension, formatDuration, pickVideoType, timeLimit } from '../src/engine/recorder.js'

test('the longest time limit is five minutes', () => {
  assert.equal(MAX_RECORDING_SECONDS, 300)
  assert.equal(timeLimit(301), 300)
  assert.equal(timeLimit(3600), 300)
})

test('time limits are whole seconds, and nothing or zero means no limit', () => {
  assert.equal(timeLimit(30), 30)
  assert.equal(timeLimit('15'), 15)
  assert.equal(timeLimit(9.6), 10)
  for (const none of [null, undefined, '', 0, -5, 'soon']) assert.equal(timeLimit(none), null, String(none))
})

test('MP4 is chosen when the browser can record it', () => {
  assert.equal(pickVideoType(() => true), 'video/mp4;codecs=avc1,mp4a.40.2')
  assert.equal(pickVideoType((type) => type.startsWith('video/webm')), 'video/webm;codecs=vp9,opus')
  assert.equal(pickVideoType(() => false), '')
})

test('the file extension follows the format', () => {
  assert.equal(fileExtension('video/mp4;codecs=avc1'), 'mp4')
  assert.equal(fileExtension('video/webm;codecs=vp9,opus'), 'webm')
})

test('durations read as minutes and seconds', () => {
  assert.equal(formatDuration(0), '0:00')
  assert.equal(formatDuration(9.9), '0:09')
  assert.equal(formatDuration(75.4), '1:15')
  assert.equal(formatDuration(300), '5:00')
})
