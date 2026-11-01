# tracking: MediaPipe models that find faces (for stickers) and people (for background swap).
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision


class Tracker:
    def __init__(self, models_dir):
        # face landmarks: 478 points per face, up to 4 faces
        self.face_landmarker = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(models_dir / 'face_landmarker.task')),
            running_mode=vision.RunningMode.VIDEO, num_faces=4))
        # person mask: 1 = person, 0 = background
        self.segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
            base_options=BaseOptions(model_asset_path=str(models_dir / 'selfie_segmenter.tflite')),
            running_mode=vision.RunningMode.VIDEO, output_confidence_masks=True))
        self.timestamp_ms = 0      # MediaPipe video mode needs increasing timestamps

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

    def close(self):
        self.face_landmarker.close()
        self.segmenter.close()
