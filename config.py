from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


class Settings(BaseSettings):
    FILES_DIR: Path
    LOGS_DIR: Path
    CLOUD_API_KEY: str
    IS_DEBUG: bool = False
    DATABASE_URL: AnyUrl

    model_config = SettingsConfigDict(env_file=".env")


_settings = Settings()  # type: ignore

def get_settings() -> Settings:
    return _settings
