// art: where face stickers, the mascot and frames go on the picture, worked out the way
// core/overlays.py does. Positions are pixels from the top left of the preview; a quad is
// four corners in order: top left, top right, bottom right, bottom left.

// MediaPipe's outer eye corners. It numbers them by where they appear, so 33 is always the
// one on the left of the picture it was given.
const EYE_LEFT = 33
const EYE_RIGHT = 263

const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]

export function stickerQuad(face, { width, height, mirror = true, widthFactor, liftFactor, aspect, minWidth = 10 }) {
  // a face sticker's corners (add_face_sticker): as wide as the eye distance times
  // widthFactor, tilted with the eyes, and lifted liftFactor eye distances above them.
  // aspect is the sticker's height / width. null when it would be under minWidth pixels.
  const point = (p) => [(mirror ? 1 - p.x : p.x) * width, p.y * height]
  // the tracker saw the unmirrored camera, so in the mirrored preview its left eye corner
  // is on the right; swap them back, as MediaPipe would number the mirrored picture
  const [lx, ly] = point(face[mirror ? EYE_RIGHT : EYE_LEFT])
  const [rx, ry] = point(face[mirror ? EYE_LEFT : EYE_RIGHT])
  const eyeDistance = Math.hypot(rx - lx, ry - ly)
  const angle = Math.atan2(ry - ly, rx - lx)
  const w = eyeDistance * widthFactor
  const h = w * aspect
  if (w < minWidth) return null
  const cx = (lx + rx) / 2 + Math.sin(angle) * liftFactor * eyeDistance
  const cy = (ly + ry) / 2 - Math.cos(angle) * liftFactor * eyeDistance
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  return rect(-w / 2, -h / 2, w, h).map(([x, y]) => [cx + x * cos - y * sin, cy + x * sin + y * cos])
}

export function mascotQuad({ width, height, imageWidth, imageHeight }) {
  // the mascot in the bottom-right corner, flush with the edges, up to 3/4 of the height
  // and 45% of the width (add_mascot)
  const scale = Math.min(height * 0.75 / imageHeight, width * 0.45 / imageWidth)
  const w = Math.floor(imageWidth * scale)
  const h = Math.floor(imageHeight * scale)
  return rect(width - w, height - h, w, h)
}

export function fullQuad({ width, height }) {
  // the whole picture (a frame the service has already fitted to this size)
  return rect(0, 0, width, height)
}
