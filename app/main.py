import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models.instagram import IngestionLog, InstagramAccount, InstagramMedia
from app.routers import accounts, auth, feed
from app.schemas.instagram import StatusResponse
from app.services.scheduler import scheduler, start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure all models reference is kept so tables are created
_models = (InstagramAccount, InstagramMedia, IngestionLog)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Instagram Feed Ingestion",
    description=(
        "An application to ingest and store Instagram feed data "
        "using the Instagram Graph API."
    ),
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

app.include_router(auth.router)
app.include_router(feed.router)
app.include_router(accounts.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Instagram Feed Ingestion API",
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/status", response_model=StatusResponse, tags=["Root"])
async def status(db: Session = Depends(get_db)):
    account_count = db.query(InstagramAccount).count()
    media_count = db.query(InstagramMedia).count()

    return StatusResponse(
        status="running",
        accounts=account_count,
        total_media=media_count,
        scheduler_running=scheduler.running,
    )
