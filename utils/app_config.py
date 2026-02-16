from __future__ import annotations

import configparser
import os
import sys
from functools import lru_cache
from pathlib import Path

DEFAULT_CONFIG_ENV_VAR = "SFERA_KANBAN_CONFIG"
DEFAULT_CONFIG_RELATIVE_PATH = Path("config") / "app.ini"


class AppConfigError(RuntimeError):
    """Raised when application configuration is missing or invalid."""


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resolve_config_path() -> Path:
    env_path = os.getenv(DEFAULT_CONFIG_ENV_VAR)
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (_base_dir() / DEFAULT_CONFIG_RELATIVE_PATH).resolve()


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_config() -> configparser.ConfigParser:
    config_path = resolve_config_path()
    if not config_path.exists():
        raise AppConfigError(
            f"Файл конфигурации не найден: {config_path}. "
            "Создайте его на основе config/app.ini.example."
        )

    parser = configparser.ConfigParser()
    parser.read(config_path, encoding="utf-8")

    required_sections = ["app", "sfera", "ordering"]
    missing_sections = [section for section in required_sections if not parser.has_section(section)]
    if missing_sections:
        raise AppConfigError(
            "В конфигурации отсутствуют разделы: " + ", ".join(missing_sections)
        )

    return parser


def _get_required(parser: configparser.ConfigParser, section: str, option: str) -> str:
    value = parser.get(section, option, fallback="").strip()
    if not value:
        raise AppConfigError(f"Пустое обязательное поле: [{section}] {option}")
    return value


CONFIG = get_config()

DEFAULT_AREA = _get_required(CONFIG, "app", "default_area")
AVAILABLE_AREAS = _split_csv(_get_required(CONFIG, "app", "available_areas"))

if DEFAULT_AREA not in AVAILABLE_AREAS:
    raise AppConfigError(
        "Значение [app] default_area должно входить в [app] available_areas"
    )

APP_HOST = CONFIG.get("app", "host", fallback="127.0.0.1").strip() or "127.0.0.1"
APP_PORT = CONFIG.getint("app", "port", fallback=5000)
APP_DEBUG = CONFIG.getboolean("app", "debug", fallback=False)

SFERA_BASE_URL = _get_required(CONFIG, "sfera", "base_url")
SFERA_USERNAME = _get_required(CONFIG, "sfera", "username")
SFERA_PASSWORD = _get_required(CONFIG, "sfera", "password")
REQUEST_TIMEOUT_SECONDS = CONFIG.getint("sfera", "request_timeout_seconds", fallback=30)
REQUEST_RETRIES = CONFIG.getint("sfera", "request_retries", fallback=3)
RETRY_SLEEP_SECONDS = CONFIG.getint("sfera", "retry_sleep_seconds", fallback=2)

ASSIGNEE_ORDER = _split_csv(CONFIG.get("ordering", "assignee_order", fallback=""))
SYSTEM_ORDER = _split_csv(CONFIG.get("ordering", "system_order", fallback=""))
