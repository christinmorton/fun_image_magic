# Checks for the guided face scan, with made-up faces (no webcam, windows or real photos
# needed). Run from the cover_studio folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

SERVICE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVICE_DIR))

from core import MODELS_DIR                                                         # noqa: E402
from core.scan import (CHIN, FOREHEAD, HOLD_SECONDS, NOSE, PAUSE_SECONDS, SIDE_A,   # noqa: E402
                       SIDE_B, Face, FaceDetector, Scanner, check_shot, head_level, head_turn, sort_photos)

W, H = 640, 480


def face(turn=0.0, level=0.55, box=(0.38, 0.2, 0.62, 0.75), blink=0.0):
    # a made-up face: 478 points inside `box` (fractions of the picture), with the nose
    # placed for a head turned `turn` degrees and `level` of the way down the face
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    points = [SimpleNamespace(x=cx, y=cy) for _ in range(478)]
    points[0], points[2] = SimpleNamespace(x=x0, y=y0), SimpleNamespace(x=x1, y=y1)
    points[SIDE_A], points[SIDE_B] = SimpleNamespace(x=x0, y=cy), SimpleNamespace(x=x1, y=cy)
    points[FOREHEAD], points[CHIN] = SimpleNamespace(x=cx, y=y0), SimpleNamespace(x=cx, y=y1)
    points[NOSE] = SimpleNamespace(x=cx + math.sin(math.radians(turn)) * (x1 - x0) / 2, y=y0 + level * (y1 - y0))
    return Face(points, {'eyeBlinkLeft': blink, 'eyeBlinkRight': blink})

def busy_frame(seed=0):
    # a detailed, mid-bright picture (sharp, well lit), different on its left and right
    frame = np.random.default_rng(seed).integers(60, 200, (H, W, 3)).astype(np.uint8)
    frame[:, :40] = 0
    return frame


class FakeDetect:
    # returns whatever faces it was last given
    def __init__(self, *faces):
        self.faces = list(faces)

    def __call__(self, frame):
        return self.faces


class FakeClock:
    # time that only moves when a test moves it
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def hold(scanner, clock, frame, seconds=HOLD_SECONDS, step=0.1):
    # feed frames for a little over `seconds` (a frame every `step`), like holding a pose
    # (one extra frame, as adding 0.1 ten times comes to just under 1)
    for _ in range(int(round(seconds / step)) + 2):
        scanner.feed(frame)
        clock.now += step

def capture(scanner, clock, frame):
    # hold long enough for a capture, then wait out the pause after it
    hold(scanner, clock, frame)
    clock.now += PAUSE_SECONDS


class TestHeadPose(unittest.TestCase):
    def test_turn_and_level(self):
        self.assertAlmostEqual(head_turn(face(0).landmarks), 0, delta=0.5)
        self.assertAlmostEqual(head_turn(face(30).landmarks), 30, delta=1)
        self.assertAlmostEqual(head_turn(face(-30).landmarks), -30, delta=1)
        self.assertAlmostEqual(head_level(face(level=0.6).landmarks), 0.6, delta=0.01)


class TestShotChecks(unittest.TestCase):
    def test_a_good_shot(self):
        shot = check_shot(busy_frame(), [face()])
        self.assertEqual(shot.problems, [])
        self.assertTrue(shot.found)

    def test_each_problem(self):
        frame = busy_frame()
        cases = [
            ([], 'No face'),
            ([face(), face()], 'One person'),
            ([face(box=(0.45, 0.4, 0.55, 0.6))], 'closer'),
            ([face(box=(0.2, 0.02, 0.8, 0.98))], 'back'),
            ([face(box=(0.02, 0.2, 0.26, 0.75))], 'middle'),
            ([face(blink=0.9)], 'eyes open'),
        ]
        for faces, words in cases:
            with self.subTest(words=words):
                self.assertIn(words, ' '.join(check_shot(frame, faces).problems))
        self.assertIn('too dark', check_shot((frame * 0.2).astype(np.uint8), [face()]).problems[0])
        self.assertIn('Too bright', check_shot(np.full((H, W, 3), 250, np.uint8), [face()]).problems[0])
        flat = np.full((H, W, 3), 128, np.uint8)
        self.assertIn('Hold still', check_shot(flat, [face()]).problems)


class TestScanner(unittest.TestCase):
    def test_front_left_right(self):
        clock, detect = FakeClock(), FakeDetect(face(0))
        scanner, frame = Scanner(detect, clock), busy_frame()
        self.assertEqual(scanner.current.key, 'front')
        hold(scanner, clock, frame, seconds=HOLD_SECONDS - 0.2)
        self.assertEqual((scanner.captures, scanner.message), ({}, 'Hold it there...'))
        self.assertGreater(scanner.progress, 0.5)
        hold(scanner, clock, frame, seconds=0.2)
        self.assertEqual(list(scanner.captures), ['front'])
        self.assertTrue(np.array_equal(scanner.captures['front'], cv2.flip(frame, 1)))   # saved un-mirrored
        scanner.feed(frame)                                                  # during the pause: ignored
        self.assertEqual(scanner.message, 'Got it!')
        clock.now += PAUSE_SECONDS
        scanner.feed(frame)                                                  # still facing front
        self.assertEqual(scanner.message, 'Keep turning to your left')
        detect.faces = [face(-35)]
        capture(scanner, clock, frame)
        detect.faces = [face(35, level=0.7)]                                # chin dropped
        scanner.feed(frame)
        self.assertIn('chin level', scanner.message)
        detect.faces = [face(35)]
        capture(scanner, clock, frame)
        self.assertTrue(scanner.done)
        self.assertEqual(list(scanner.captures), ['front', 'left', 'right'])
        scanner.redo('left')
        self.assertEqual(scanner.current.key, 'left')
        scanner.redo()
        self.assertEqual((scanner.captures, scanner.current.key), ({}, 'front'))

    def test_no_capture_while_still_turning(self):
        # passing through the range on the way round doesn't count: the head must settle
        clock, detect = FakeClock(), FakeDetect(face(0))
        scanner, frame = Scanner(detect, clock), busy_frame()
        capture(scanner, clock, frame)
        for turn in range(-22, -56, -3):                                    # turning steadily left
            detect.faces = [face(turn)]
            scanner.feed(frame)
            clock.now += 0.1
        self.assertNotIn('left', scanner.captures)
        self.assertEqual(scanner.message, 'Hold still')
        detect.faces = [face(-35)]
        hold(scanner, clock, frame)
        self.assertIn('left', scanner.captures)

    def test_a_problem_restarts_the_hold(self):
        clock, detect = FakeClock(), FakeDetect(face(0))
        scanner = Scanner(detect, clock)
        hold(scanner, clock, busy_frame(), seconds=HOLD_SECONDS - 0.2)
        detect.faces = []
        scanner.feed(busy_frame())
        self.assertEqual(scanner.progress, 0)
        self.assertIn('No face', scanner.message)

    def test_turned_too_far_to_be_found(self):
        clock, detect = FakeClock(), FakeDetect(face(0))
        scanner = Scanner(detect, clock)
        capture(scanner, clock, busy_frame())
        detect.faces = [face(-50)]
        scanner.feed(busy_frame())
        detect.faces = []                                                   # turned out of sight
        scanner.feed(busy_frame())
        self.assertEqual(scanner.message, 'Too far: turn back a little')

    def test_the_sharpest_frame_is_kept(self):
        clock = FakeClock()
        scanner = Scanner(FakeDetect(face(0)), clock)
        sharp = busy_frame(1)
        soft = cv2.addWeighted(sharp, 0.5, cv2.GaussianBlur(sharp, (0, 0), 2), 0.5, 0)   # softer, but passes
        for i in range(12):
            scanner.feed(sharp if i == 4 else soft)
            clock.now += 0.1
        self.assertTrue(np.array_equal(scanner.captures['front'], cv2.flip(sharp, 1)))


class TestPhotos(unittest.TestCase):
    def test_sort_photos_by_turn(self):
        # each photo's brightness says which way its (made-up) face is turned
        turns = {50: 0, 100: 30, 150: -40, 200: None}
        def detect(img):
            turn = turns[int(img[0, 0, 0])]
            return [] if turn is None else [face(turn)]
        photos = [np.full((10, 10, 3), v, np.uint8) for v in turns]
        found, problems = sort_photos(photos, detect)
        self.assertEqual({k: int(v[0, 0, 0]) for k, v in found.items()}, {'front': 50, 'left': 150, 'right': 100})
        self.assertEqual(problems, ['Photo 4: no face found'])
        self.assertEqual(sort_photos([], detect), ({}, []))


class TestRealDetector(unittest.TestCase):
    def test_it_starts_in_both_modes(self):
        # the real MediaPipe model, with blink scores turned on; a blank picture has no face
        for still in (False, True):
            detector = FaceDetector(MODELS_DIR, still=still)
            try:
                self.assertEqual(detector(np.zeros((H, W, 3), np.uint8)), [])
            finally:
                detector.close()


if __name__ == '__main__':
    unittest.main()
