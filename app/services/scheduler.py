import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import SessionLocal
from app.services.ingestion import ingest_all_accounts

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def scheduled_ingestion():
    logger.info("Starting scheduled ingestion...")
    db = SessionLocal()
    try:
        results = await ingest_all_accounts(db)
        for user_id, count in results.items():
            if count >= 0:
                logger.info(
                    "Scheduled ingestion for %s: %d new items",
                    user_id,
                    count,
                )
            else:
                logger.error("Scheduled ingestion failed for %s", user_id)
    except Exception:
        logger.exception("Scheduled ingestion encountered an error")
    finally:
        db.close()


def _run_ingestion():
    loop = asyncio.get_event_loop()
    loop.create_task(scheduled_ingestion())


def start_scheduler():
    interval = settings.ingestion_interval_minutes
    scheduler.add_job(
        _run_ingestion,
        "interval",
        minutes=interval,
        id="instagram_ingestion",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started. Ingestion runs every %d minutes.", interval
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
