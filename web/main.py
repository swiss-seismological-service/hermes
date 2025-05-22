from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from web.repositories.database import sessionmanager
from web.routers import (forecasts, forecastseries, injections, modelconfigs,
                         modelruns, projects)


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
app.include_router(modelconfigs.router, prefix='/v1')
app.include_router(injections.router, prefix='/v1')

app = CORSMiddleware(
    app=app,
    # allow_origins=get_settings().ALLOW_ORIGINS,
    # allow_origin_regex=get_settings().ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)
