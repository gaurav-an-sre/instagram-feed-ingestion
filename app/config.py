from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    instagram_app_id: str = ""
    instagram_app_secret: str = ""
    instagram_redirect_uri: str = "http://localhost:8000/auth/callback"
    instagram_access_token: str = ""
    database_url: str = "sqlite:///./instagram_feed.db"
    media_download_dir: str = "./media"
    ingestion_interval_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
