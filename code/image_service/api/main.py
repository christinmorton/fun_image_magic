# main: the FastAPI app. Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
# then open http://127.0.0.1:8000/docs for the interactive API docs.
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Body, Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

from core import ASSETS_DIR, MODELS_DIR
from core.ai import AI_PRESETS_BY_KEY, GeminiGenerator
from core.asset_library import load_art
from core.look import render as render_look
from core.slots import SLOT_COUNT, Slot, Slots
from core.tracking import Tracker

from .ai_jobs import AiJobs
from .auth import require_token
from .catalog import ART_KINDS, Catalog, art_images, build_catalog, thumbnail_png
from .looks import ImageOptions, LookIn, encode_image, to_core_look
from .photos import MAX_UPLOAD_BYTES, PhotoStore, decode_upload
from .settings import SERVICE_VERSION, ai_configured, ai_daily_limit, photo_ttl_seconds, service_token


@asynccontextmanager
async def lifespan(app):
    # load the art and the MediaPipe models once when the service starts
    app.state.art = load_art(ASSETS_DIR)
    app.state.catalog = build_catalog(app.state.art)
    app.state.thumbnails = {}          # (kind, index) -> PNG bytes, made on first request
    app.state.tracker = Tracker(MODELS_DIR)
    app.state.photos = PhotoStore(app.state.tracker, photo_ttl_seconds())
    # AI runs only when a Gemini key is configured (creating the client makes no request)
    generator = GeminiGenerator() if ai_configured() else None
    app.state.ai_jobs = AiJobs(app.state.photos, generator, ai_daily_limit(), service_token, photo_ttl_seconds())
    yield
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

def stored_photo(request, photo_id):
    photo = request.app.state.photos.get(photo_id)
    if photo is None:
        raise HTTPException(404, f'Photo "{photo_id}" not found (it may have expired; upload it again)')
    return photo


app = FastAPI(
    title='CSN Image Service',
    version=SERVICE_VERSION,
    description='Creates and edits photo booth images for the CSN web app. '
                'Every /v1 route needs the shared token: Authorization: Bearer <IMAGE_SERVICE_TOKEN>.',
    lifespan=lifespan,
)


@app.get('/health', tags=['service'])
def health():
    # no token needed, so a monitor or Laravel can check the service is up
    return {'status': 'ok', 'version': SERVICE_VERSION}


v1 = APIRouter(prefix='/v1', dependencies=[Depends(require_token)])

@v1.get('/catalog', response_model=Catalog, tags=['catalog'])
def catalog(request: Request):
    # everything a user can choose, with the numbers to put in a look
    return request.app.state.catalog

@v1.get('/catalog/{kind}/{index}/thumbnail.png', tags=['catalog'],
        responses={200: {'content': {'image/png': {}}, 'description': 'A PNG thumbnail (up to 200 px)'}})
def thumbnail(kind: str, index: int, request: Request):
    if kind not in ART_KINDS:
        raise HTTPException(404, f'Unknown kind "{kind}"; use one of {ART_KINDS}')
    images = art_images(request.app.state.art, kind)
    if not 0 <= index < len(images):
        raise HTTPException(404, f'No {kind} number {index}; there are {len(images)}')
    cache = request.app.state.thumbnails
    if (kind, index) not in cache:
        cache[(kind, index)] = thumbnail_png(images[index])
    return Response(cache[(kind, index)], media_type='image/png',
                    headers={'Cache-Control': 'public, max-age=86400'})


@v1.post('/photos', status_code=201, response_model=PhotoInfo, tags=['photos'])
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

@v1.delete('/photos/{photo_id}', status_code=204, tags=['photos'])
def delete_photo(photo_id: str, request: Request):
    # delete a photo now instead of waiting for it to expire (privacy)
    if not request.app.state.photos.delete(photo_id):
        raise HTTPException(404, f'Photo "{photo_id}" not found')
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
        'description': 'Sunglasses, Vegas background, color pop, classic frame and a Cody prop',
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

@v1.post('/render', tags=['images'], response_class=Response, responses=IMAGE_RESPONSES)
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

@v1.post('/compose', tags=['images'], response_class=Response, responses=IMAGE_RESPONSES)
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
    result_photo_id: str | None = Field(None, description='When done: a new photo to render with any look')
    person_kept: bool | None = Field(None, description='Backgrounds: was the original person put back on top?')
    error: str | None = None
    created_at: datetime
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

@v1.post('/ai/jobs', status_code=202, response_model=AiJobInfo, tags=['ai'])
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

@v1.get('/ai/usage', response_model=AiUsage, tags=['ai'])
def ai_usage(request: Request):
    # today's AI images against the daily limit, with an estimated cost
    return request.app.state.ai_jobs.limit.usage()

app.include_router(v1)
