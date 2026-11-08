# photos: a short-lived, in-memory store of uploaded photos and their analysis (faces and
# person mask), so a photo is analysed once and then rendered with many looks. Photos expire
# after a while (2 hours by default), and the oldest go first if too many pile up.
import secrets
import threading
import time
from dataclasses import dataclass

import cv2
import numpy as np

MAX_UPLOAD_BYTES = 15 * 1024 * 1024    # bigger uploads are refused
MAX_SIDE = 2048                        # bigger photos are shrunk to this on their long side
MAX_PHOTOS = 200                       # the oldest are dropped beyond this


@dataclass
class StoredPhoto:
    photo_id: str
    image: object                      # BGR image
    faces: list                        # MediaPipe face landmarks
    person_mask: object                # 1 = person, 0 = background
    expires_at: float                  # time.time() when it is deleted

    def person_found(self):
        # more than 1% of the photo looks like a person
        return self.person_mask is not None and float((self.person_mask > 0.5).mean()) > 0.01


def decode_upload(data):
    # uploaded bytes -> a BGR image (big photos shrunk); ValueError if it isn't an image
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError('not an image OpenCV can read (use JPEG, PNG, BMP or WebP)')
    h, w = img.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    return img


class PhotoStore:
    def __init__(self, tracker, ttl_seconds, max_photos=MAX_PHOTOS):
        self.tracker = tracker
        self.ttl_seconds = ttl_seconds
        self.max_photos = max_photos
        self._photos = {}                  # photo_id -> StoredPhoto, oldest first
        self._lock = threading.Lock()      # requests run in parallel threads; MediaPipe can't

    def add(self, image):
        with self._lock:
            faces, person_mask = self.tracker.analyse_still(image)
            self._purge()
            while len(self._photos) >= self.max_photos:
                self._photos.pop(next(iter(self._photos)))         # drop the oldest
            photo = StoredPhoto(secrets.token_urlsafe(12), image, faces, person_mask,
                                time.time() + self.ttl_seconds)
            self._photos[photo.photo_id] = photo
            return photo

    def find_person(self, image):
        # the person mask of any image (used to check AI results), or None if nobody is there
        with self._lock:
            _, person_mask = self.tracker.analyse_still(image)
        found = person_mask is not None and float((person_mask > 0.5).mean()) > 0.01
        return person_mask if found else None

    def get(self, photo_id):
        with self._lock:
            self._purge()
            return self._photos.get(photo_id)

    def delete(self, photo_id):
        with self._lock:
            return self._photos.pop(photo_id, None) is not None

    def clear(self):
        # delete every stored photo now; returns how many there were
        with self._lock:
            count = len(self._photos)
            self._photos.clear()
            return count

    def _purge(self):
        now = time.time()
        for photo_id in [pid for pid, photo in self._photos.items() if photo.expires_at <= now]:
            del self._photos[photo_id]
