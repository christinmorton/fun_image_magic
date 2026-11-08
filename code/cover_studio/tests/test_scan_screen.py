# Checks for drawing the scan screen, with made-up faces (no webcam or windows needed).
# Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import sys
import unittest
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core.scan import Scanner                                                     # noqa: E402
from desktop.scan import BAR_H, STRIP_H, draw_scan                                # noqa: E402
from test_scan import H, W, FakeClock, FakeDetect, busy_frame, capture, face      # noqa: E402


class TestScanScreen(unittest.TestCase):
    def test_draw_while_scanning_and_when_done(self):
        clock, detect = FakeClock(), FakeDetect(face(0))
        scanner = Scanner(detect, clock)
        screen = draw_scan(busy_frame(), scanner)
        self.assertEqual(screen.shape, (BAR_H + H + STRIP_H, W, 3))
        for turn in (0, -35, 35):
            detect.faces = [face(turn)]
            capture(scanner, clock, busy_frame())
        self.assertTrue(scanner.done)
        self.assertEqual(draw_scan(busy_frame(), scanner, flash=True).shape, screen.shape)


if __name__ == '__main__':
    unittest.main()
