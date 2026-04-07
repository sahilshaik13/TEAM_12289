from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "EchoMemory"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = ""

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_DAYS: int = 7

    GCS_BUCKET: str = ""
    CLOUD_TASKS_QUEUE_PATH: str = ""
    WORKER_URL: str = ""

    VERTEX_AI_PROJECT: str = ""
    VERTEX_AI_LOCATION: str = "asia-south1"
    VERTEX_AI_MODEL: str = "text-embedding-004"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "chrome-extension://*",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
