# limits: a simple per-minute request limit for the routes that do real work (uploads,
# renders, layouts, AI jobs), so a runaway loop or a flood of requests can't overload the
# machine. It counts per client address; normally the only client is the Laravel server.
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, per_minute):
        self.per_minute = per_minute           # 0 = no limit
        self._calls = defaultdict(deque)       # client -> times of its recent requests
        self._lock = threading.Lock()

    def wait_seconds(self, client):
        # 0 if the request may go ahead (and it is counted), else how long to wait
        if self.per_minute <= 0:
            return 0
        now = time.monotonic()
        with self._lock:
            calls = self._calls[client]
            while calls and calls[0] <= now - 60:
                calls.popleft()                # forget requests older than a minute
            if len(calls) >= self.per_minute:
                return max(1, int(calls[0] + 60 - now) + 1)
            calls.append(now)
            return 0
