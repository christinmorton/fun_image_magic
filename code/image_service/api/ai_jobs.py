# ai_jobs: AI requests take 10-30 seconds, so they run as background jobs. A job turns one
# stored photo into a new stored photo with an AI preset; Laravel either polls the job or
# gets a signed webhook when it finishes. A daily limit caps spending.
import hashlib
import hmac
import json
import secrets
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from core.ai import AI_PRESETS_BY_KEY, AiError, COST_PER_IMAGE_USD, run_ai_preset


@dataclass
class Job:
    job_id: str
    photo_id: str
    preset: str
    callback_url: str | None = None
    status: str = 'queued'               # queued -> running -> done or failed
    result_photo_id: str | None = None   # the new photo (render it like any other)
    person_kept: bool | None = None      # backgrounds: was the original person put back?
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None

    def as_dict(self):
        stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat() if t else None
        return {'job_id': self.job_id, 'photo_id': self.photo_id, 'preset': self.preset,
                'status': self.status, 'result_photo_id': self.result_photo_id,
                'person_kept': self.person_kept, 'error': self.error,
                'created_at': stamp(self.created_at), 'finished_at': stamp(self.finished_at)}


class DailyLimit:
    # counts AI images per UTC day and refuses more than the limit (resets at midnight UTC,
    # and when the service restarts - the provider's own budget alert is the hard cap)
    def __init__(self, limit):
        self.limit, self.day, self.used = limit, None, 0
        self._lock = threading.Lock()

    def try_use(self):
        with self._lock:
            self._roll_over()
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

    def usage(self):
        with self._lock:
            self._roll_over()
            return {'date': self.day, 'used': self.used, 'limit': self.limit,
                    'remaining': max(self.limit - self.used, 0),
                    'estimated_cost_usd': round(self.used * COST_PER_IMAGE_USD, 2)}

    def _roll_over(self):
        today = datetime.now(timezone.utc).date().isoformat()
        if today != self.day:
            self.day, self.used = today, 0


def deliver_webhook(job, token):
    # POST the finished job to Laravel. The body is signed with the shared token, so Laravel
    # can check it came from this service:
    #   X-Image-Service-Signature: sha256=<HMAC-SHA256 of the raw body, keyed with the token>
    body = json.dumps(job.as_dict()).encode('utf-8')
    signature = hmac.new(token.encode('utf-8'), body, hashlib.sha256).hexdigest()
    try:
        httpx.post(job.callback_url, content=body, timeout=10,
                   headers={'Content-Type': 'application/json', 'X-Image-Service-Signature': f'sha256={signature}'})
    except httpx.HTTPError:
        pass        # Laravel can still poll GET /v1/ai/jobs/{id}


class AiJobs:
    def __init__(self, photos, generator, daily_limit, token_source, ttl_seconds, workers=2):
        self.photos = photos                  # api.photos.PhotoStore
        self.generator = generator            # None when no AI key is configured
        self.limit = DailyLimit(daily_limit)
        self.token_source = token_source      # function returning the shared token (for webhooks)
        self.ttl_seconds = ttl_seconds
        self.deliver = deliver_webhook        # replaceable in tests
        self._jobs = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='ai-job')

    def submit(self, photo, preset_key, callback_url=None):
        job = Job(secrets.token_urlsafe(12), photo.photo_id, preset_key, callback_url)
        with self._lock:
            self._purge()
            self._jobs[job.job_id] = job
        self._executor.submit(self._run, job, photo)
        return job

    def get(self, job_id):
        with self._lock:
            self._purge()
            return self._jobs.get(job_id)

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, job, photo):
        job.status = 'running'
        try:
            image, details = run_ai_preset(photo.image, AI_PRESETS_BY_KEY[job.preset], self.generator,
                                           find_person=self.photos.find_person)
            job.result_photo_id = self.photos.add(image).photo_id
            job.person_kept = details['person_kept']
            job.status = 'done'
        except AiError as error:
            job.status, job.error = 'failed', str(error)
        except Exception as error:            # never leave a job "running" forever
            job.status, job.error = 'failed', f'Unexpected error: {type(error).__name__}'
        job.finished_at = time.time()
        if job.callback_url:
            self.deliver(job, self.token_source())

    def _purge(self):
        cutoff = time.time() - self.ttl_seconds
        for job_id in [jid for jid, job in self._jobs.items() if job.created_at < cutoff]:
            del self._jobs[job_id]
