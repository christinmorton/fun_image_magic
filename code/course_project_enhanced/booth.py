# booth: the photo strip - a countdown, a shot, repeated, then the shots stacked into a strip.
import cv2
import numpy as np


class PhotoStrip:
    def __init__(self, shots_per_strip=4, seconds_per_shot=3):
        self.shots_per_strip = shots_per_strip
        self.seconds_per_shot = seconds_per_shot
        self.shooting = False
        self.shots = []
        self.next_shot_at = 0
        self.flash_until = 0

    def start(self, now):
        if not self.shooting:
            self.shooting, self.shots, self.next_shot_at = True, [], now + self.seconds_per_shot

    def update(self, picture, now):
        # call every frame; returns (seconds_left, strip)
        # seconds_left is the countdown number to show (or None); strip is the finished strip (or None)
        if not self.shooting:
            return None, None
        if now < self.next_shot_at:
            return int(self.next_shot_at - now) + 1, None
        self.shots.append(cv2.copyMakeBorder(picture, 12, 12, 12, 12, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
        self.next_shot_at = now + self.seconds_per_shot
        self.flash_until = now + 0.15
        if len(self.shots) == self.shots_per_strip:
            self.shooting = False
            return None, np.vstack(self.shots)
        return None, None

    def flashing(self, now):
        # True for a moment after each shot, for a white flash
        return now < self.flash_until
