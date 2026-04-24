"""Application settings loaded from environment / .env file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_bearer_token: str = "dev-token-change-me"
    loads_json_path: str = "../data/loads.json"
    fmcsa_web_key: str = ""  # WS2b will use this


settings = Settings()
