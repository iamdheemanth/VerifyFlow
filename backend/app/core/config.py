from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_judge_model: str
    github_token: str
    github_owner: str
    max_retries: int
    verification_confidence_threshold: float

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
