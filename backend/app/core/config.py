import tempfile
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_FILESYSTEM_ALLOWED_PATHS = [
    "/tmp/verifyflow",
    str(Path(tempfile.gettempdir()) / "verifyflow"),
]


class Settings(BaseSettings):
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_judge_model: str
    github_token: str
    github_owner: str
    filesystem_allowed_paths: list[str] = DEFAULT_FILESYSTEM_ALLOWED_PATHS
    browser_channels: list[str] = ["msedge", "chrome", "chromium"]
    max_retries: int
    verification_confidence_threshold: float

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
