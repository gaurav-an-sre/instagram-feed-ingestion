import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INSTAGRAM_AUTH_URL = "https://api.instagram.com/oauth/authorize"
INSTAGRAM_TOKEN_URL = "https://api.instagram.com/oauth/access_token"
INSTAGRAM_GRAPH_URL = "https://graph.instagram.com"

MEDIA_FIELDS = (
    "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp"
)


class InstagramClient:
    def __init__(self, access_token: str | None = None):
        self.access_token = access_token
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self._client.aclose()

    def get_authorization_url(self) -> str:
        params = {
            "client_id": settings.instagram_app_id,
            "redirect_uri": settings.instagram_redirect_uri,
            "scope": "user_profile,user_media",
            "response_type": "code",
        }
        return f"{INSTAGRAM_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> dict:
        data = {
            "client_id": settings.instagram_app_id,
            "client_secret": settings.instagram_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": settings.instagram_redirect_uri,
            "code": code,
        }
        response = await self._client.post(INSTAGRAM_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()

    async def get_long_lived_token(self, short_lived_token: str) -> dict:
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": settings.instagram_app_secret,
            "access_token": short_lived_token,
        }
        response = await self._client.get(
            f"{INSTAGRAM_GRAPH_URL}/access_token", params=params
        )
        response.raise_for_status()
        result = response.json()
        result["expires_at"] = datetime.utcnow() + timedelta(
            seconds=result.get("expires_in", 5184000)
        )
        return result

    async def refresh_long_lived_token(self) -> dict:
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": self.access_token,
        }
        response = await self._client.get(
            f"{INSTAGRAM_GRAPH_URL}/refresh_access_token", params=params
        )
        response.raise_for_status()
        result = response.json()
        result["expires_at"] = datetime.utcnow() + timedelta(
            seconds=result.get("expires_in", 5184000)
        )
        return result

    async def get_user_profile(self) -> dict:
        params = {
            "fields": "id,username,account_type,media_count",
            "access_token": self.access_token,
        }
        response = await self._client.get(
            f"{INSTAGRAM_GRAPH_URL}/me", params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_user_media(
        self, limit: int = 25, after: str | None = None
    ) -> dict:
        params: dict[str, str | int] = {
            "fields": MEDIA_FIELDS,
            "limit": limit,
            "access_token": self.access_token or "",
        }
        if after:
            params["after"] = after

        response = await self._client.get(
            f"{INSTAGRAM_GRAPH_URL}/me/media", params=params
        )
        response.raise_for_status()
        return response.json()

    async def get_all_user_media(self) -> list[dict]:
        all_media: list[dict] = []
        after: str | None = None

        while True:
            result = await self.get_user_media(limit=100, after=after)
            data = result.get("data", [])
            if not data:
                break

            all_media.extend(data)
            paging = result.get("paging", {})
            cursors = paging.get("cursors", {})
            after = cursors.get("after")

            if not after or "next" not in paging:
                break

            logger.info(
                "Fetched %d media items so far, continuing...", len(all_media)
            )

        logger.info("Total media items fetched: %d", len(all_media))
        return all_media

    async def get_media_children(self, media_id: str) -> list[dict]:
        params = {
            "fields": "id,media_type,media_url,thumbnail_url,timestamp",
            "access_token": self.access_token or "",
        }
        response = await self._client.get(
            f"{INSTAGRAM_GRAPH_URL}/{media_id}/children", params=params
        )
        response.raise_for_status()
        return response.json().get("data", [])
