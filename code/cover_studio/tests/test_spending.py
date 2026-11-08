# Checks for the spending log and daily limit (nothing is paid for).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import tempfile
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.spending import PRICES, OverLimit, Spending     # noqa: E402


class TestSpending(unittest.TestCase):
    def test_log_limit_and_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            day = {'date': '2026-11-08'}
            spending = Spending(Path(tmp) / 'spending.json', limit=0.20, today=lambda: day['date'])
            self.assertEqual(spending.spent_today(), 0)
            self.assertEqual(spending.record(3, '1K', 'previews'), round(3 * PRICES['1K'], 4))
            spending.check(0.06)                                        # still fits
            with self.assertRaises(OverLimit):
                spending.check(0.10)
            day['date'] = '2026-11-09'                                  # a new day starts fresh
            self.assertEqual(spending.spent_today(), 0)
            spending.check(0.20)
            self.assertEqual(len(spending.entries()), 1)                # the log keeps every day

    def test_nothing_logged_for_no_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            spending = Spending(Path(tmp) / 'spending.json', limit=1)
            self.assertEqual(spending.record(0, '1K', 'all failed'), 0)
            self.assertFalse((Path(tmp) / 'spending.json').exists())


if __name__ == '__main__':
    unittest.main()
