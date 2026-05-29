import logging
import os
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.instagram import IngestionLog, InstagramAccount, InstagramMedia
from app.services.instagram_client import InstagramClient

logger = logging.getLogger(__name__)


async def download_media_file(url: str, save_path: str) -> str | None:
    try:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(save_path, "wb") as f:
                f.write(response.content)
        return save_path
    except Exception:
        logger.exception("Failed to download media from %s", url)
        return None


def _build_file_path(media_id: str, media_url: str) -> str:
    ext = ".jpg"
    if "?" in media_url:
        url_path = media_url.split("?")[0]
    else:
        url_path = media_url
    if "." in url_path.split("/")[-1]:
        ext = "." + url_path.split("/")[-1].rsplit(".", 1)[-1]
    return os.path.join(settings.media_download_dir, f"{media_id}{ext}")


async def ingest_feed_for_account(
    db: Session, account: InstagramAccount
) -> int:
    log = IngestionLog(
        instagram_user_id=account.instagram_user_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()

    client = InstagramClient(access_token=account.access_token)
    try:
        media_items = await client.get_all_user_media()
        new_count = 0

        for item in media_items:
            media_id = item.get("id", "")
            existing = (
                db.query(InstagramMedia)
                .filter(InstagramMedia.media_id == media_id)
                .first()
            )
            if existing:
                continue

            media_url = item.get("media_url")
            local_path = None
            if media_url:
                save_path = _build_file_path(media_id, media_url)
                local_path = await download_media_file(media_url, save_path)

            timestamp_str = item.get("timestamp")
            timestamp = None
            if timestamp_str:
                timestamp = datetime.fromisoformat(
                    timestamp_str.replace("Z", "+00:00")
                )

            media_record = InstagramMedia(
                media_id=media_id,
                instagram_user_id=account.instagram_user_id,
                media_type=item.get("media_type", "UNKNOWN"),
                media_url=media_url,
                thumbnail_url=item.get("thumbnail_url"),
                permalink=item.get("permalink"),
                caption=item.get("caption"),
                timestamp=timestamp,
                local_file_path=local_path,
            )
            db.add(media_record)
            new_count += 1

            if item.get("media_type") == "CAROUSEL_ALBUM":
                try:
                    children = await client.get_media_children(media_id)
                    for child in children:
                        child_id = child.get("id", "")
                        child_existing = (
                            db.query(InstagramMedia)
                            .filter(InstagramMedia.media_id == child_id)
                            .first()
                        )
                        if child_existing:
                            continue

                        child_url = child.get("media_url")
                        child_local_path = None
                        if child_url:
                            child_save_path = _build_file_path(
                                child_id, child_url
                            )
                            child_local_path = await download_media_file(
                                child_url, child_save_path
                            )

                        child_record = InstagramMedia(
                            media_id=child_id,
                            instagram_user_id=account.instagram_user_id,
                            media_type=child.get("media_type", "UNKNOWN"),
                            media_url=child_url,
                            thumbnail_url=child.get("thumbnail_url"),
                            permalink=item.get("permalink"),
                            caption=None,
                            timestamp=timestamp,
                            local_file_path=child_local_path,
                        )
                        db.add(child_record)
                        new_count += 1
                except Exception:
                    logger.exception(
                        "Failed to fetch children for carousel %s", media_id
                    )

        db.commit()

        log.status = "completed"
        log.media_count = new_count
        log.completed_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Ingestion completed for user %s: %d new media items",
            account.instagram_user_id,
            new_count,
        )
        return new_count

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        log.completed_at = datetime.utcnow()
        db.commit()
        logger.exception(
            "Ingestion failed for user %s", account.instagram_user_id
        )
        raise
    finally:
        await client.close()


async def ingest_all_accounts(db: Session) -> dict[str, int]:
    accounts = db.query(InstagramAccount).all()
    results: dict[str, int] = {}

    for account in accounts:
        try:
            count = await ingest_feed_for_account(db, account)
            results[account.instagram_user_id] = count
        except Exception:
            logger.exception(
                "Failed to ingest for account %s",
                account.instagram_user_id,
            )
            results[account.instagram_user_id] = -1

    return results
