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
        "https://api.kcisa.kr/openapi/service/rest/convergence2019/getConver02"
    )
    seoul_open_api_key: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    sync_secret: str = "change-me"

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
