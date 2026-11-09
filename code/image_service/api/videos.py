# videos: a short-lived store of uploaded videos, so the calling app can fetch each one and
# pass it on (to its own storage or a cloud provider). The service doesn't process videos;
# it only checks that a file really is MP4 or WebM. Videos are kept on disk, since five
# minutes of webcam video is around 150 MB, and they expire after a while (2 hours by default).
import secrets
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

CHUNK = 1024 * 1024                    # copied 1 MB at a time


class NotAVideo(Exception):
    pass

class VideoTooBig(Exception):
    pass

class StorageFull(Exception):
    pass


def video_format(head):
    # (media type, file extension) from a file's first bytes, or None if it isn't MP4 or WebM
    if len(head) >= 12 and head[4:8] == b'ftyp':       # MP4 (ISO media): a size, then "ftyp"
        return 'video/mp4', 'mp4'
    if head[:4] == b'\x1a\x45\xdf\xa3':                # WebM (Matroska's EBML header)
        return 'video/webm', 'webm'
    return None


@dataclass
class StoredVideo:
    video_id: str
    path: Path
    content_type: str
    extension: str
    size: int
    duration_seconds: float | None     # as the uploader said; the service doesn't read the video
    expires_at: float                  # time.time() when it is deleted


def _remove(path):
    # a file being downloaded can't be deleted on Windows; it's left for the next start-up
    with suppress(OSError):
        path.unlink(missing_ok=True)


class VideoStore:
    def __init__(self, folder, ttl_seconds):
        self.folder = Path(folder)
        self.ttl_seconds = ttl_seconds
        self._videos = {}                  # video_id -> StoredVideo, oldest first
        self._lock = threading.Lock()      # uploads and downloads run in parallel threads
        self.folder.mkdir(parents=True, exist_ok=True)
        # files from an earlier run: nothing knows their ids any more, so they go
        for leftover in self.folder.iterdir():
            if leftover.is_file():
                _remove(leftover)

    def add(self, source, max_bytes, storage_bytes, duration_seconds=None):
        # copies a video from a file object into the store. Raises NotAVideo, VideoTooBig (over
        # max_bytes) or StorageFull (the stored videos would pass storage_bytes; nothing is
        # dropped to make room, since the app may not have fetched them yet).
        head = source.read(CHUNK)
        kind = video_format(head)
        if kind is None:
            raise NotAVideo()
        content_type, extension = kind
        with self._lock:
            self._purge()
            used = sum(video.size for video in self._videos.values())
        video_id = secrets.token_urlsafe(12)
        partial = self.folder / f'{video_id}.{extension}.part'     # renamed once it's complete
        size = 0
        try:
            with open(partial, 'wb') as out:
                chunk = head
                while chunk:
                    size += len(chunk)
                    if size > max_bytes:
                        raise VideoTooBig()
                    if used + size > storage_bytes:
                        raise StorageFull()
                    out.write(chunk)
                    chunk = source.read(CHUNK)
        except BaseException:
            _remove(partial)
            raise
        path = partial.with_suffix('')
        partial.rename(path)
        video = StoredVideo(video_id, path, content_type, extension, size, duration_seconds,
                            time.time() + self.ttl_seconds)
        with self._lock:
            self._videos[video_id] = video
        return video

    def get(self, video_id):
        with self._lock:
            self._purge()
            return self._videos.get(video_id)

    def delete(self, video_id):
        with self._lock:
            video = self._videos.pop(video_id, None)
        if video is None:
            return False
        _remove(video.path)
        return True

    def clear(self):
        # delete every stored video now; returns how many there were
        with self._lock:
            videos = list(self._videos.values())
            self._videos.clear()
        for video in videos:
            _remove(video.path)
        return len(videos)

    def _purge(self):
        # (called with the lock held)
        now = time.time()
        for video_id in [vid for vid, video in self._videos.items() if video.expires_at <= now]:
            _remove(self._videos.pop(video_id).path)
