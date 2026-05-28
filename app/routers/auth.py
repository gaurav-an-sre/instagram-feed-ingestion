import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.instagram import InstagramAccount
from app.schemas.instagram import (
    AuthURLResponse,
    ManualTokenRequest,
    TokenExchangeResponse,
)
from app.services.instagram_client import InstagramClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login", response_model=AuthURLResponse)
async def get_login_url():
    client = InstagramClient()
    auth_url = client.get_authorization_url()
    return AuthURLResponse(auth_url=auth_url)


@router.get("/callback", response_model=TokenExchangeResponse)
async def auth_callback(
    code: str = Query(..., description="Authorization code from Instagram"),
    db: Session = Depends(get_db),
):
    client = InstagramClient()

    try:
        token_data = await client.exchange_code_for_token(code)
    except Exception as e:
        logger.exception("Failed to exchange code for token")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to exchange authorization code: {e}",
        ) from e

    short_lived_token = token_data.get("access_token", "")
    user_id = str(token_data.get("user_id", ""))

    try:
        long_lived_data = await client.get_long_lived_token(short_lived_token)
        access_token = long_lived_data.get("access_token", short_lived_token)
        expires_at = long_lived_data.get("expires_at")
        token_type = "long_lived"
    except Exception:
        logger.warning("Failed to get long-lived token, using short-lived")
        access_token = short_lived_token
        expires_at = datetime.utcnow() + timedelta(hours=1)
        token_type = "short_lived"

    profile_client = InstagramClient(access_token=access_token)
    try:
        profile = await profile_client.get_user_profile()
        username = profile.get("username")
    except Exception:
        username = None
    finally:
        await profile_client.close()

    existing = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.instagram_user_id == user_id)
        .first()
    )
    if existing:
        existing.access_token = access_token
        existing.token_type = token_type
        existing.token_expires_at = expires_at
        existing.username = username or existing.username
        existing.updated_at = datetime.utcnow()
    else:
        account = InstagramAccount(
            instagram_user_id=user_id,
            username=username,
            access_token=access_token,
            token_type=token_type,
            token_expires_at=expires_at,
        )
        db.add(account)

    db.commit()
    await client.close()

    return TokenExchangeResponse(
        message="Authentication successful",
        instagram_user_id=user_id,
        username=username,
    )


@router.post("/token", response_model=TokenExchangeResponse)
async def set_manual_token(
    request: ManualTokenRequest,
    db: Session = Depends(get_db),
):
    client = InstagramClient(access_token=request.access_token)

    try:
        profile = await client.get_user_profile()
    except Exception as e:
        await client.close()
        raise HTTPException(
            status_code=400,
            detail=f"Invalid access token: {e}",
        ) from e

    user_id = str(profile.get("id", ""))
    username = profile.get("username")

    existing = (
        db.query(InstagramAccount)
        .filter(InstagramAccount.instagram_user_id == user_id)
        .first()
    )
    if existing:
        existing.access_token = request.access_token
        existing.username = username or existing.username
        existing.updated_at = datetime.utcnow()
    else:
        account = InstagramAccount(
            instagram_user_id=user_id,
            username=username,
            access_token=request.access_token,
            token_type="manual",
        )
        db.add(account)

    db.commit()
    await client.close()

    return TokenExchangeResponse(
        message="Token set successfully",
        instagram_user_id=user_id,
        username=username,
    )
