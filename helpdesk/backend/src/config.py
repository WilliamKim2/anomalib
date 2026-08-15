from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HELPDESK_")

    database_url: str = "sqlite+aiosqlite:///./helpdesk.db"


settings = Settings()
