import re
from pathlib import Path

from app.config import LANGUAGES
from app.i18n import LOCALES_DIR, TranslatorHub

KEY = re.compile(r"^([a-z][a-z0-9-]*)\s*=", re.MULTILINE)


def keys(path: Path) -> set[str]:
    return set(KEY.findall(path.read_text(encoding="utf-8")))


def test_all_locales_have_same_keys() -> None:
    reference = keys(LOCALES_DIR / "ru" / "main.ftl")
    for lang in LANGUAGES:
        assert keys(LOCALES_DIR / lang / "main.ftl") == reference, lang


def test_translate_with_args() -> None:
    hub = TranslatorHub("ru")
    assert "Alice" in hub.get("en")("main-menu", name="Alice")
    assert hub.get("en")("btn-back") == "⬅️ Back"


def test_unknown_language_falls_back_to_default() -> None:
    hub = TranslatorHub("ru")
    assert hub.get("de").language == "ru"
    assert hub.get(None).language == "ru"
