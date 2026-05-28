from datetime import datetime

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: int
    instagram_user_id: str
    username: str | None
    token_type: str
    token_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MediaResponse(BaseModel):
    id: int
    media_id: str
    instagram_user_id: str
    media_type: str
    media_url: str | None
    thumbnail_url: str | None
    permalink: str | None
    caption: str | None
    timestamp: datetime | None
    local_file_path: str | None
    ingested_at: datetime

    model_config = {"from_attributes": True}


class MediaListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    media: list[MediaResponse]


class IngestionLogResponse(BaseModel):
    id: int
    instagram_user_id: str
    status: str
    media_count: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class IngestionTriggerResponse(BaseModel):
    message: str
    instagram_user_id: str


class AuthURLResponse(BaseModel):
    auth_url: str


class TokenExchangeResponse(BaseModel):
    message: str
    instagram_user_id: str
    username: str | None


class ManualTokenRequest(BaseModel):
    access_token: str


class StatusResponse(BaseModel):
    status: str
    accounts: int
    total_media: int
    scheduler_running: bool
