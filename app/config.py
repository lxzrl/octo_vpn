from functools import lru_cache
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

Language = Literal["ru", "en"]
LANGUAGES: tuple[Language, ...] = ("ru", "en")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: SecretStr
    admin_ids: Annotated[frozenset[int], NoDecode] = frozenset()

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "octo"
    postgres_password: SecretStr = SecretStr("")
    postgres_db: str = "octo"
    # Полный URL перекрывает postgres_* (удобно для тестов и локального запуска).
    database_url: str | None = None

    redis_url: str = "redis://redis:6379/0"

    default_language: Language = "ru"
    log_level: str = "INFO"

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_admin_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return frozenset(int(part) for part in value.split(",") if part.strip())
        if isinstance(value, int):
            return frozenset({value})
        return value

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return URL.create(
            "postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
