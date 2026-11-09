# Web Webcam

The booth's live camera in the browser: the webcam, live effects on the GPU and face
tracking from frame to frame, with the image service doing the exact final render. It exists
because the service has no camera and sees only single stills (see
`docs/desktop-to-api-lessons.md`). The plan is `docs/web-webcam-plan.md`.

## Run it

You need Node 20 or newer and the image service running.

```powershell
# from code/image_service/: the service (it needs IMAGE_SERVICE_TOKEN in .env)
.\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000

# from code/image_service/web/, in a second window
npm install          # the first time
npm run dev          # then open http://localhost:5173/vanilla/
```

Without the service the page still works, with the live preview only.

| Command | What it does |
| --- | --- |
| `npm run dev` | The dev server, with the proxy to the service |
| `npm test` | The engine tests (no browser or camera needed) |
| `npm run build` | A production build in `dist/`, including the MediaPipe files |

`tests/test_web.py` (in the Python suite) checks that the presets, filters, look defaults
and brand colours here still match `core/`.

## The keys

| Key | Does |
| --- | --- |
| Space | Capture (after the timer) |
| `[` `]` | The previous and next preset |

## How it fits together

```
browser                                       your server              image service
───────                                       ───────────              ─────────────
camera → live effects (WebGL) → preview
       → face tracking (MediaPipe, video mode)
capture → unedited photo + look  ──POST──►   /image-service/*  ──►    /v1/photos, /v1/render
                                              adds the token
```

- **`src/engine/`**: the camera, effects, tracker and service client, with no buttons or
  layout. `WebcamBooth` (in `booth.js`) runs the live loop. Every front end uses it.
- **`vanilla/`**: the booth in plain HTML, CSS and JavaScript. `mountBooth(element, options)`
  in `booth-ui.js` puts the whole booth into any element.
- **React and Vue** versions come later, over the same engine.

The live preview is close to the service's render but not identical. A few presets use
shortcuts a shader can do in one pass. Night Vision and X-Ray are the furthest off, because
OpenCV evens out each picture's histogram. The finished picture always comes from the
service.

## Putting it in another app

1. **Forward a route to the service.** The page calls paths like
   `/image-service/v1/render`. Your server forwards each one to the service at the same
   path without the prefix, adding `Authorization: Bearer <IMAGE_SERVICE_TOKEN>`. It passes
   the body, the `Content-Type` and the reply back unchanged. The event stream for AI jobs
   (`/v1/ai/jobs/{id}/events`) must not be buffered. **Never send the token to the
   browser.** `vite.config.js` shows the same proxy for development.
2. **Serve the MediaPipe files.** `/mediapipe/models/` serves `face_landmarker.task` (from
   `core/models/`), and `/mediapipe/wasm/` serves `vision_wasm_internal.js` and `.wasm` (from
   `node_modules/@mediapipe/tasks-vision/wasm/`). `npm run build` copies them into `dist/`.
   Other paths can be passed as `mediapipe: { wasmBaseUrl, faceModelUrl }`.
3. **Mount the booth:**

   ```js
   import { mountBooth } from './vanilla/booth-ui.js'
   mountBooth(document.querySelector('#booth'), {
     serviceUrl: '/image-service',
     onCapture: ({ blob, look, photoId }) => { /* keep it in your app */ },
   })
   ```

   If the page sends a CSRF token or session header to your server, use the engine's
   `ImageServiceClient({ baseUrl, headers })` directly.

The camera needs `https`, or `localhost` during development.

**Rate limit:** the service counts requests per client IP. When your server forwards for
every user, they all share one IP, so `RATE_LIMIT_PER_MINUTE` in the service `.env` applies
to all of them together.
