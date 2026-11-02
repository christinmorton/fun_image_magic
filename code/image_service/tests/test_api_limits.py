# Checks for the request rate limit and "delete everything" (privacy) in the web API.
# Run:  .\.venv\Scripts\python.exe -m unittest discover tests
import unittest

from test_ai import FakeGenerator
from test_api import AUTH
from test_api_photos import PhotoTestCase

from api.limits import RateLimiter            # noqa: E402


class TestRateLimiter(unittest.TestCase):
    def test_counts_per_minute_and_forgets_old_requests(self):
        limiter = RateLimiter(2)
        self.assertEqual(limiter.wait_seconds('app'), 0)
        self.assertEqual(limiter.wait_seconds('app'), 0)
        self.assertGreater(limiter.wait_seconds('app'), 0)           # a third within the minute
        self.assertEqual(limiter.wait_seconds('someone-else'), 0)     # counted per client
        calls = limiter._calls['app']
        for i in range(len(calls)):
            calls[i] -= 61                                            # pretend a minute passed
        self.assertEqual(limiter.wait_seconds('app'), 0)

    def test_zero_means_no_limit(self):
        limiter = RateLimiter(0)
        self.assertTrue(all(limiter.wait_seconds('x') == 0 for _ in range(500)))


class TestApiLimits(PhotoTestCase):
    def test_work_routes_are_rate_limited(self):
        self.client.app.state.limiter.per_minute = 3
        for _ in range(3):
            self.assertEqual(self.upload().status_code, 201)
        refused = self.upload()
        self.assertEqual(refused.status_code, 429)
        self.assertGreater(int(refused.headers['retry-after']), 0)
        self.assertIn('RATE_LIMIT_PER_MINUTE', refused.json()['detail'])
        # cheap reads are never limited
        self.assertEqual(self.client.get('/v1/catalog', headers=AUTH).status_code, 200)

    def test_delete_everything(self):
        self.client.app.state.ai_jobs.generator = FakeGenerator()       # never the real model
        a = self.upload().json()['photo_id']
        b = self.upload().json()['photo_id']
        job_id = self.client.post('/v1/ai/jobs', headers=AUTH, json={'photo_id': a, 'preset': 'comic'}).json()['job_id']
        response = self.client.delete('/v1/photos', headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()['deleted_photos'], 2)
        self.assertEqual(response.json()['deleted_ai_jobs'], 1)
        for photo_id in (a, b):
            self.assertEqual(self.client.get(f'/v1/photos/{photo_id}', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.get(f'/v1/ai/jobs/{job_id}', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.delete('/v1/photos').status_code, 401)            # needs the token


if __name__ == '__main__':
    unittest.main()
