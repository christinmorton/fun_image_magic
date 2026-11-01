# sources: where the picture comes from - the webcam, or an uploaded image file.
from tkinter import Tk, filedialog

import cv2
import numpy as np


# uploaded images: big photos are shrunk to fit on screen (never enlarged)
MAX_IMAGE_W, MAX_IMAGE_H = 960, 720


def choose_image_file():
    # opens the normal Windows "Open" dialog; returns '' if cancelled
    root = Tk()
    root.withdraw()                      # hide the empty Tk window behind the dialog
    root.attributes('-topmost', True)    # keep the dialog in front of the video
    path = filedialog.askopenfilename(title='Choose an image to edit', filetypes=[
        ('Images', '*.jpg *.jpeg *.png *.bmp *.webp'), ('All files', '*.*')])
    root.destroy()
    return path

def load_image(path):
    # np.fromfile + imdecode also works for paths with non-English characters
    try:
        img = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
    except OSError:
        return None
    if img is None:
        return None
    h, w = img.shape[:2]
    scale = min(MAX_IMAGE_W / w, MAX_IMAGE_H / h, 1.0)
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


class PictureSource:
    # either the webcam (cap) or an uploaded image (still_image), never both
    def __init__(self):
        self.cap = None
        self.still_image = None

    def open_webcam(self):
        # returns False (and keeps the current picture) if there is no webcam
        cap = cv2.VideoCapture(0)    # 0 = the default webcam
        if not cap.isOpened():
            cap.release()
            return False
        self.cap, self.still_image = cap, None
        return True

    def use_image(self, img):
        self.still_image = img
        if self.cap is not None:
            self.cap.release()           # turn the webcam off while editing a photo
            self.cap = None

    def read(self):
        # the next picture, or None if the webcam stopped
        if self.still_image is not None:
            # a fresh copy of the uploaded image every frame, so edits never build up
            return self.still_image.copy()
        ok, frame = self.cap.read()
        if not ok:
            return None
        return cv2.flip(frame, 1)        # mirrored, like a selfie camera

    def width(self):
        if self.still_image is not None:
            return self.still_image.shape[1]
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    def release(self):
        if self.cap is not None:
            self.cap.release()
