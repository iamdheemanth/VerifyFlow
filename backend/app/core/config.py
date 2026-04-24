import tempfile
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_FILESYSTEM_ALLOWED_PATHS = [
    "/tmp/verifyflow",
    str(Path(tempfile.gettempdir()) / "verifyflow"),
]

PLACEHOLDER_VALUES = {
    "your-key-here",
    "your-github-token",
    "your-github-username",
    "replace-me",
    "change-me",
    "changeme",
    "replace-with-at-least-32-random-characters",
    "replace-with-provider-api-key",
    "replace-with-github-token",
    "replace-with-github-owner",
}


class Settings(BaseSettings):
    database_url: str = Field(validation_alias="DATABASE_URL")
    llm_base_url: str = Field(validation_alias="LLM_BASE_URL")
    llm_api_key: str = Field(validation_alias="LLM_API_KEY")
    llm_model: str = Field(validation_alias="LLM_MODEL")
    llm_judge_model: str = Field(validation_alias="LLM_JUDGE_MODEL")
    nextauth_secret: str = Field(validation_alias="NEXTAUTH_SECRET")
    github_token: str | None = Field(default=None, validation_alias="GITHUB_TOKEN")
    github_owner: str | None = Field(default=None, validation_alias="GITHUB_OWNER")
    filesystem_allowed_paths: list[str] = Field(
        default_factory=lambda: list(DEFAULT_FILESYSTEM_ALLOWED_PATHS),
        validation_alias="FILESYSTEM_ALLOWED_PATHS",
    )
    browser_channels: list[str] = Field(
        default_factory=lambda: ["msedge", "chrome", "chromium"],
        validation_alias="BROWSER_CHANNELS",
    )
    max_retries: int = Field(validation_alias="MAX_RETRIES")
    verification_confidence_threshold: float = Field(validation_alias="VERIFICATION_CONFIDENCE_THRESHOLD")

    @field_validator(
        "database_url",
        "llm_base_url",
        "llm_api_key",
        "llm_model",
        "llm_judge_model",
        "nextauth_secret",
    )
    @classmethod
    def _required_string_must_not_be_blank(cls, value: str, info):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{info.field_name.upper()} is required and must not be empty.")
        return value.strip()

    @field_validator("llm_api_key", "nextauth_secret")
    @classmethod
    def _required_secret_must_not_be_placeholder(cls, value: str, info):
        if value.strip().lower() in PLACEHOLDER_VALUES:
            raise ValueError(f"{info.field_name.upper()} must be set to a real secret, not an example placeholder.")
        return value

    @field_validator("nextauth_secret")
    @classmethod
    def _nextauth_secret_must_be_strong_enough(cls, value: str):
        if len(value) < 32:
            raise ValueError("NEXTAUTH_SECRET must be at least 32 characters long.")
        return value

    @field_validator("database_url")
    @classmethod
    def _database_url_must_have_scheme(cls, value: str):
        if "://" not in value:
            raise ValueError("DATABASE_URL must include a database URL scheme.")
        return value

    @field_validator("llm_base_url")
    @classmethod
    def _llm_base_url_must_be_http(cls, value: str):
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("LLM_BASE_URL must start with http:// or https://.")
        return value.rstrip("/")

    @field_validator("github_token", "github_owner", mode="before")
    @classmethod
    def _empty_optional_strings_are_none(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("github_token", "github_owner")
    @classmethod
    def _optional_github_values_must_not_be_placeholders(cls, value: str | None, info):
        if value is not None and value.lower() in PLACEHOLDER_VALUES:
            raise ValueError(f"{info.field_name.upper()} must be set to a real value or omitted.")
        return value

    def require_github_config(self) -> tuple[str, str]:
        if not self.github_token or not self.github_owner:
            raise RuntimeError(
                "GitHub MCP tools require GITHUB_TOKEN and GITHUB_OWNER. "
                "Set them only when GitHub verification tools are enabled."
            )
        return self.github_token, self.github_owner

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
