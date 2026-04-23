from __future__ import annotations

import configparser
import os
import sys
from functools import lru_cache
from pathlib import Path

DEFAULT_CONFIG_ENV_VAR = "SFERA_KANBAN_CONFIG"
DEFAULT_CONFIG_RELATIVE_PATH = Path("config") / "app.ini"
EXAMPLE_CONFIG_RELATIVE_PATH = Path("config") / "app.ini.example"

class AppConfigError(RuntimeError):
    """Raised when application configuration is missing or invalid."""


def _run_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _bundle_dir() -> Path | None:
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass).resolve() if meipass else None


def _existing(path: Path) -> Path | None:
    return path.resolve() if path.exists() else None


def resolve_config_path() -> Path:
    env_path = os.getenv(DEFAULT_CONFIG_ENV_VAR)
    if env_path:
        resolved = Path(env_path).expanduser().resolve()
        if resolved.exists():
            return resolved
        raise AppConfigError(f"Файл из {DEFAULT_CONFIG_ENV_VAR} не найден: {resolved}")

    candidates: list[Path] = [
        _run_dir() / DEFAULT_CONFIG_RELATIVE_PATH,
        _run_dir() / EXAMPLE_CONFIG_RELATIVE_PATH,
    ]

    bundle = _bundle_dir()
    if bundle:
        candidates.extend([
            bundle / DEFAULT_CONFIG_RELATIVE_PATH,
            bundle / EXAMPLE_CONFIG_RELATIVE_PATH,
        ])

    for candidate in candidates:
        resolved = _existing(candidate)
        if resolved:
            return resolved

    raise AppConfigError(
        "Не найден файл конфигурации. Ожидается config/app.ini рядом с приложением "
        f"или путь через {DEFAULT_CONFIG_ENV_VAR}."
    )


def _split_csv(raw_value: str) -> list[str]:
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_config() -> configparser.ConfigParser:
    config_path = resolve_config_path()
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(config_path, encoding="utf-8")

    required_sections = ["app", "sfera", "ordering"]
    missing_sections = [section for section in required_sections if not parser.has_section(section)]
    if missing_sections:
        raise AppConfigError("В конфигурации отсутствуют разделы: " + ", ".join(missing_sections))

    return parser


def _get_required(parser: configparser.ConfigParser, section: str, option: str) -> str:
    value = parser.get(section, option, fallback="").strip()
    if not value:
        raise AppConfigError(f"Пустое обязательное поле: [{section}] {option}")
    return value


def _resource_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

RESOURCE_DIR = _resource_dir()


CONFIG = get_config()

DEFAULT_AREA = _get_required(CONFIG, "app", "default_area")
AVAILABLE_AREAS = _split_csv(_get_required(CONFIG, "app", "available_areas"))

if DEFAULT_AREA not in AVAILABLE_AREAS:
    raise AppConfigError("Значение [app] default_area должно входить в [app] available_areas")

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
PROJECTS_ORDER = _split_csv(CONFIG.get("ordering", "project_order", fallback=""))
CACHE_PROJECTS_ENABLED = CONFIG.getboolean("app", "cache_projects", fallback=True)