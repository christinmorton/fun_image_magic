# Checks for video uploads in the web API (no server needed). The service only keeps videos
# for the app to fetch; it doesn't process them. Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m unittest discover tests
import os
import tempfile
import time
import unittest
from pathlib import Path

from test_api import AUTH, ApiTestCase     # the shared token / client setup

from api.videos import VideoStore          # noqa: E402

MB = 1024 * 1024
# the first bytes are what the service checks; the rest stands in for the video
MP4 = b'\x00\x00\x00\x20ftypisom' + b'\x00' * 2000
WEBM = b'\x1a\x45\xdf\xa3' + b'\x00' * 2000
SETTINGS = ('VIDEO_DIR', 'VIDEO_MAX_MB', 'VIDEO_STORAGE_MB')


class VideoTestCase(ApiTestCase):
    def setUp(self):
        # each test keeps its videos in its own temporary folder
        self.saved_settings = {name: os.environ.get(name) for name in SETTINGS}
        self.folder = tempfile.TemporaryDirectory()
        os.environ['VIDEO_DIR'] = self.folder.name
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for name, value in self.saved_settings.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self.folder.cleanup()

    def upload(self, data=MP4, name='recording.mp4', type='video/mp4', **form):
        return self.client.post('/v1/videos', headers=AUTH, files={'video': (name, data, type)}, data=form)

    def files_kept(self):
        return sorted(path.name for path in Path(self.folder.name).iterdir())


class TestVideos(VideoTestCase):
    def test_upload_fetch_and_delete(self):
        response = self.upload(duration_seconds='12.5')
        self.assertEqual(response.status_code, 201, response.text)
        info = response.json()
        video_id = info['video_id']
        self.assertEqual((info['content_type'], info['size_bytes'], info['duration_seconds']), ('video/mp4', len(MP4), 12.5))
        self.assertEqual(info['file_url'], f'/v1/videos/{video_id}/file')
        self.assertEqual(self.files_kept(), [f'{video_id}.mp4'])
        self.assertEqual(self.client.get(f'/v1/videos/{video_id}', headers=AUTH).json(), info)

        # the app downloads it, exactly as uploaded, to pass it on
        file = self.client.get(info['file_url'], headers=AUTH)
        self.assertEqual(file.status_code, 200)
        self.assertEqual(file.content, MP4)
        self.assertEqual(file.headers['content-type'], 'video/mp4')
        self.assertIn(f'video-{video_id}.mp4', file.headers['content-disposition'])

        # then deletes it
        self.assertEqual(self.client.delete(f'/v1/videos/{video_id}', headers=AUTH).status_code, 204)
        self.assertEqual(self.files_kept(), [])
        self.assertEqual(self.client.get(f'/v1/videos/{video_id}', headers=AUTH).status_code, 404)
        self.assertEqual(self.client.get(info['file_url'], headers=AUTH).status_code, 404)
        self.assertEqual(self.client.delete(f'/v1/videos/{video_id}', headers=AUTH).status_code, 404)

    def test_webm_is_accepted(self):
        info = self.upload(WEBM, 'recording.webm', 'video/webm').json()
        self.assertEqual(info['content_type'], 'video/webm')
        self.assertIsNone(info['duration_seconds'])
        self.assertEqual(self.files_kept(), [f"{info['video_id']}.webm"])

    def test_the_file_is_checked_not_its_name(self):
        not_video = self.upload(b'just some text, not a video at all', 'clip.mp4', 'video/mp4')
        self.assertEqual(not_video.status_code, 415)
        self.assertEqual(self.files_kept(), [])

    def test_bad_requests(self):
        self.assertEqual(self.client.post('/v1/videos', headers=AUTH).status_code, 422)            # no file
        self.assertEqual(self.upload(duration_seconds='-3').status_code, 422)
        no_token = self.client.post('/v1/videos', files={'video': ('r.mp4', MP4, 'video/mp4')})
        self.assertEqual(no_token.status_code, 401)
        self.assertEqual(self.client.get('/v1/videos/nope/file').status_code, 401)

    def test_videos_over_the_size_limit_are_refused(self):
        os.environ['VIDEO_MAX_MB'] = '1'
        too_big = self.upload(MP4[:12] + b'\x00' * MB)
        self.assertEqual(too_big.status_code, 413)
        self.assertIn('VIDEO_MAX_MB', too_big.json()['detail'])
        self.assertEqual(self.files_kept(), [])                   # the part already copied is removed
        self.assertEqual(self.upload(MP4[:12] + b'\x00' * (MB - 100)).status_code, 201)

    def test_full_storage_refuses_new_videos_and_keeps_the_old(self):
        os.environ['VIDEO_STORAGE_MB'] = '1'
        first = self.upload(MP4[:12] + b'\x00' * (600 * 1024)).json()
        second = self.upload(MP4[:12] + b'\x00' * (600 * 1024))
        self.assertEqual(second.status_code, 507)
        self.assertEqual(self.files_kept(), [f"{first['video_id']}.mp4"])
        # once the app has taken the first one, there's room again
        self.client.delete(f"/v1/videos/{first['video_id']}", headers=AUTH)
        self.assertEqual(self.upload(MP4[:12] + b'\x00' * (600 * 1024)).status_code, 201)

    def test_delete_all(self):
        for _ in range(3):
            self.upload()
        self.assertEqual(self.client.delete('/v1/videos', headers=AUTH).json(), {'deleted_videos': 3})
        self.assertEqual(self.files_kept(), [])

    def test_videos_expire(self):
        video_id = self.upload().json()['video_id']
        self.client.app.state.videos._videos[video_id].expires_at = time.time() - 1   # pretend time passed
        self.assertEqual(self.client.get(f'/v1/videos/{video_id}', headers=AUTH).status_code, 404)
        self.assertEqual(self.files_kept(), [])


class TestVideoStore(unittest.TestCase):
    def test_files_from_an_earlier_run_are_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'old.mp4').write_bytes(MP4)
            VideoStore(folder, 60)
            self.assertEqual(list(Path(folder).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
