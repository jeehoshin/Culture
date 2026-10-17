from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    app_env: str = "development"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    use_fixture_data: bool = True
    kopis_api_key: str | None = None
    culture_portal_api_key: str | None = None
    culture_portal_api_url: str = (
        "https://api.kcisa.kr/openapi/API_CCA_145/request"
    )
    seoul_open_api_key: str | None = None
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None
    supabase_service_role_key: str | None = None
    sync_secret: str = "change-me"
    sync_kopis_enabled: bool = True
    sync_culture_portal_enabled: bool = True
    culture_portal_max_pages: int = 100
    supabase_fetch_limit: int = 5000

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def supabase_server_key(self) -> str | None:
        return self.supabase_secret_key or self.supabase_service_role_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
