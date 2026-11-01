# Checks for AI jobs in the web API. Every test swaps in a fake generator first, so nothing
# here calls Google or costs money (even if GEMINI_API_KEY is in .env).
# Run:  .\.venv\Scripts\python.exe -m unittest discover tests
import hashlib
import hmac
import json
import time
import unittest
from unittest import mock

from test_ai import FakeGenerator               # a fake model: returns a solid image
from test_api import AUTH, TOKEN
from test_api_photos import PhotoTestCase

import api.ai_jobs                              # noqa: E402  (for patching httpx in the webhook)
from core.ai import AiError                     # noqa: E402


class FailingGenerator:
    def generate(self, prompt, images, aspect_ratio):
        raise AiError('ResourceExhausted: quota exceeded')


class AiTestCase(PhotoTestCase):
    def setUp(self):
        super().setUp()
        self.jobs = self.client.app.state.ai_jobs
        self.generator = FakeGenerator()
        self.jobs.generator = self.generator    # never the real model in tests

    def start(self, photo_id, preset='comic', **extra):
        return self.client.post('/v1/ai/jobs', headers=AUTH, json={'photo_id': photo_id, 'preset': preset, **extra})

    def wait_for(self, job_id, timeout=15):
        # poll the job like Laravel would, until it finishes
        end = time.time() + timeout
        while time.time() < end:
            job = self.client.get(f'/v1/ai/jobs/{job_id}', headers=AUTH).json()
            if job['status'] in ('done', 'failed'):
                return job
            time.sleep(0.05)
        self.fail(f'job {job_id} did not finish')


class TestAiJobs(AiTestCase):
    def test_a_style_job_makes_a_new_photo(self):
        photo_id = self.upload().json()['photo_id']
        response = self.start(photo_id, 'comic')
        self.assertEqual(response.status_code, 202)
        self.assertIn(response.json()['status'], ('queued', 'running', 'done'))
        job = self.wait_for(response.json()['job_id'])
        self.assertEqual(job['status'], 'done', job)
        result = self.client.get(f"/v1/photos/{job['result_photo_id']}", headers=AUTH).json()
        self.assertEqual((result['width'], result['height']), (640, 480))     # same size as the photo
        render = self.client.post('/v1/render', headers=AUTH, json={'photo_id': job['result_photo_id'],
                                                                     'look': {'frame': 0}})
        self.assertEqual(render.status_code, 200)                             # frames go on afterwards
        self.assertEqual(self.generator.calls[0][1:], (1, '4:3'))

    def test_a_background_job_without_a_person(self):
        photo_id = self.upload().json()['photo_id']
        job = self.wait_for(self.start(photo_id, 'vegas_strip').json()['job_id'])
        self.assertEqual(job['status'], 'done')
        self.assertFalse(job['person_kept'])                                  # nobody to put back

    def test_a_failed_job_says_why(self):
        self.jobs.generator = FailingGenerator()
        photo_id = self.upload().json()['photo_id']
        job = self.wait_for(self.start(photo_id).json()['job_id'])
        self.assertEqual(job['status'], 'failed')
        self.assertIn('quota exceeded', job['error'])

    def test_request_errors(self):
        photo_id = self.upload().json()['photo_id']
        self.assertEqual(self.start(photo_id, 'not_a_preset').status_code, 422)
        self.assertEqual(self.start('no-such-photo').status_code, 404)
        self.assertEqual(self.client.get('/v1/ai/jobs/nope', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.post('/v1/ai/jobs', json={'photo_id': photo_id, 'preset': 'comic'}).status_code, 401)
        self.jobs.generator = None
        response = self.start(photo_id)
        self.assertEqual(response.status_code, 503)
        self.assertIn('GEMINI_API_KEY', response.json()['detail'])

    def test_daily_limit_and_usage(self):
        self.jobs.limit.limit = 1
        photo_id = self.upload().json()['photo_id']
        self.assertEqual(self.start(photo_id).status_code, 202)
        refused = self.start(photo_id)
        self.assertEqual(refused.status_code, 429)
        self.assertIn('daily AI limit', refused.json()['detail'])
        usage = self.client.get('/v1/ai/usage', headers=AUTH).json()
        self.assertEqual((usage['used'], usage['limit'], usage['remaining']), (1, 1, 0))
        self.assertGreater(usage['estimated_cost_usd'], 0)

    def test_catalog_lists_ai_presets(self):
        presets = self.client.get('/v1/catalog', headers=AUTH).json()['ai_presets']
        self.assertEqual(len(presets), 9)
        self.assertIn({'key': 'vegas_strip', 'name': 'Las Vegas Strip at night', 'kind': 'background'}, presets)


class SlowGenerator(FakeGenerator):
    # like the real model, takes a moment, so the "generating" stage can be seen
    def __init__(self, seconds=0.6):
        super().__init__()
        self.seconds = seconds

    def generate(self, prompt, images, aspect_ratio):
        time.sleep(self.seconds)
        return super().generate(prompt, images, aspect_ratio)


class TestWebhook(AiTestCase):
    def test_every_stage_and_the_end_are_posted_to_the_callback(self):
        delivered = []
        self.jobs.deliver = lambda job, token, event: delivered.append((event, job.as_dict(), token))
        photo_id = self.upload().json()['photo_id']
        job_id = self.start(photo_id, callback_url='https://laravel.example/ai-done').json()['job_id']
        self.wait_for(job_id)
        for _ in range(100):                                                   # the last one comes just after
            if delivered and delivered[-1][0] == 'done':
                break
            time.sleep(0.05)
        events = [(event, body['stage']) for event, body, _ in delivered]
        self.assertEqual(events, [('progress', 'preparing'), ('progress', 'generating'),
                                  ('progress', 'saving'), ('done', 'done')])
        self.assertTrue(all(body['job_id'] == job_id and token == TOKEN for _, body, token in delivered))
        self.assertEqual(delivered[-1][1]['progress'], 100)
        self.assertEqual(self.start(photo_id, callback_url='not a url').status_code, 422)

    def test_webhook_is_signed_with_the_token(self):
        job = api.ai_jobs.Job('job1', 'photo1', 'comic', 'https://laravel.example/ai-done', status='done', stage='done')
        with mock.patch.object(api.ai_jobs.httpx, 'post') as post:
            api.ai_jobs.deliver_webhook(job, 'secret-token', 'done')
        body, headers = post.call_args.kwargs['content'], post.call_args.kwargs['headers']
        expected = hmac.new(b'secret-token', body, hashlib.sha256).hexdigest()
        self.assertEqual(headers['X-Image-Service-Signature'], f'sha256={expected}')     # how Laravel checks it
        self.assertEqual((json.loads(body)['event'], json.loads(body)['status']), ('done', 'done'))


class TestProgress(AiTestCase):
    def test_progress_moves_with_time_while_generating(self):
        job = api.ai_jobs.Job('j', 'p', 'comic', expected_seconds=20, stage='generating', started_at=100.0,
                              stage_started_at=100.0, status='running')
        self.assertEqual(job.progress(now=100.0), 10)
        self.assertEqual(job.progress(now=110.0), 50)                      # half the expected time
        self.assertEqual(job.progress(now=500.0), 90)                      # never claims 100 early
        info = job.as_dict(now=110.0)
        self.assertEqual((info['elapsed_seconds'], info['estimated_seconds'], info['eta_seconds']), (10.0, 22.0, 12.0))
        self.assertEqual(info['stage_label'], 'The AI is creating the image')

    def test_polling_shows_the_generating_stage_and_learns_how_long_it_takes(self):
        self.jobs.generator = SlowGenerator(0.6)
        photo_id = self.upload().json()['photo_id']
        job_id = self.start(photo_id).json()['job_id']
        seen = set()
        for _ in range(200):
            job = self.client.get(f'/v1/ai/jobs/{job_id}', headers=AUTH).json()
            seen.add(job['stage'])
            if job['status'] == 'done':
                break
            time.sleep(0.02)
        self.assertIn('generating', seen)
        self.assertEqual((job['progress'], job['eta_seconds']), (100, 0))
        self.assertGreater(job['elapsed_seconds'], 0.5)
        self.assertAlmostEqual(self.jobs.expected_ai_seconds(), 0.6, delta=0.3)   # learned from this job

    def test_event_stream_follows_the_job_to_the_end(self):
        self.jobs.generator = SlowGenerator(1.5)
        photo_id = self.upload().json()['photo_id']
        job_id = self.start(photo_id).json()['job_id']
        events = []
        with self.client.stream('GET', f'/v1/ai/jobs/{job_id}/events', headers=AUTH) as response:
            self.assertEqual(response.headers['content-type'].split(';')[0], 'text/event-stream')
            event = None
            for line in response.iter_lines():
                if line.startswith('event: '):
                    event = line[len('event: '):]
                elif line.startswith('data: '):
                    events.append((event, json.loads(line[len('data: '):])))
        self.assertEqual(events[-1][0], 'done')
        self.assertEqual(events[-1][1]['progress'], 100)
        self.assertTrue(any(name == 'progress' for name, _ in events[:-1]))
        self.assertEqual(self.client.get('/v1/ai/jobs/nope/events', headers=AUTH).status_code, 404)

    def test_every_response_says_how_long_it_took(self):
        photo_id = self.upload().json()['photo_id']
        response = self.client.post('/v1/render', headers=AUTH, json={'photo_id': photo_id, 'look': {'preset': 3}})
        self.assertGreater(float(response.headers['x-processing-time-ms']), 0)
        self.assertTrue(response.headers['server-timing'].startswith('app;dur='))
        self.assertIn('x-processing-time-ms', self.client.get('/health').headers)


if __name__ == '__main__':
    unittest.main()
