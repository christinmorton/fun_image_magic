# ai_jobs: AI requests take 10-30 seconds, so they run as background jobs. A job turns one
# stored photo into a new stored photo with an AI preset. Laravel can follow its progress by
# polling it, by webhooks (one per stage, signed), or by a live event stream. A daily limit
# caps spending.
#
# The AI provider gives no live progress, so progress comes from stages plus time: while
# the AI is generating, progress moves from 10% towards 90% based on how long similar jobs
# took recently (estimated_seconds), and the page can animate a bar smoothly from that.
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from core.ai import AI_PRESETS_BY_KEY, AiError, COST_PER_IMAGE_USD, run_ai_preset

# progress (%) when each stage starts; "generating" then moves on with time
STAGE_PROGRESS = {'queued': 0, 'preparing': 5, 'generating': 10, 'checking_person': 92,
                  'saving': 96, 'done': 100, 'failed': 100}
STAGE_LABELS = {'queued': 'Waiting to start', 'preparing': 'Preparing the photo',
                'generating': 'The AI is creating the image', 'checking_person': 'Checking the person',
                'saving': 'Saving the result', 'done': 'Done', 'failed': 'Failed'}
DEFAULT_AI_SECONDS = 20.0          # first guess for how long the AI takes, until jobs are timed


@dataclass
class Job:
    job_id: str
    photo_id: str
    preset: str
    callback_url: str | None = None
    status: str = 'queued'               # queued -> running -> done or failed
    stage: str = 'queued'                # see STAGE_PROGRESS
    result_photo_id: str | None = None   # the new photo (render it like any other)
    person_kept: bool | None = None      # backgrounds: was the original person put back?
    error: str | None = None
    expected_seconds: float = DEFAULT_AI_SECONDS   # how long the AI part should take
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None      # when the work began (after waiting in the queue)
    stage_started_at: float | None = None
    finished_at: float | None = None

    def progress(self, now=None):
        # 0-100; while generating, moves from 10 towards 90 as the expected time passes
        if self.stage != 'generating' or self.stage_started_at is None:
            return STAGE_PROGRESS[self.stage]
        elapsed = (now or time.time()) - self.stage_started_at
        return min(90, 10 + int(80 * elapsed / max(self.expected_seconds, 1)))

    def as_dict(self, now=None):
        now = now or time.time()
        stamp = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat() if t else None
        elapsed = ((self.finished_at or now) - self.started_at) if self.started_at else 0.0
        estimated = self.expected_seconds + 2.0          # the AI part plus preparing and saving
        running = self.status in ('queued', 'running')
        return {'job_id': self.job_id, 'photo_id': self.photo_id, 'preset': self.preset,
                'status': self.status, 'stage': self.stage, 'stage_label': STAGE_LABELS[self.stage],
                'progress': self.progress(now),
                'elapsed_seconds': round(elapsed, 1),
                'estimated_seconds': round(estimated, 1),
                'eta_seconds': round(max(estimated - elapsed, 0), 1) if running else 0,
                'result_photo_id': self.result_photo_id, 'person_kept': self.person_kept,
                'error': self.error, 'created_at': stamp(self.created_at),
                'started_at': stamp(self.started_at), 'finished_at': stamp(self.finished_at)}


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


def deliver_webhook(job, token, event):
    # POST the job to Laravel, with "event": "progress" (a new stage), "done" or "failed".
    # The body is signed with the shared token, so Laravel can check it came from this service:
    #   X-Image-Service-Signature: sha256=<HMAC-SHA256 of the raw body, keyed with the token>
    body = json.dumps({'event': event, **job.as_dict()}).encode('utf-8')
    signature = hmac.new(token.encode('utf-8'), body, hashlib.sha256).hexdigest()
    try:
        httpx.post(job.callback_url, content=body, timeout=3 if event == 'progress' else 10,
                   headers={'Content-Type': 'application/json', 'X-Image-Service-Signature': f'sha256={signature}'})
    except httpx.HTTPError:
        pass        # a missed update isn't fatal: Laravel can still poll GET /v1/ai/jobs/{id}


class AiJobs:
    def __init__(self, photos, generator, daily_limit, token_source, ttl_seconds, workers=2):
        self.photos = photos                  # api.photos.PhotoStore
        self.generator = generator            # None when no AI key is configured
        self.limit = DailyLimit(daily_limit)
        self.token_source = token_source      # function returning the shared token (for webhooks)
        self.ttl_seconds = ttl_seconds
        self.deliver = deliver_webhook        # replaceable in tests
        self._durations = deque(maxlen=10)    # how long recent AI calls took (for estimates)
        self._jobs = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='ai-job')

    def expected_ai_seconds(self):
        # the average of recent AI calls (a default until some have been timed)
        return sum(self._durations) / len(self._durations) if self._durations else DEFAULT_AI_SECONDS

    def submit(self, photo, preset_key, callback_url=None):
        job = Job(secrets.token_urlsafe(12), photo.photo_id, preset_key, callback_url,
                  expected_seconds=self.expected_ai_seconds())
        with self._lock:
            self._purge()
            self._jobs[job.job_id] = job
        self._executor.submit(self._run, job, photo)
        return job

    def get(self, job_id):
        with self._lock:
            self._purge()
            return self._jobs.get(job_id)

    def clear(self):
        # forget every job (jobs still running finish, but their results are not kept)
        with self._lock:
            count = len(self._jobs)
            self._jobs.clear()
            return count

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _set_stage(self, job, stage):
        job.stage, job.stage_started_at = stage, time.time()
        if job.callback_url and stage not in ('done', 'failed'):
            self.deliver(job, self.token_source(), 'progress')

    def _run(self, job, photo):
        job.status, job.started_at = 'running', time.time()
        self._set_stage(job, 'preparing')
        ai_started = None

        def on_stage(stage):
            nonlocal ai_started
            if stage == 'generating':
                ai_started = time.time()
            elif ai_started is not None and stage == 'checking_person':
                self._durations.append(time.time() - ai_started)
                ai_started = None
            self._set_stage(job, stage)

        try:
            image, details = run_ai_preset(photo.image, AI_PRESETS_BY_KEY[job.preset], self.generator,
                                           find_person=self.photos.find_person, on_stage=on_stage)
            if ai_started is not None:                  # styles have no "checking_person" stage
                self._durations.append(time.time() - ai_started)
            self._set_stage(job, 'saving')
            job.result_photo_id = self.photos.add(image).photo_id
            job.person_kept = details['person_kept']
            job.status = 'done'
        except AiError as error:
            job.status, job.error = 'failed', str(error)
        except Exception as error:            # never leave a job "running" forever
            job.status, job.error = 'failed', f'Unexpected error: {type(error).__name__}'
        job.finished_at = time.time()
        job.stage = job.status
        if job.callback_url:
            self.deliver(job, self.token_source(), job.status)

    def _purge(self):
        cutoff = time.time() - self.ttl_seconds
        for job_id in [jid for jid, job in self._jobs.items() if job.created_at < cutoff]:
            del self._jobs[job_id]
