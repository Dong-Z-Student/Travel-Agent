from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    api_prefix: str = "/api"
    project_name: str = "Travel Agent API"

    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""
    amap_web_service_key: str = ""

    agent_mode: str = "orchestrator"
    agent_timeout_seconds: int = 60
    agent_max_retries: int = 2
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_fast_model: str = "deepseek-v4-flash"
    deepseek_planner_model: str = "deepseek-v4-pro"
    agent_default_model: str = "deepseek-v4-flash"
    agent_complex_model: str = "deepseek-v4-pro"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    cors_origin_regex: str | None = r"https?://(localhost|127\.0\.0\.1):\d+"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
