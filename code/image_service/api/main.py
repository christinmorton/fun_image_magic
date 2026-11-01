# main: the FastAPI app. Run from the image_service folder:
#   .\.venv\Scripts\python.exe -m uvicorn api.main:app --port 8000
# then open http://127.0.0.1:8000/docs for the interactive API docs.
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response

from core import ASSETS_DIR
from core.asset_library import load_art

from .auth import require_token
from .catalog import ART_KINDS, Catalog, art_images, build_catalog, thumbnail_png
from .settings import SERVICE_VERSION


@asynccontextmanager
async def lifespan(app):
    # load the art once when the service starts, not on every request
    app.state.art = load_art(ASSETS_DIR)
    app.state.catalog = build_catalog(app.state.art)
    app.state.thumbnails = {}          # (kind, index) -> PNG bytes, made on first request
    yield


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

app.include_router(v1)
