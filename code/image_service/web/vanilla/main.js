// the vanilla page: one call mounts the booth. On another site, copy this call into its page
// and point serviceUrl at the route on its own server that forwards to the image service.
import { mountBooth } from './booth-ui.js'

mountBooth(document.querySelector('#booth'), {
  serviceUrl: '/image-service',
  onCapture: ({ photoId, look }) => console.info('Captured', { photoId, look }),
})
