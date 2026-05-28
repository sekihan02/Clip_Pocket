from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from clip_pocket.constants import MAX_ITEMS, RETENTION_SECONDS
from clip_pocket.i18n import normalize_language


MIN_MAX_ITEMS = 10
MAX_MAX_ITEMS = 1000
SUPPORTED_COLOR_THEMES = ("light", "dark")
DEFAULT_COLOR_THEME = "light"
DEFAULT_WINDOW_OPACITY = 1.0
MIN_WINDOW_OPACITY = 0.0
MAX_WINDOW_OPACITY = 1.0


def normalize_max_items(value: object) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return MAX_ITEMS
    return min(max(number, MIN_MAX_ITEMS), MAX_MAX_ITEMS)


def normalize_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    return default


def normalize_retention_seconds(value: object) -> int | None:
    if value is None:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return RETENTION_SECONDS
    if number <= 0:
        return RETENTION_SECONDS
    return number


def normalize_color_theme(value: object) -> str:
    if isinstance(value, str) and value in SUPPORTED_COLOR_THEMES:
        return value
    return DEFAULT_COLOR_THEME


def normalize_window_opacity(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return DEFAULT_WINDOW_OPACITY
    if not math.isfinite(number):
        return DEFAULT_WINDOW_OPACITY
    return min(max(number, MIN_WINDOW_OPACITY), MAX_WINDOW_OPACITY)


@dataclass
class AppSettings:
    language: str = "en"
    ctrl_double_tap_enabled: bool = True
    right_triple_click_enabled: bool = False
    retention_seconds: int | None = RETENTION_SECONDS
    max_items: int = MAX_ITEMS
    color_theme: str = DEFAULT_COLOR_THEME
    window_opacity: float = DEFAULT_WINDOW_OPACITY

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> AppSettings:
        return cls(
            language=normalize_language(str(value.get("language", "en"))),
            ctrl_double_tap_enabled=normalize_bool(
                value.get("ctrl_double_tap_enabled"),
                True,
            ),
            right_triple_click_enabled=normalize_bool(
                value.get("right_triple_click_enabled"),
                False,
            ),
            retention_seconds=normalize_retention_seconds(
                value.get("retention_seconds", RETENTION_SECONDS)
            ),
            max_items=normalize_max_items(value.get("max_items", MAX_ITEMS)),
            color_theme=normalize_color_theme(value.get("color_theme", DEFAULT_COLOR_THEME)),
            window_opacity=normalize_window_opacity(
                value.get("window_opacity", DEFAULT_WINDOW_OPACITY)
            ),
        )


def settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "ClipPocket" / "settings.json"
    return Path.home() / ".clip-pocket" / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or settings_path()
    try:
        with target.open("r", encoding="utf-8") as file:
            value = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppSettings()

    if not isinstance(value, dict):
        return AppSettings()
    return AppSettings.from_mapping(value)


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp")
    with temporary.open("w", encoding="utf-8") as file:
        json.dump(asdict(settings), file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary.replace(target)
