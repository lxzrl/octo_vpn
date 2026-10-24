from sqlalchemy.engine import make_url

from app.config import Settings


def test_db_url_escapes_password() -> None:
    settings = Settings(bot_token="1:x", postgres_password="p@ss/w:rd", database_url=None)
    url = make_url(settings.db_url)
    assert url.password == "p@ss/w:rd"
    assert url.host == "postgres" and url.database == "octo"


def test_admin_ids_from_comma_separated_string() -> None:
    assert Settings(bot_token="1:x", admin_ids="1, 2,").admin_ids == {1, 2}


def test_empty_proxy_is_none() -> None:
    assert Settings(bot_token="1:x", telegram_proxy="").telegram_proxy is None
