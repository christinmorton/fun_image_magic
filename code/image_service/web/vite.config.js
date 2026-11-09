// vite.config.js: the pages, a proxy to the image service, and the MediaPipe files.
//   npm run dev        -> http://localhost:5173 (the service must be running on port 8000)
// The browser calls /image-service/...; the dev server forwards it to the service and adds
// the token from image_service/.env. The token never reaches the browser or the bundle.
// A real app does the same from its own server: forward the request and add the token.
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'

const WEB_DIR = path.dirname(fileURLToPath(import.meta.url))
const SERVICE_DIR = path.resolve(WEB_DIR, '..')
export const SERVICE_PREFIX = '/image-service'

// URL folder -> folder on disk, for the files MediaPipe loads at run time. The models are
// the ones core/ uses, so there's one copy; only the files listed are put in a build.
const MEDIAPIPE_FILES = {
  '/mediapipe/models/': {
    dir: path.join(SERVICE_DIR, 'core', 'models'),
    files: ['face_landmarker.task', 'selfie_segmenter.tflite'],
  },
  '/mediapipe/wasm/': {
    dir: path.join(WEB_DIR, 'node_modules', '@mediapipe', 'tasks-vision', 'wasm'),
    files: ['vision_wasm_internal.js', 'vision_wasm_internal.wasm'],
  },
}
const CONTENT_TYPES = { '.js': 'text/javascript', '.wasm': 'application/wasm' }

function mediapipeFiles() {
  // serves the files above in development and preview, and copies them into a build
  function middleware(req, res, next) {
    const url = decodeURIComponent((req.url || '').split('?')[0])
    for (const [prefix, { dir, files }] of Object.entries(MEDIAPIPE_FILES)) {
      const name = url.startsWith(prefix) ? url.slice(prefix.length) : null
      if (name && files.includes(name)) {
        res.setHeader('Content-Type', CONTENT_TYPES[path.extname(name)] || 'application/octet-stream')
        fs.createReadStream(path.join(dir, name)).pipe(res)
        return
      }
    }
    next()
  }
  return {
    name: 'mediapipe-files',
    configureServer(server) { server.middlewares.use(middleware) },
    configurePreviewServer(server) { server.middlewares.use(middleware) },
    generateBundle() {
      for (const [prefix, { dir, files }] of Object.entries(MEDIAPIPE_FILES)) {
        for (const name of files) {
          this.emitFile({ type: 'asset', fileName: prefix.slice(1) + name, source: fs.readFileSync(path.join(dir, name)) })
        }
      }
    },
  }
}

export default defineConfig(({ mode }) => {
  // every key in image_service/.env (not only VITE_ ones), for this file only: nothing here
  // is passed to the page
  const env = loadEnv(mode, SERVICE_DIR, '')
  const target = env.IMAGE_SERVICE_URL || 'http://127.0.0.1:8000'
  const token = env.IMAGE_SERVICE_TOKEN || ''
  if (!token) {
    console.warn('IMAGE_SERVICE_TOKEN is not set in image_service/.env: the live camera works, but renders will fail')
  }
  const proxy = {
    [SERVICE_PREFIX]: {
      target,
      changeOrigin: true,
      rewrite: (url) => url.slice(SERVICE_PREFIX.length) || '/',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    },
  }
  return {
    root: WEB_DIR,
    plugins: [mediapipeFiles()],
    server: { proxy },
    preview: { proxy },
    build: {
      rollupOptions: {
        input: {
          index: path.join(WEB_DIR, 'index.html'),
          vanilla: path.join(WEB_DIR, 'vanilla', 'index.html'),
        },
      },
    },
  }
})
