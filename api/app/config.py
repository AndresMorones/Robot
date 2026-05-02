"""Application settings loaded from environment / .env file.

All secrets injected via env vars (never committed). For local dev: .env in api/.
For production: Fly secrets (`fly secrets set ...`).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_bearer_token: str = "dev-token-change-me"

    loads_csv_path: str = "../data/loads.csv"
    calls_json_path: str = "../data/calls.json"

    hr_base_url: str = "https://platform.happyrobot.ai/api/v2"
    happyrobot_api_key: str = ""
    # HR workflow id for the active-call Monitor API proxy (/v1/calls/active).
    # Empty = endpoint reports status="unconfigured" without contacting HR.
    hr_workflow_id: str = ""

    log_level: str = "INFO"


settings = Settings()
