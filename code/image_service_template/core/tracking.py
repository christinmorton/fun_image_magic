# tracking: MediaPipe models that find faces (for stickers) and people (for background swap).
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision


def make_face_landmarker(models_dir, mode):
    # face landmarks: 478 points per face, up to 4 faces
    return vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(models_dir / 'face_landmarker.task')),
        running_mode=mode, num_faces=4))

def make_segmenter(models_dir, mode):
    # person mask: 1 = person, 0 = background
    return vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=str(models_dir / 'selfie_segmenter.tflite')),
        running_mode=mode, output_confidence_masks=True))


class Tracker:
    def __init__(self, models_dir):
        self.models_dir = models_dir
        self.face_landmarker = make_face_landmarker(models_dir, vision.RunningMode.VIDEO)
        self.segmenter = make_segmenter(models_dir, vision.RunningMode.VIDEO)
        self.timestamp_ms = 0      # MediaPipe video mode needs increasing timestamps
        # image-mode models for single photos (the editor's slots), made the first time
        # they are needed: video mode expects each frame to follow on from the last one
        self.still_landmarker = None
        self.still_segmenter = None

    def analyse(self, img, find_faces, find_person):
        # call once per frame; only runs the models that are needed
        # returns (faces, person_mask): a list of faces, and a mask or None
        self.timestamp_ms += 33
        faces, person_mask = [], None
        if find_faces or find_person:
            rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if find_person:
            person_mask = self.segmenter.segment_for_video(rgb, self.timestamp_ms).confidence_masks[0].numpy_view()
        if find_faces:
            faces = self.face_landmarker.detect_for_video(rgb, self.timestamp_ms).face_landmarks
        return faces, person_mask

    def analyse_still(self, img):
        # faces and person mask for a single photo; returns (faces, person_mask)
        if self.still_landmarker is None:
            self.still_landmarker = make_face_landmarker(self.models_dir, vision.RunningMode.IMAGE)
            self.still_segmenter = make_segmenter(self.models_dir, vision.RunningMode.IMAGE)
        rgb = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        faces = self.still_landmarker.detect(rgb).face_landmarks
        # copy the mask: the photo keeps it, and MediaPipe may reuse the memory
        person_mask = np.array(self.still_segmenter.segment(rgb).confidence_masks[0].numpy_view())
        return faces, person_mask

    def close(self):
        self.face_landmarker.close()
        self.segmenter.close()
        if self.still_landmarker is not None:
            self.still_landmarker.close()
            self.still_segmenter.close()
