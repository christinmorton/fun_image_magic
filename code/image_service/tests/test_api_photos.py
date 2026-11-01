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


class TestRender(PhotoTestCase):
    def render(self, photo_id, look=None, **options):
        return self.client.post('/v1/render', headers=AUTH, json={'photo_id': photo_id, 'look': look or {}, **options})

    def test_default_look_returns_the_photo_unchanged(self):
        img = gradient_photo()
        response = self.render(self.upload(img).json()['photo_id'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['content-type'], 'image/png')
        self.assertTrue(np.array_equal(decode(response), img))          # PNG is lossless

    def test_a_full_look(self):
        img = gradient_photo()
        photo_id = self.upload(img).json()['photo_id']
        look = {'preset': 4, 'contrast': 1.2, 'kernel': 1, 'frame': 0, 'mascot': 1, 'background': 2,
                'focus': 1, 'sticker': 0, 'props': [{'prop': 0, 'x': 0.8, 'y': 0.6, 'size': 0.4}]}
        out = decode(self.render(photo_id, look))
        self.assertEqual(out.shape, img.shape)
        self.assertFalse(np.array_equal(out, img))

    def test_jpeg_and_max_width(self):
        photo_id = self.upload().json()['photo_id']
        response = self.render(photo_id, format='jpeg', quality=80, max_width=320)
        self.assertEqual(response.headers['content-type'], 'image/jpeg')
        self.assertEqual(decode(response).shape[:2], (240, 320))

    def test_bad_looks_are_refused_with_a_reason(self):
        photo_id = self.upload().json()['photo_id']
        for look, expected_text in [({'preset': 99}, 'preset'), ({'sticker': 50}, 'only 7'),
                                    ({'props': [{'prop': 0, 'x': 2}]}, 'x'), ({'presett': 1}, 'presett'),
                                    ({'props': [{'prop': 42}]}, 'props[0]')]:
            with self.subTest(look=look):
                response = self.render(photo_id, look)
                self.assertEqual(response.status_code, 422)
                self.assertIn(expected_text, response.text)

    def test_unknown_photo(self):
        self.assertEqual(self.render('no-such-photo').status_code, 404)


class TestCompose(PhotoTestCase):
    def compose(self, slots, layout='grid', **options):
        return self.client.post('/v1/compose', headers=AUTH, json={'layout': layout, 'slots': slots, **options})

    def test_grid_of_photos_with_their_own_looks(self):
        a = self.upload(gradient_photo()).json()['photo_id']
        b = self.upload(gradient_photo(960, 640)).json()['photo_id']    # a different size is fitted in
        response = self.compose([{'photo_id': a, 'look': {'preset': 6}}, {'photo_id': b, 'look': {'frame': 2}}])
        self.assertEqual(response.status_code, 200)
        cell_w, cell_h = 640 + 24, 480 + 24                                # each photo gets a 12 px border
        self.assertEqual(decode(response).shape[:2], (2 * cell_h, 2 * cell_w))

    def test_strip_leaves_out_empty_slots(self):
        a = self.upload().json()['photo_id']
        response = self.compose([{'photo_id': a}, {'photo_id': None}, {'photo_id': a, 'look': {'preset': 2}}],
                                layout='strip')
        self.assertEqual(decode(response).shape[:2], (2 * (480 + 24), 640 + 24))

    def test_compose_errors(self):
        a = self.upload().json()['photo_id']
        self.assertEqual(self.compose([{'photo_id': None}]).status_code, 422)            # nothing to compose
        self.assertEqual(self.compose([{'photo_id': a}] * 5).status_code, 422)           # more than 4 slots
        self.assertEqual(self.compose([{'photo_id': 'gone'}]).status_code, 404)
        bad = self.compose([{'photo_id': a}, {'photo_id': a, 'look': {'frame': 30}}])
        self.assertEqual(bad.status_code, 422)
        self.assertIn('slots[1]', bad.json()['detail'])


if __name__ == '__main__':
    unittest.main()
