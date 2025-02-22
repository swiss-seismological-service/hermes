from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from web.database import sessionmanager
from web.routers import data, forecasts, forecastseries, modelruns, projects
from web.routers.v2 import modelruns as modelruns2
from web.routers.v2 import router as v2


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Function that handles startup and shutdown events.
    To understand more, read https://fastapi.tiangolo.com/advanced/events/
    """
    yield
    if sessionmanager._engine is not None:
        # Close the DB connection
        await sessionmanager.close()

app = FastAPI(lifespan=lifespan)

app.include_router(projects.router, prefix='/v1')
app.include_router(forecastseries.router, prefix='/v1')
app.include_router(forecasts.router, prefix='/v1')
app.include_router(modelruns.router, prefix='/v1')
app.include_router(data.router, prefix='/v1')

app.include_router(v2, prefix='/v2')
app.include_router(modelruns2.router, prefix='/v2')

app = CORSMiddleware(
    app=app,
    # allow_origins=get_settings().ALLOW_ORIGINS,
    # allow_origin_regex=get_settings().ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
