import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.instagram import IngestionLog, InstagramAccount
from app.schemas.instagram import AccountResponse, IngestionLogResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/", response_model=list[AccountResponse])
async def list_accounts(db: Session = Depends(get_db)):
    accounts = db.query(InstagramAccount).all()
    return [AccountResponse.model_validate(a) for a in accounts]


@router.get("/{instagram_user_id}", response_model=AccountResponse)
async def get_account(
    instagram_user_id: str, db: Session = Depends(get_db)
):
    account = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.instagram_user_id == instagram_user_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return AccountResponse.model_validate(account)


@router.delete("/{instagram_user_id}")
async def delete_account(
    instagram_user_id: str, db: Session = Depends(get_db)
):
    account = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.instagram_user_id == instagram_user_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    db.delete(account)
    db.commit()
    return {"message": f"Account {instagram_user_id} deleted"}


@router.get(
    "/{instagram_user_id}/logs",
    response_model=list[IngestionLogResponse],
)
async def get_ingestion_logs(
    instagram_user_id: str, db: Session = Depends(get_db)
):
    logs = (
        db.query(IngestionLog)
        .filter(IngestionLog.instagram_user_id == instagram_user_id)
        .order_by(IngestionLog.started_at.desc())
        .limit(50)
        .all()
    )
    return [IngestionLogResponse.model_validate(log) for log in logs]
