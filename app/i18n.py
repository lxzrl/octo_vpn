from pathlib import Path
from typing import Any

from fluent.runtime import FluentLocalization, FluentResourceLoader

from app.config import LANGUAGES, Language

LOCALES_DIR = Path(__file__).parent / "locales"


class Translator:
    """Тексты бота на одном языке. Вызывается как функция: i18n("menu-profile")."""

    def __init__(self, localization: FluentLocalization, language: Language) -> None:
        self._localization = localization
        self.language = language

    def __call__(self, key: str, **kwargs: Any) -> str:
        return str(self._localization.format_value(key, kwargs or None))


class TranslatorHub:
    def __init__(self, default: Language, locales_dir: Path = LOCALES_DIR) -> None:
        loader = FluentResourceLoader(str(locales_dir / "{locale}"))
        self.default = default
        self._translators = {
            lang: Translator(
                # Фолбэк на язык по умолчанию, если ключа нет в переводе.
                FluentLocalization([lang, default], ["main.ftl"], loader),
                lang,
            )
            for lang in LANGUAGES
        }
        # Админка только на русском: её видят несколько человек, переводить незачем.
        self.admin = Translator(FluentLocalization(["ru"], ["admin.ftl", "main.ftl"], loader), "ru")

    def get(self, language: str | None) -> Translator:
        if language in self._translators:
            return self._translators[language]
        return self._translators[self.default]
