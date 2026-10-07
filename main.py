from contextlib import asynccontextmanager
from app.monitoring.orchestrator import start_monitoring, stop_monitoring
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models
from app.api.router import api_router
from app.config.settings import settings


@asynccontextmanager
async def application_lifespan(app):
    await start_monitoring()
    try:
        yield
    finally:
        await stop_monitoring()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
 lifespan=application_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.api_prefix,
)
