# main: the FastAPI app. Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
# then open http://127.0.0.1:8000/docs for the interactive API docs.
import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Body, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from core import ASSETS_DIR, MODELS_DIR
from core.ai import AI_PRESETS_BY_KEY, GeminiGenerator
from core.asset_library import load_art
from core.look import render as render_look
from core.overlays import fit_frame
from core.slots import SLOT_COUNT, Slot, Slots
from core.tracking import Tracker

from .ai_jobs import AiJobs
from .auth import require_token
from .limits import RateLimiter
from .catalog import ART_KINDS, Catalog, art_images, build_catalog, full_png, thumbnail_png
from .looks import ImageOptions, LookIn, encode_image, to_core_look
from .photos import MAX_UPLOAD_BYTES, PhotoStore, decode_upload
from .settings import (SERVICE_VERSION, ai_configured, ai_daily_limit, photo_ttl_seconds,
                       rate_limit_per_minute, service_token, video_dir, video_max_bytes,
                       video_storage_bytes, video_ttl_seconds)
from .videos import NotAVideo, StorageFull, VideoStore, VideoTooBig


@asynccontextmanager
async def lifespan(app):
    # load the art and the MediaPipe models once when the service starts
    app.state.art = load_art(ASSETS_DIR)
    app.state.catalog = build_catalog(app.state.art)
    app.state.thumbnails = {}          # (kind, index) -> PNG bytes, made on first request
    app.state.full_images = {}         # the same, at full size
    app.state.tracker = Tracker(MODELS_DIR)
    app.state.photos = PhotoStore(app.state.tracker, photo_ttl_seconds())
    app.state.videos = VideoStore(video_dir(), video_ttl_seconds())
    # AI runs only when a Gemini key is configured (creating the client makes no request)
    generator = GeminiGenerator() if ai_configured() else None
    app.state.limiter = RateLimiter(rate_limit_per_minute())
    app.state.ai_jobs = AiJobs(app.state.photos, generator, ai_daily_limit(), service_token, photo_ttl_seconds())
    yield
    app.state.videos.clear()
    app.state.ai_jobs.shutdown()
    app.state.tracker.close()


class PhotoInfo(BaseModel):
    photo_id: str                      # use this in /v1/render and /v1/compose
    width: int
    height: int
    faces: int                         # faces found (face stickers need at least one)
    person_found: bool                 # a person was found (background swap and focus need one)
    expires_at: datetime               # the photo is deleted after this (UTC)

def photo_info(photo):
    return PhotoInfo(photo_id=photo.photo_id, width=photo.image.shape[1], height=photo.image.shape[0],
                     faces=len(photo.faces), person_found=photo.person_found(),
                     expires_at=datetime.fromtimestamp(photo.expires_at, timezone.utc))

def rate_limited(request: Request):
    # for the routes that do real work: refuse with 429 when a client sends too many
    wait = request.app.state.limiter.wait_seconds(request.client.host if request.client else 'unknown')
    if wait:
        raise HTTPException(429, f'Too many requests; try again in {wait} s (RATE_LIMIT_PER_MINUTE in .env)',
                            headers={'Retry-After': str(wait)})

def stored_photo(request, photo_id):
    photo = request.app.state.photos.get(photo_id)
    if photo is None:
        raise HTTPException(404, f'Photo "{photo_id}" not found (it may have expired; upload it again)')
    return photo


app = FastAPI(
    title='Image Service',
    version=SERVICE_VERSION,
    description='Creates and edits photo booth images. '
                'Every /v1 route needs the shared token: Authorization: Bearer <IMAGE_SERVICE_TOKEN>.',
    lifespan=lifespan,
)


@app.middleware('http')
async def processing_time(request, call_next):
    # every response says how long the service worked on it, so the app can log or show it:
    #   X-Processing-Time-Ms: 68.4      Server-Timing: app;dur=68.4
    start = time.perf_counter()
    response = await call_next(request)
    ms = f'{(time.perf_counter() - start) * 1000:.1f}'
    response.headers['X-Processing-Time-Ms'] = ms
    response.headers['Server-Timing'] = f'app;dur={ms}'
    return response


@app.get('/health', tags=['service'])
def health():
    # no token needed, so a monitor or the app can check the service is up
    return {'status': 'ok', 'version': SERVICE_VERSION}


v1 = APIRouter(prefix='/v1', dependencies=[Depends(require_token)])

@v1.get('/catalog', response_model=Catalog, tags=['catalog'])
def catalog(request: Request):
    # everything a user can choose, with the numbers to put in a look
    return request.app.state.catalog

def art_picture(request, kind, index):
    # one picture from the art library, or 404
    if kind not in ART_KINDS:
        raise HTTPException(404, f'Unknown kind "{kind}"; use one of {ART_KINDS}')
    images = art_images(request.app.state.art, kind)
    if not 0 <= index < len(images):
        raise HTTPException(404, f'No {kind} number {index}; there are {len(images)}')
    return images[index]

def png_response(data):
    return Response(data, media_type='image/png', headers={'Cache-Control': 'public, max-age=86400'})

@v1.get('/catalog/{kind}/{index}/thumbnail.png', tags=['catalog'],
        responses={200: {'content': {'image/png': {}}, 'description': 'A PNG thumbnail (up to 200 px)'}})
def thumbnail(kind: str, index: int, request: Request):
    picture = art_picture(request, kind, index)
    cache = request.app.state.thumbnails
    if (kind, index) not in cache:
        cache[(kind, index)] = thumbnail_png(picture)
    return png_response(cache[(kind, index)])

@v1.get('/catalog/{kind}/{index}/image.png', tags=['catalog'],
        responses={200: {'content': {'image/png': {}}, 'description': 'The full-size picture, as PNG'}})
def art_image(kind: str, index: int, request: Request,
              width: int | None = Query(None, ge=16, le=4096, description='Frames only, with height: fit the frame to this size'),
              height: int | None = Query(None, ge=16, le=4096, description='Frames only, with width')):
    # the full-size picture, for an app that draws the art itself (e.g. live, over a camera).
    # A frame fitted to a photo's size is exactly what a render puts on that photo.
    picture = art_picture(request, kind, index)
    if (width is None) != (height is None):
        raise HTTPException(422, 'Give both width and height, or neither')
    if width is not None:
        if kind != 'frames':
            raise HTTPException(422, 'Only frames can be fitted to a size (leave out width and height)')
        return png_response(full_png(fit_frame(picture, width, height)))
    cache = request.app.state.full_images
    if (kind, index) not in cache:
        cache[(kind, index)] = full_png(picture)
    return png_response(cache[(kind, index)])


@v1.post('/photos', status_code=201, response_model=PhotoInfo, tags=['photos'], dependencies=[Depends(rate_limited)])
async def upload_photo(request: Request, image: UploadFile = File(..., description='A JPEG, PNG, BMP or WebP photo')):
    # upload a photo once: it is analysed (faces, person) and kept for a while, so it can be
    # rendered with many looks without uploading it again
    data = await image.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f'The photo is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB')
    try:
        img = decode_upload(data)
    except ValueError as error:
        raise HTTPException(400, f'Could not read the upload: {error}')
    # the analysis is slow-ish CPU work: run it in a worker thread so the server stays responsive
    photo = await run_in_threadpool(request.app.state.photos.add, img)
    return photo_info(photo)

@v1.get('/photos/{photo_id}', response_model=PhotoInfo, tags=['photos'])
def get_photo(photo_id: str, request: Request):
    return photo_info(stored_photo(request, photo_id))

@v1.delete('/photos', tags=['photos'])
def delete_all_photos(request: Request):
    # delete every stored photo and AI job right now, e.g. at the end of an event (privacy).
    # Photos only ever live in memory, so after this nothing of them is left on the service.
    return {'deleted_photos': request.app.state.photos.clear(),
            'deleted_ai_jobs': request.app.state.ai_jobs.clear()}

@v1.delete('/photos/{photo_id}', status_code=204, tags=['photos'])
def delete_photo(photo_id: str, request: Request):
    # delete a photo now instead of waiting for it to expire (privacy)
    if not request.app.state.photos.delete(photo_id):
        raise HTTPException(404, f'Photo "{photo_id}" not found')
    return Response(status_code=204)


class VideoInfo(BaseModel):
    video_id: str
    content_type: str                  # 'video/mp4' or 'video/webm'
    size_bytes: int
    duration_seconds: float | None     # as the uploader said (the service doesn't read the video)
    file_url: str                      # GET this, with the token, to download the video
    expires_at: datetime               # the video is deleted after this (UTC)

def video_info(video):
    return VideoInfo(video_id=video.video_id, content_type=video.content_type, size_bytes=video.size,
                     duration_seconds=video.duration_seconds, file_url=f'/v1/videos/{video.video_id}/file',
                     expires_at=datetime.fromtimestamp(video.expires_at, timezone.utc))

def stored_video(request, video_id):
    video = request.app.state.videos.get(video_id)
    if video is None:
        raise HTTPException(404, f'Video "{video_id}" not found (it may have expired)')
    return video

@v1.post('/videos', status_code=201, response_model=VideoInfo, tags=['videos'], dependencies=[Depends(rate_limited)])
async def upload_video(request: Request,
                       video: UploadFile = File(..., description='An MP4 or WebM video'),
                       duration_seconds: float | None = Form(None, ge=0, description='Optional: its length, kept with it')):
    # keep a recorded video for a while, so the app can fetch it (GET file_url) and pass it on
    # to its own storage. The service doesn't process videos yet.
    try:
        stored = await run_in_threadpool(request.app.state.videos.add, video.file, video_max_bytes(),
                                         video_storage_bytes(), duration_seconds)
    except NotAVideo:
        raise HTTPException(415, 'Only MP4 and WebM videos are accepted')
    except VideoTooBig:
        raise HTTPException(413, f'The video is larger than {video_max_bytes() // (1024 * 1024)} MB (VIDEO_MAX_MB in .env)')
    except StorageFull:
        raise HTTPException(507, 'The service is holding as much video as it may (VIDEO_STORAGE_MB in .env); '
                                 'fetch and delete some videos first')
    return video_info(stored)

@v1.get('/videos/{video_id}', response_model=VideoInfo, tags=['videos'])
def get_video(video_id: str, request: Request):
    return video_info(stored_video(request, video_id))

@v1.get('/videos/{video_id}/file', tags=['videos'], response_class=FileResponse,
        responses={200: {'content': {'video/mp4': {}, 'video/webm': {}}, 'description': 'The video file'}})
def download_video(video_id: str, request: Request):
    # the video as it was uploaded, for the app to save or send to a cloud provider
    video = stored_video(request, video_id)
    return FileResponse(video.path, media_type=video.content_type, filename=f'video-{video_id}.{video.extension}')

@v1.delete('/videos', tags=['videos'])
def delete_all_videos(request: Request):
    # delete every stored video now, e.g. once the app has fetched them (privacy)
    return {'deleted_videos': request.app.state.videos.clear()}

@v1.delete('/videos/{video_id}', status_code=204, tags=['videos'])
def delete_video(video_id: str, request: Request):
    # delete a video now, e.g. once the app has it, instead of waiting for it to expire
    if not request.app.state.videos.delete(video_id):
        raise HTTPException(404, f'Video "{video_id}" not found')
    return Response(status_code=204)


class RenderRequest(ImageOptions):
    photo_id: str
    look: LookIn = LookIn()

IMAGE_RESPONSES = {200: {'content': {'image/png': {}, 'image/jpeg': {}}, 'description': 'The finished image'}}

def image_response(data, media_type, name):
    # "inline" shows the image (in a browser or /docs); the file name is used when it's saved
    extension = 'jpg' if media_type == 'image/jpeg' else 'png'
    return Response(data, media_type=media_type,
                    headers={'Content-Disposition': f'inline; filename="{name}.{extension}"'})

# ready-made request bodies for the /docs page (its own example fills in every default, and
# the smallest max_width, which renders an unchanged 64 px image)
PHOTO = 'PASTE-YOUR-PHOTO-ID'
RENDER_EXAMPLES = {
    'full_look': {
        'summary': 'A full look',
        'description': 'Sunglasses, Vegas background, color pop, classic frame and a mascot prop',
        'value': {'photo_id': PHOTO, 'look': {
            'sticker': 0, 'background': 5, 'focus': 1, 'frame': 0,
            'props': [{'prop': 5, 'x': 0.8, 'y': 0.6, 'size': 0.6}]}},
    },
    'preset_and_frame': {
        'summary': 'A preset and a frame, as JPEG',
        'value': {'photo_id': PHOTO, 'look': {'preset': 4, 'frame': 2}, 'format': 'jpeg', 'quality': 90},
    },
    'plain': {
        'summary': 'Just the photo (nothing changed)',
        'value': {'photo_id': PHOTO},
    },
}
COMPOSE_EXAMPLES = {
    'grid_of_looks': {
        'summary': 'A 2x2 grid: one photo, four looks',
        'value': {'layout': 'grid', 'slots': [
            {'photo_id': PHOTO, 'look': {'preset': 1, 'frame': 1}},
            {'photo_id': PHOTO, 'look': {'preset': 4, 'frame': 2}},
            {'photo_id': PHOTO, 'look': {'preset': 6, 'frame': 3}},
            {'photo_id': PHOTO, 'look': {'preset': 11, 'frame': 4}}]},
    },
    'strip': {
        'summary': 'A photo strip, as JPEG',
        'value': {'layout': 'strip', 'format': 'jpeg', 'slots': [
            {'photo_id': PHOTO, 'look': {'frame': 0}},
            {'photo_id': PHOTO, 'look': {'preset': 2, 'frame': 0}},
            {'photo_id': PHOTO, 'look': {'preset': 7, 'frame': 0}}]},
    },
}

@v1.post('/render', tags=['images'], response_class=Response, responses=IMAGE_RESPONSES,
         dependencies=[Depends(rate_limited)])
def render(request: Request, body: RenderRequest = Body(openapi_examples=RENDER_EXAMPLES)):
    # one photo + one look -> the finished image (runs in a worker thread: it's a plain def)
    photo = stored_photo(request, body.photo_id)
    art = request.app.state.art
    look = to_core_look(body.look, art)
    picture = render_look(photo.image.copy(), look, art, photo.faces, photo.person_mask)
    data, media_type = encode_image(picture, body)
    return image_response(data, media_type, 'render')


class SlotIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    photo_id: str | None = Field(None, description='Leave out (or null) for an empty slot')
    look: LookIn = LookIn()

class ComposeRequest(ImageOptions):
    layout: Literal['strip', 'grid'] = 'strip'
    slots: list[SlotIn] = Field(min_length=1, max_length=SLOT_COUNT, description=f'Up to {SLOT_COUNT}, in order')

@v1.post('/compose', tags=['images'], response_class=Response, responses=IMAGE_RESPONSES,
          dependencies=[Depends(rate_limited)])
def compose(request: Request, body: ComposeRequest = Body(openapi_examples=COMPOSE_EXAMPLES)):
    # up to four photos, each with its own look -> one strip (stacked) or 2x2 grid, like the
    # desktop editor saves it: empty slots are left out of a strip and white in a grid
    art = request.app.state.art
    slots = Slots()
    for i, slot_in in enumerate(body.slots):
        if slot_in.photo_id is None:
            continue
        photo = stored_photo(request, slot_in.photo_id)
        try:
            look = to_core_look(slot_in.look, art)
        except HTTPException as error:
            raise HTTPException(error.status_code, f'slots[{i}]: {error.detail}')
        slots.slots[i] = Slot(photo.image, look, photo.faces, photo.person_mask)
    if not slots.any_filled():
        raise HTTPException(422, 'At least one slot needs a photo_id')
    picture, _ = slots.compose(art, body.layout.capitalize(), for_saving=True)
    data, media_type = encode_image(picture, body)
    return image_response(data, media_type, body.layout)


class AiJobRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra={'examples': [
        {'photo_id': 'PASTE-YOUR-PHOTO-ID', 'preset': 'comic'}]})
    photo_id: str = Field(description='An unedited photo from POST /v1/photos')
    preset: str = Field(description='A key from the catalog "ai_presets", e.g. "comic" or "vegas_strip"')
    callback_url: AnyHttpUrl | None = Field(None, description='Optional: where to POST the finished job (signed)')

class AiJobInfo(BaseModel):
    job_id: str
    photo_id: str
    preset: str
    status: Literal['queued', 'running', 'done', 'failed']
    stage: Literal['queued', 'preparing', 'generating', 'checking_person', 'saving', 'done', 'failed']
    stage_label: str = Field(description='The stage in words, e.g. "The AI is creating the image"')
    progress: int = Field(description='0-100; while generating it moves on with time (an estimate)')
    elapsed_seconds: float = Field(description='Since the work started (not counting the queue)')
    estimated_seconds: float = Field(description='Expected total, from how long recent jobs took')
    eta_seconds: float = Field(description='Expected time left (0 when finished)')
    result_photo_id: str | None = Field(None, description='When done: a new photo to render with any look')
    person_kept: bool | None = Field(None, description='Backgrounds: was the original person put back on top?')
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

class AiUsage(BaseModel):
    date: str                          # UTC day
    used: int
    limit: int                         # AI_DAILY_LIMIT
    remaining: int
    estimated_cost_usd: float

def ai_jobs(request):
    jobs = request.app.state.ai_jobs
    if jobs.generator is None:
        raise HTTPException(503, 'AI is not configured: set GEMINI_API_KEY in the image service .env')
    return jobs

@v1.post('/ai/jobs', status_code=202, response_model=AiJobInfo, tags=['ai'], dependencies=[Depends(rate_limited)])
def start_ai_job(body: AiJobRequest, request: Request):
    # start an AI preset on a photo; it runs in the background (10-30 s). Poll
    # GET /v1/ai/jobs/{job_id}, or give a callback_url to be told when it's done.
    # Tip: send the unedited photo, then render the result with frames and props on top.
    jobs = ai_jobs(request)
    if body.preset not in AI_PRESETS_BY_KEY:
        raise HTTPException(422, f'Unknown AI preset "{body.preset}"; use one of {list(AI_PRESETS_BY_KEY)}')
    photo = stored_photo(request, body.photo_id)
    if not jobs.limit.try_use():
        raise HTTPException(429, f'The daily AI limit ({jobs.limit.limit} images) has been reached; '
                                 'it resets at midnight UTC (AI_DAILY_LIMIT in .env)')
    job = jobs.submit(photo, body.preset, str(body.callback_url) if body.callback_url else None)
    return job.as_dict()

@v1.get('/ai/jobs/{job_id}', response_model=AiJobInfo, tags=['ai'])
def get_ai_job(job_id: str, request: Request):
    job = request.app.state.ai_jobs.get(job_id)
    if job is None:
        raise HTTPException(404, f'AI job "{job_id}" not found (it may have expired)')
    return job.as_dict()

@v1.get('/ai/jobs/{job_id}/events', tags=['ai'], response_class=StreamingResponse,
        responses={200: {'content': {'text/event-stream': {}},
                         'description': 'Server-Sent Events: the job about once a second until it ends'}})
async def ai_job_events(job_id: str, request: Request):
    # a live stream of the job for a progress bar: one "progress" event about once a second
    # (the same fields as GET /v1/ai/jobs/{id}), then one "done" or "failed" event, then it closes
    jobs = request.app.state.ai_jobs
    if jobs.get(job_id) is None:
        raise HTTPException(404, f'AI job "{job_id}" not found (it may have expired)')

    async def events():
        give_up_at = time.time() + 10 * 60                  # never stream forever
        while time.time() < give_up_at and not await request.is_disconnected():
            job = jobs.get(job_id)
            if job is None:
                yield 'event: failed\ndata: {"error": "the job expired or was deleted"}\n\n'
                return
            event = job.status if job.status in ('done', 'failed') else 'progress'
            yield f'event: {event}\ndata: {json.dumps(job.as_dict())}\n\n'
            if event != 'progress':
                return
            await asyncio.sleep(1)

    return StreamingResponse(events(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@v1.get('/ai/usage', response_model=AiUsage, tags=['ai'])
def ai_usage(request: Request):
    # today's AI images against the daily limit, with an estimated cost
    return request.app.state.ai_jobs.limit.usage()

app.include_router(v1)
