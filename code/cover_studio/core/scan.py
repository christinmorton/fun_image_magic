# scan: the guided multi-angle face scan. The person looks straight at the camera, then
# turns left, then right; each angle is captured on its own once the head is in place and
# the shot is good (one face, big enough, in the middle, well lit, sharp, eyes open). The
# sharpest frame of a short steady hold is kept. No windows here: desktop/scan.py shows the
# camera and the guide. Turns are measured in the mirrored (selfie) picture the person
# sees, so "left" is their own left; captures are saved the right way round.
import math
import time
from dataclasses import dataclass, field

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

NOSE, FOREHEAD, CHIN, SIDE_A, SIDE_B = 1, 10, 152, 234, 454      # MediaPipe face mesh points

HOLD_SECONDS = 1.0          # how long a good, steady pose is held before it's captured
STEADY = 4.0                # degrees the head may move during the hold (more = still turning)
PAUSE_SECONDS = 1.2         # after a capture, "Got it!" shows this long before the next angle
DROPOUT_GRACE = 0.4         # a hold survives the face going missing for this long (a turned face can flicker)
# how sure the face finder must be: to pick up a face, and to keep following it from frame
# to frame. MediaPipe's default (0.5) loses faces partway through a turn; lower keeps them
FIND_CONFIDENCE, FOLLOW_CONFIDENCE = 0.4, 0.25
MIN_SHARPNESS = 40.0        # detail in the face (see sharpness()); below this is blurry
MIN_FACE, MAX_FACE = 0.3, 0.85        # face height, as a fraction of the picture's height (height,
                                      # not width: a face looks narrower as it turns, not shorter)
DARK, BRIGHT = 70, 215      # the face's average brightness (0-255) must be between these
LEVEL = 0.08                # side shots: how far the nose may move up or down the face vs the front shot
BLINK = 0.65                # eyes count as closed above this (smiling alone can reach about 0.5)


@dataclass(frozen=True)
class Angle:
    key: str                # 'front', 'left' or 'right' (also the saved file's name)
    prompt: str             # what the person is told
    low: float              # the head's turn (degrees; - is towards their left) must be
    high: float             # between low and high


# side shots are three-quarter turns: they show more of the face than a full profile, and
# the face finder loses a face that's turned much further (checked on stock portraits)
ANGLES = [
    Angle('front', 'Look straight at the camera', -10, 10),
    Angle('left', 'Turn your head slowly to your left', -55, -20),
    Angle('right', 'Turn your head slowly to your right', 20, 55),
]


@dataclass
class Face:
    landmarks: list                                   # 478 points, each with .x and .y (0-1)
    blendshapes: dict = field(default_factory=dict)   # e.g. 'eyeBlinkLeft' -> 0.0-1.0


@dataclass
class Shot:
    # what one picture is like for scanning
    problems: list                      # what's wrong, most important first (empty = good)
    found: bool = False                 # exactly one face was found
    turn: float = 0.0                   # see head_turn()
    level: float = 0.0                  # see head_level()
    sharpness: float = 0.0


def head_turn(landmarks):
    # how far the head is turned, in rough degrees: negative towards the picture's left,
    # positive towards its right. From where the nose tip sits between the two sides of
    # the face: in the middle when facing the camera, nearer a side as the head turns
    a, b = landmarks[SIDE_A].x, landmarks[SIDE_B].x
    left, right = min(a, b), max(a, b)
    if right - left < 1e-6:
        return 0.0
    offset = (landmarks[NOSE].x - left) / (right - left) * 2 - 1
    return math.degrees(math.asin(max(-1.0, min(1.0, offset))))

def head_level(landmarks):
    # how far down the face the nose tip sits, from the forehead (0) to the chin (1); it
    # changes as the chin lifts or drops, so side shots are compared with the front shot
    top, bottom = landmarks[FOREHEAD].y, landmarks[CHIN].y
    return (landmarks[NOSE].y - top) / max(bottom - top, 1e-6)

def face_box(landmarks, w, h):
    # the face's bounding box in pixels: (x0, y0, x1, y1), kept inside the picture
    xs = [p.x for p in landmarks]
    ys = [p.y for p in landmarks]
    return (max(0, int(min(xs) * w)), max(0, int(min(ys) * h)),
            min(w, int(max(xs) * w)), min(h, int(max(ys) * h)))

def sharpness(gray):
    # how much fine detail a grey picture has (the variance of its Laplacian), measured at
    # 200 px wide so faces near and far are judged alike; low means blurry
    scale = 200 / max(gray.shape[1], 1)
    small = cv2.resize(gray, (200, max(1, int(gray.shape[0] * scale))), interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(small, cv2.CV_64F).var())

def check_shot(frame, faces):
    # everything that's wrong with this picture for scanning, and how the head is held
    h, w = frame.shape[:2]
    if not faces:
        return Shot(['No face found: look at the camera'])
    if len(faces) > 1:
        return Shot(['One person at a time, please'])
    face = faces[0]
    x0, y0, x1, y1 = face_box(face.landmarks, w, h)
    shot = Shot([], True, head_turn(face.landmarks), head_level(face.landmarks))
    size = (y1 - y0) / h
    if size < MIN_FACE:
        shot.problems.append('Come a little closer')
    elif size > MAX_FACE:
        shot.problems.append('Move back a little')
    if not (0.3 <= (x0 + x1) / 2 / w <= 0.7 and 0.25 <= (y0 + y1) / 2 / h <= 0.75):
        shot.problems.append('Move into the middle of the picture')
    if x1 - x0 < 8 or y1 - y0 < 8:
        return shot
    gray = cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    if gray.mean() < DARK:
        shot.problems.append('Your face is too dark: add some light in front of you')
    elif gray.mean() > BRIGHT:
        shot.problems.append('Too bright: move away from the light')
    shot.sharpness = sharpness(gray)
    if shot.sharpness < MIN_SHARPNESS:
        shot.problems.append('Hold still')
    blink = max(face.blendshapes.get('eyeBlinkLeft', 0.0), face.blendshapes.get('eyeBlinkRight', 0.0))
    if blink > BLINK:
        shot.problems.append('Keep your eyes open')
    return shot

def turn_advice(angle, turn):
    # what to say when the head isn't at the angle yet, or None when it is
    if angle.low <= turn <= angle.high:
        return None
    if angle.key == 'front':
        return 'Turn a little to your right' if turn < angle.low else 'Turn a little to your left'
    if angle.key == 'left':
        return 'Keep turning to your left' if turn > angle.high else 'Too far: turn back a little'
    return 'Keep turning to your right' if turn < angle.low else 'Too far: turn back a little'


class Scanner:
    # walks through ANGLES, one capture each. feed() it every frame the person sees (the
    # mirrored picture); captures holds the finished angles, the right way round. A pose
    # is captured once it has been good and steady for HOLD_SECONDS
    def __init__(self, detect, clock=time.monotonic):
        self.detect = detect            # detect(frame) -> list of Face
        self.clock = clock              # seconds (replaced in tests)
        self.captures = {}              # angle key -> BGR picture
        self.front_level = None
        self.hold = None                # the current steady hold: started, first turn, best frame...
        self.last_good = 0.0            # when the latest good frame of the hold was seen
        self.paused_until = 0.0         # after a capture, wait before the next angle
        self.message = ''
        self.turn = None                # the latest head turn seen (for the screen)
        self.seen = False               # a single face is in the latest frame
        self.just_captured = None       # the key captured by the latest feed(), for a flash

    @property
    def current(self):
        # the angle being scanned now, or None when every angle is captured
        return next((a for a in ANGLES if a.key not in self.captures), None)

    @property
    def done(self):
        return self.current is None

    @property
    def progress(self):
        # 0-1 through the current hold
        if self.hold is None:
            return 0.0
        return min(1.0, (self.clock() - self.hold['started']) / HOLD_SECONDS)

    def redo(self, key=None):
        # scan one angle again (or all of them, if key is None)
        for k in ([key] if key else list(self.captures)):
            self.captures.pop(k, None)
        if 'front' not in self.captures:
            self.front_level = None
        self.hold, self.turn, self.paused_until = None, None, 0.0

    def feed(self, frame):
        self.just_captured = None
        angle = self.current
        if angle is None or self.clock() < self.paused_until:
            return
        shot = check_shot(frame, self.detect(frame))
        self.seen = shot.found
        if not shot.found and self.hold is not None and self.clock() - self.last_good <= DROPOUT_GRACE:
            return                              # a moment's flicker: keep the hold going
        lost_while_turning = (not shot.found and self.turn is not None and angle.key != 'front'
                              and abs(self.turn) > abs(angle.high if angle.key == 'right' else angle.low) * 0.8)
        if shot.found:
            self.turn = shot.turn
        problems = list(shot.problems)
        if lost_while_turning:
            # turned so far that the face can't be found any more
            problems = ['Too far: turn back a little']
        if not problems:
            advice = turn_advice(angle, shot.turn)
            if advice:
                problems.append(advice)
            elif angle.key != 'front' and self.front_level is not None and abs(shot.level - self.front_level) > LEVEL:
                problems.append('Keep your chin level, like in the first shot')
        if not problems and self.hold is not None and abs(shot.turn - self.hold['turn']) > STEADY:
            problems.append('Hold still')                       # still turning: start the hold again
        if problems:
            self.hold, self.message = None, problems[0]
            return
        now = self.clock()
        self.last_good = now
        if self.hold is None:
            self.hold = {'started': now, 'turn': shot.turn, 'sharpness': -1.0}
        if shot.sharpness > self.hold['sharpness']:              # keep only the sharpest frame so far
            self.hold.update(sharpness=shot.sharpness, frame=frame.copy(), level=shot.level)
        self.message = 'Hold it there...'
        if now - self.hold['started'] >= HOLD_SECONDS:
            self.captures[angle.key] = cv2.flip(self.hold['frame'], 1)   # un-mirrored: how others see them
            if angle.key == 'front':
                self.front_level = self.hold['level']
            self.hold, self.message, self.just_captured = None, 'Got it!', angle.key
            self.paused_until = now + PAUSE_SECONDS


def sort_photos(photos, detect):
    # loaded photos (not mirrored) sorted into angles by how the head is turned in each:
    # {'front': ..., 'left': ..., 'right': ...} for those that fit, plus the problems found.
    # Photos are judged mirrored, like the live scan, so "left" means the same thing
    found, problems = [], []
    for i, photo in enumerate(photos):
        mirrored = cv2.flip(photo, 1)
        faces = detect(mirrored)
        if len(faces) != 1:
            problems.append(f'Photo {i + 1}: ' + ('no face found' if not faces else 'more than one face'))
            continue
        found.append((head_turn(faces[0].landmarks), photo))
    sorted_photos = {}
    if found:
        front = min(found, key=lambda f: abs(f[0]))
        sorted_photos['front'] = front[1]
        rest = [f for f in found if f is not front]
        lefts = [f for f in rest if f[0] < -10]
        rights = [f for f in rest if f[0] > 10]
        if lefts:
            sorted_photos['left'] = min(lefts, key=lambda f: f[0])[1]
        if rights:
            sorted_photos['right'] = max(rights, key=lambda f: f[0])[1]
    return sorted_photos, problems


class FaceDetector:
    # MediaPipe's face landmarker with blink detection, finding up to two faces (so a second
    # person can be noticed). Video mode follows a live camera; still mode is for photos
    def __init__(self, models_dir, still=False):
        self.still = still
        self.timestamp_ms = 0
        self.landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models_dir / 'face_landmarker.task')),
            running_mode=vision.RunningMode.IMAGE if still else vision.RunningMode.VIDEO,
            num_faces=2, output_face_blendshapes=True, min_face_detection_confidence=FIND_CONFIDENCE,
            min_face_presence_confidence=FOLLOW_CONFIDENCE, min_tracking_confidence=FOLLOW_CONFIDENCE))

    def __call__(self, frame):
        rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if self.still:
            result = self.landmarker.detect(rgb)
        else:
            self.timestamp_ms += 33          # video mode needs increasing timestamps
            result = self.landmarker.detect_for_video(rgb, self.timestamp_ms)
        shapes = result.face_blendshapes or [[] for _ in result.face_landmarks]
        return [Face(points, {c.category_name: c.score for c in blend})
                for points, blend in zip(result.face_landmarks, shapes)]

    def close(self):
        self.landmarker.close()
