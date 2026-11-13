import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.runtime import in_tests, prepare_schema
from app.routers import (
    admin,
    auth,
    checks,
    collaboration,
    directories,
    documents,
    reports,
    supplies,
    users,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    backup_task = None
    if not in_tests():
        await prepare_schema()
        from app.config import settings
        from app.services.scheduler import backup_loop

        if settings.BACKUP_SCHEDULE_ENABLED:
            backup_task = asyncio.create_task(backup_loop())
    yield
    if backup_task:
        backup_task.cancel()
        try:
            await backup_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="AllLove Logistics API",
    version="1.0.0",
    description="Система отслеживания поставок одежды шоурума AllLove",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://localhost:5173",
        "https://127.0.0.1:5173",
        "https://localhost",
        "https://logistics.alllove.local",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)


@app.get("/")
async def root():
    return {"message": "AllLove Logistics API is running", "version": "1.0.0"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(directories.router)
app.include_router(supplies.router)
app.include_router(documents.router)
app.include_router(checks.router)
app.include_router(collaboration.router)
app.include_router(reports.router)
app.include_router(admin.router)
