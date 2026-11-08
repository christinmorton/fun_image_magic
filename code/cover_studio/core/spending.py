# spending: a log of every paid AI image (spending.json, kept on this machine and never
# committed) and a daily limit, so a slip can't run up a bill. The budget alert on the
# Google account is still the hard cap.
import json
import os
from datetime import datetime

from . import CORE_DIR

SPENDING_FILE = CORE_DIR.parent / 'spending.json'
DEFAULT_DAILY_LIMIT = 2.00          # US dollars per day; COVER_STUDIO_DAILY_LIMIT_USD in .env changes it
# about what one image really costs: the list price (docs/ai-api-pricing.md) plus the
# photos sent with it. Google billed about 0.045 per 1K image in practice
PRICES = {'1K': 0.045, '2K': 0.062, '4K': 0.125}


class OverLimit(Exception):
    """A paid request would go over today's spending limit (the message says by how much)."""


def daily_limit():
    try:
        return max(0.0, float(os.environ.get('COVER_STUDIO_DAILY_LIMIT_USD', DEFAULT_DAILY_LIMIT)))
    except ValueError:
        return DEFAULT_DAILY_LIMIT


class Spending:
    def __init__(self, path=SPENDING_FILE, limit=None, today=None):
        self.path = path
        self.limit = daily_limit() if limit is None else limit
        self.today = today or (lambda: datetime.now().date().isoformat())   # local date; replaced in tests

    def entries(self):
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding='utf-8'))

    def spent_today(self):
        today = self.today()
        return round(sum(e['cost'] for e in self.entries() if e['date'] == today), 4)

    def check(self, cost):
        # raises OverLimit if spending `cost` now would go over today's limit
        spent = self.spent_today()
        if spent + cost > self.limit + 1e-9:
            raise OverLimit(f'That would cost about ${cost:.2f}, but ${spent:.2f} of today\'s ${self.limit:.2f} '
                            'limit is already spent (COVER_STUDIO_DAILY_LIMIT_USD in .env).')

    def record(self, images, size, what):
        # log `images` paid images of `size` ('1K', '2K' or '4K'); returns their cost
        cost = round(images * PRICES[size], 4)
        if images:
            log = self.entries() + [{'time': datetime.now().isoformat(timespec='seconds'), 'date': self.today(),
                                     'images': images, 'size': size, 'cost': cost, 'what': what}]
            self.path.write_text(json.dumps(log, indent=2), encoding='utf-8')
        return cost
