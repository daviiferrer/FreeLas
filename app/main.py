import logging
import os

# Configure logging FIRST, before any other imports
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    force=True, # Force override uvicorn/other defaults
)

# Also ensure our specific loggers are set
logging.getLogger("freelaas").setLevel(getattr(logging, LOG_LEVEL))

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router
from app.pipeline.orchestrator import PipelineOrchestrator
logger = logging.getLogger("freelaas")

scheduler = AsyncIOScheduler()
orchestrator = PipelineOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 FreeLaas starting up...")

    await init_db()
    logger.info("✅ Database initialized")

    scheduler.add_job(
        orchestrator.run_full_cycle,
        "interval",
        minutes=settings.SCRAPE_INTERVAL_MINUTES,
        id="pipeline_cycle",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"⏰ Scheduler started — running every {settings.SCRAPE_INTERVAL_MINUTES} minutes")

    yield

    scheduler.shutdown()
    logger.info("👋 FreeLaas shutting down")


app = FastAPI(
    title="FreeLaas",
    description="AI Freelancer Agent for 99Freelas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "freelaas"}
