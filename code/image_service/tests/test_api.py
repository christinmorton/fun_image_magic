# Checks for the web API (no server or network needed: FastAPI's TestClient calls the app
# directly). Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import os
import sys
import unittest
from dataclasses import fields
from pathlib import Path

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from fastapi.testclient import TestClient    # noqa: E402

from api.main import app                     # noqa: E402
from core.look import Look                   # noqa: E402

TOKEN = 'test-token-123'
AUTH = {'Authorization': f'Bearer {TOKEN}'}


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        # a known token for the tests, whatever is in the real .env
        self.saved_token = os.environ.get('IMAGE_SERVICE_TOKEN')
        os.environ['IMAGE_SERVICE_TOKEN'] = TOKEN
        self.client = TestClient(app)
        self.client.__enter__()          # runs the start-up step (loads the art)

    def tearDown(self):
        self.client.__exit__(None, None, None)
        if self.saved_token is None:
            os.environ.pop('IMAGE_SERVICE_TOKEN', None)
        else:
            os.environ['IMAGE_SERVICE_TOKEN'] = self.saved_token


class TestHealthAndAuth(ApiTestCase):
    def test_health_needs_no_token(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')

    def test_v1_needs_the_right_token(self):
        self.assertEqual(self.client.get('/v1/catalog').status_code, 401)
        self.assertEqual(self.client.get('/v1/catalog', headers={'Authorization': 'Bearer wrong'}).status_code, 401)
        self.assertEqual(self.client.get('/v1/catalog', headers=AUTH).status_code, 200)

    def test_bearer_typed_twice_still_works(self):
        # pasting "Bearer <token>" into the /docs Authorize box sends "Bearer Bearer <token>"
        response = self.client.get('/v1/catalog', headers={'Authorization': f'Bearer Bearer {TOKEN}'})
        self.assertEqual(response.status_code, 200)
        wrong = self.client.get('/v1/catalog', headers={'Authorization': 'Bearer Bearer nope'})
        self.assertEqual(wrong.status_code, 401)
        self.assertIn('paste only the token', wrong.json()['detail'])

    def test_no_token_configured_refuses_everything(self):
        os.environ['IMAGE_SERVICE_TOKEN'] = ''
        response = self.client.get('/v1/catalog', headers=AUTH)
        self.assertEqual(response.status_code, 503)
        self.assertIn('IMAGE_SERVICE_TOKEN', response.json()['detail'])

    def test_docs_describe_the_token(self):
        schema = self.client.get('/openapi.json').json()
        self.assertIn('/v1/catalog', schema['paths'])
        self.assertIn('HTTPBearer', schema['components']['securitySchemes'])
        self.assertEqual(self.client.get('/docs').status_code, 200)


class TestCatalog(ApiTestCase):
    def test_catalog_lists_everything(self):
        catalog = self.client.get('/v1/catalog', headers=AUTH).json()
        self.assertEqual(len(catalog['presets']), 17)
        self.assertEqual(catalog['presets'][4], {'index': 4, 'name': 'Pop Art', 'thumbnail': None})
        self.assertEqual([item['name'] for item in catalog['layouts']], ['strip', 'grid'])
        self.assertEqual(catalog['focus_modes'][1]['name'], 'Color Pop')
        self.assertEqual(len(catalog['stickers']), 7)
        self.assertEqual(len(catalog['props']), 8)
        self.assertEqual(catalog['backgrounds'][3]['name'], 'go csn')
        self.assertEqual(catalog['off'], -1)
        # look_defaults has every Look setting, so Laravel can start from it
        self.assertEqual(set(catalog['look_defaults']), {f.name for f in fields(Look)})

    def test_thumbnails(self):
        catalog = self.client.get('/v1/catalog', headers=AUTH).json()
        for kind, expect_alpha in [('stickers', True), ('props', True), ('backgrounds', False)]:
            with self.subTest(kind=kind):
                response = self.client.get(catalog[kind][0]['thumbnail'], headers=AUTH)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['content-type'], 'image/png')
                img = cv2.imdecode(np.frombuffer(response.content, np.uint8), cv2.IMREAD_UNCHANGED)
                self.assertLessEqual(max(img.shape[:2]), 200)
                self.assertEqual(img.shape[2] == 4, expect_alpha)   # transparency kept for cut-outs

    def test_thumbnail_errors(self):
        self.assertEqual(self.client.get('/v1/catalog/hats/0/thumbnail.png', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.get('/v1/catalog/props/99/thumbnail.png', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.get('/v1/catalog/props/0/thumbnail.png').status_code, 401)


if __name__ == '__main__':
    unittest.main()
