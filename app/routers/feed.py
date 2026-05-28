import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.instagram import InstagramAccount, InstagramMedia
from app.schemas.instagram import (
    IngestionTriggerResponse,
    MediaListResponse,
    MediaResponse,
)
from app.services.ingestion import ingest_feed_for_account

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feed", tags=["Feed"])


@router.get("/media", response_model=MediaListResponse)
async def list_media(
    instagram_user_id: str | None = Query(
        None, description="Filter by Instagram user ID"
    ),
    media_type: str | None = Query(
        None, description="Filter by media type (IMAGE, VIDEO, CAROUSEL_ALBUM)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    query = db.query(InstagramMedia)

    if instagram_user_id:
        query = query.filter(
            InstagramMedia.instagram_user_id == instagram_user_id
        )
    if media_type:
        query = query.filter(InstagramMedia.media_type == media_type)

    total = query.count()
    offset = (page - 1) * page_size
    media_items = (
        query.order_by(InstagramMedia.timestamp.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return MediaListResponse(
        total=total,
        page=page,
        page_size=page_size,
        media=[MediaResponse.model_validate(m) for m in media_items],
    )


@router.get("/media/{media_id}", response_model=MediaResponse)
async def get_media(media_id: str, db: Session = Depends(get_db)):
    media = (
        db.query(InstagramMedia)
        .filter(InstagramMedia.media_id == media_id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return MediaResponse.model_validate(media)


@router.post("/ingest/{instagram_user_id}", response_model=IngestionTriggerResponse)
async def trigger_ingestion(
    instagram_user_id: str, db: Session = Depends(get_db)
):
    account = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.instagram_user_id == instagram_user_id)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=404,
            detail=f"Account {instagram_user_id} not found. "
            "Please authenticate first.",
        )

    try:
        count = await ingest_feed_for_account(db, account)
        return IngestionTriggerResponse(
            message=f"Ingestion completed. {count} new media items ingested.",
            instagram_user_id=instagram_user_id,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Ingestion failed: {e}"
        ) from e


@router.post("/ingest", response_model=list[IngestionTriggerResponse])
async def trigger_ingestion_all(db: Session = Depends(get_db)):
    accounts = db.query(InstagramAccount).all()
    if not accounts:
        raise HTTPException(
            status_code=404,
            detail="No accounts found. Please authenticate first.",
        )

    results = []
    for account in accounts:
        try:
            count = await ingest_feed_for_account(db, account)
            results.append(
                IngestionTriggerResponse(
                    message=f"Ingestion completed. {count} new items.",
                    instagram_user_id=account.instagram_user_id,
                )
            )
        except Exception as e:
            results.append(
                IngestionTriggerResponse(
                    message=f"Ingestion failed: {e}",
                    instagram_user_id=account.instagram_user_id,
                )
            )

    return results
