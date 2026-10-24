from decimal import Decimal
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

    # Панель Remnawave: адрес панели и API-токен (Настройки → API-токены).
    remnawave_url: str = "https://panel.example.com"
    remnawave_token: SecretStr = SecretStr("")
    # Ключ Caddy, если панель закрыта Caddy с авторизацией по X-Api-Key.
    remnawave_caddy_token: SecretStr | None = None
    # Сквады, в которые добавляется пользователь. Пусто = все сквады панели.
    remnawave_squads: Annotated[tuple[str, ...], NoDecode] = ()

    # Значения ниже — начальные: админ может поменять их в боте (раздел «Настройки»).
    trial_days: int = 3
    # Канал, подписка на который нужна для пробного периода: @username или -100…
    # Пусто = проверка выключена.
    trial_channel: str | None = None
    # Ссылка на канал для кнопки; для @username строится автоматически.
    trial_channel_url: str | None = None

    # Сколько рублей стоит одна звезда Telegram: цена в Stars = цена в рублях / курс,
    # с округлением вверх.
    stars_rub_rate: Decimal = Decimal("1.5")
    # Неоплаченный счёт отменяется через столько минут, зарезервированный баланс возвращается.
    payment_ttl_minutes: int = 60

    # Реферальные начисления: процент от реально оплаченной суммы покупки друга.
    referral_first_percent: int = 20
    referral_next_percent: int = 10

    # Часовой пояс, в котором пользователям показываются даты.
    display_timezone: str = "Europe/Moscow"
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

    @field_validator("remnawave_squads", mode="before")
    @classmethod
    def _split_squads(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        return value

    @field_validator("trial_channel", "trial_channel_url", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        return value or None

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
