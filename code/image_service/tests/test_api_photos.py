# Checks for photo upload, rendering and layouts in the web API (no server needed).
# Run from the image_service folder:  .\.venv\Scripts\python.exe -m unittest discover tests
import time
import unittest

import cv2
import numpy as np

from test_api import AUTH, ApiTestCase     # the shared token / client setup


def gradient_photo(w=640, h=480):
    # a colourful test photo (no faces or people in it)
    x = np.linspace(0, 255, w, dtype=np.uint8)[None, :]
    y = np.linspace(0, 255, h, dtype=np.uint8)[:, None]
    return cv2.merge([np.repeat(x, h, 0), np.repeat(y, w, 1), np.full((h, w), 128, np.uint8)])

def png_bytes(img):
    ok, png = cv2.imencode('.png', img)
    return png.tobytes()

def decode(response):
    return cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR)


class PhotoTestCase(ApiTestCase):
    def upload(self, img=None, name='photo.png'):
        img = gradient_photo() if img is None else img
        return self.client.post('/v1/photos', headers=AUTH, files={'image': (name, png_bytes(img), 'image/png')})


class TestPhotos(PhotoTestCase):
    def test_upload_get_and_delete(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        info = response.json()
        self.assertEqual((info['width'], info['height'], info['faces']), (640, 480, 0))
        self.assertIn('person_found', info)
        photo_id = info['photo_id']
        self.assertEqual(self.client.get(f'/v1/photos/{photo_id}', headers=AUTH).json(), info)
        self.assertEqual(self.client.delete(f'/v1/photos/{photo_id}', headers=AUTH).status_code, 204)
        self.assertEqual(self.client.get(f'/v1/photos/{photo_id}', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.delete(f'/v1/photos/{photo_id}', headers=AUTH).status_code, 404)

    def test_big_photos_are_shrunk(self):
        info = self.upload(gradient_photo(3000, 2000)).json()
        self.assertEqual((info['width'], info['height']), (2048, 1365))

    def test_bad_uploads(self):
        not_image = self.client.post('/v1/photos', headers=AUTH, files={'image': ('x.png', b'hello', 'image/png')})
        self.assertEqual(not_image.status_code, 400)
        too_big = self.client.post('/v1/photos', headers=AUTH,
                                   files={'image': ('big.png', b'0' * (15 * 1024 * 1024 + 1), 'image/png')})
        self.assertEqual(too_big.status_code, 413)
        no_token = self.client.post('/v1/photos', files={'image': ('p.png', png_bytes(gradient_photo()), 'image/png')})
        self.assertEqual(no_token.status_code, 401)

    def test_photos_expire(self):
        photo_id = self.upload().json()['photo_id']
        self.client.app.state.photos._photos[photo_id].expires_at = time.time() - 1   # pretend time passed
        response = self.client.get(f'/v1/photos/{photo_id}', headers=AUTH)
        self.assertEqual(response.status_code, 404)
        self.assertIn('expired', response.json()['detail'])


if __name__ == '__main__':
    unittest.main()
