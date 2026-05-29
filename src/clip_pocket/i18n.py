from __future__ import annotations


SUPPORTED_LANGUAGES = ("en", "ja")

LANGUAGE_NAMES = {
    "en": "English",
    "ja": "日本語",
}

TEXT = {
    "en": {
        "app_settings": "Clip Pocket Settings",
        "restore": "Restore to clipboard",
        "delete": "Delete",
        "search": "Search",
        "clear_search": "Clear",
        "sort": "Sort",
        "keep_open": "Keep window open",
        "count": "{count} items",
        "count_filtered": "{shown} of {count} items",
        "status_ready": "Resident. Press Ctrl twice or use the notification-area icon to open.",
        "status_duplicate": "Updated the existing item.",
        "status_added": "Copied text added.",
        "status_restore_failed": "Could not restore the item to the clipboard.",
        "status_restored": "Restored to the clipboard. Paste it with Ctrl+V.",
        "status_deleted": "Deleted the selected item.",
        "status_startup_failed": "Could not change the startup setting.",
        "status_startup_enabled": "Clip Pocket will start when Windows starts.",
        "status_startup_disabled": "Clip Pocket will not start when Windows starts.",
        "status_pinned": "The window will stay open.",
        "status_unpinned": "The window will auto-hide.",
        "status_settings_failed": "Could not save settings.",
        "status_settings_saved": "Settings saved.",
        "status_expired": "Expired items removed.",
        "status_paused": "Clipboard monitoring paused.",
        "status_resumed": "Clipboard monitoring resumed.",
        "status_window_visible": "Resident. The window auto-hides when unpinned.",
        "remaining": "{preview}    | about {minutes} min left",
        "remaining_unlimited": "{preview}    | no expiration",
        "monitoring_active": "Monitoring: Active",
        "monitoring_paused": "Monitoring: Paused",
        "settings_title": "Settings",
        "language": "Language",
        "startup": "Start when Windows starts",
        "ctrl_double_tap": "Open with Ctrl double-tap",
        "right_triple_click": "Open with right-click triple-click (experimental)",
        "right_triple_click_hint": "May conflict with normal context menus. Keep it off unless you need it.",
        "color_theme": "Color",
        "opacity": "Opacity",
        "opacity_value": "{percent}%",
        "font_size": "Font size",
        "window_width": "Window width",
        "window_height": "Window height",
        "retention": "Delete copied items after",
        "max_items": "Maximum copied items",
        "apply": "Apply",
        "exit_app": "Quit Clip Pocket",
        "close": "Close",
        "menu_open": "Open",
        "menu_settings": "Settings",
        "menu_pause": "Pause monitoring",
        "menu_resume": "Resume monitoring",
        "menu_exit": "Quit",
        "warning_ctrl_hook": "Could not start Ctrl double-tap detection.",
        "warning_mouse_hook": "Could not start right-click triple-click detection.",
        "warning_tray_icon": "Could not add the notification-area icon.",
        "warning_windows_host": "Could not create the Windows resident host.",
        "warning_clipboard_listener": "Could not start clipboard monitoring.",
    },
    "ja": {
        "app_settings": "Clip Pocket 設定",
        "restore": "クリップボードに戻す",
        "delete": "削除",
        "search": "検索",
        "clear_search": "クリア",
        "sort": "並び替え",
        "keep_open": "ウィンドウを固定",
        "count": "{count}件",
        "count_filtered": "{shown}/{count}件",
        "status_ready": "常駐中です。Ctrl二回、または通知領域アイコンから開けます。",
        "status_duplicate": "同じ内容の保存期限を更新しました",
        "status_added": "コピー内容を追加しました",
        "status_restore_failed": "クリップボードに戻せませんでした",
        "status_restored": "クリップボードに戻しました。貼り付け先で Ctrl+V してください。",
        "status_deleted": "選択した項目を削除しました",
        "status_startup_failed": "自動起動の設定を変更できませんでした",
        "status_startup_enabled": "Windows起動時に自動起動します",
        "status_startup_disabled": "Windows起動時の自動起動を解除しました",
        "status_pinned": "ウィンドウを開いたままにします",
        "status_unpinned": "枠外に出ると自動で隠れます",
        "status_settings_failed": "設定を保存できませんでした",
        "status_settings_saved": "設定を保存しました",
        "status_expired": "期限切れの項目を削除しました",
        "status_paused": "クリップボード監視を一時停止しました。",
        "status_resumed": "クリップボード監視を再開しました。",
        "status_window_visible": "常駐中です。固定していない場合は枠外で隠れます。",
        "remaining": "{preview}    | 残り約{minutes}分",
        "remaining_unlimited": "{preview}    | 無期限",
        "monitoring_active": "監視: 有効",
        "monitoring_paused": "監視: 一時停止中",
        "settings_title": "設定",
        "language": "言語",
        "startup": "Windowsログイン時に自動起動する",
        "ctrl_double_tap": "Ctrl二回で開く",
        "right_triple_click": "右クリック三回で開く（実験）",
        "right_triple_click_hint": "通常の右クリックメニューと競合する場合があります。必要な場合だけ有効にしてください。",
        "color_theme": "色",
        "opacity": "透過率",
        "opacity_value": "{percent}%",
        "font_size": "文字サイズ",
        "window_width": "ウィンドウ幅",
        "window_height": "ウィンドウ高さ",
        "retention": "コピーの削除までの期間",
        "max_items": "保存するコピー数",
        "apply": "適用",
        "exit_app": "Clip Pocketを終了",
        "close": "閉じる",
        "menu_open": "開く",
        "menu_settings": "設定",
        "menu_pause": "監視を一時停止",
        "menu_resume": "監視を再開",
        "menu_exit": "終了",
        "warning_ctrl_hook": "Ctrl二回の検知を開始できませんでした。",
        "warning_mouse_hook": "右クリック三回の検知を開始できませんでした。",
        "warning_tray_icon": "通知領域アイコンを追加できませんでした。",
        "warning_windows_host": "Windows常駐ホストを作成できませんでした。",
        "warning_clipboard_listener": "クリップボード監視を開始できませんでした。",
    },
}

RETENTION_OPTIONS = [
    ("1h", {"en": "1 hour", "ja": "1時間"}, 60 * 60),
    ("6h", {"en": "6 hours", "ja": "6時間"}, 6 * 60 * 60),
    ("24h", {"en": "24 hours", "ja": "24時間"}, 24 * 60 * 60),
    ("7d", {"en": "7 days", "ja": "7日"}, 7 * 24 * 60 * 60),
    ("30d", {"en": "30 days", "ja": "30日"}, 30 * 24 * 60 * 60),
    ("unlimited", {"en": "Unlimited", "ja": "無制限"}, None),
]

COLOR_THEME_OPTIONS = [
    ("light", {"en": "White", "ja": "白"}),
    ("dark", {"en": "Black", "ja": "黒"}),
]

SORT_OPTIONS = [
    ("updated_desc", {"en": "Newest first", "ja": "新しい順"}),
    ("updated_asc", {"en": "Oldest first", "ja": "古い順"}),
    ("text_asc", {"en": "Text A-Z", "ja": "文字 A-Z"}),
    ("text_desc", {"en": "Text Z-A", "ja": "文字 Z-A"}),
]


def normalize_language(language: str) -> str:
    return language if language in SUPPORTED_LANGUAGES else "en"


def text(language: str, key: str, **values: object) -> str:
    normalized = normalize_language(language)
    template = TEXT[normalized].get(key, TEXT["en"][key])
    return template.format(**values)


def retention_key_from_seconds(seconds: int | None) -> str:
    for key, _labels, value in RETENTION_OPTIONS:
        if value == seconds:
            return key
    return "24h"


def retention_seconds_from_key(key: str) -> int | None:
    for option_key, _labels, value in RETENTION_OPTIONS:
        if option_key == key:
            return value
    return 24 * 60 * 60


def retention_label(language: str, key: str) -> str:
    normalized = normalize_language(language)
    for option_key, labels, _value in RETENTION_OPTIONS:
        if option_key == key:
            return labels[normalized]
    return RETENTION_OPTIONS[2][1][normalized]


def retention_labels(language: str) -> list[str]:
    normalized = normalize_language(language)
    return [labels[normalized] for _key, labels, _value in RETENTION_OPTIONS]


def retention_key_from_label(language: str, label: str) -> str:
    normalized = normalize_language(language)
    for key, labels, _value in RETENTION_OPTIONS:
        if labels[normalized] == label:
            return key
    return "24h"


def color_theme_label(language: str, key: str) -> str:
    normalized = normalize_language(language)
    for option_key, labels in COLOR_THEME_OPTIONS:
        if option_key == key:
            return labels[normalized]
    return COLOR_THEME_OPTIONS[0][1][normalized]


def color_theme_labels(language: str) -> list[str]:
    normalized = normalize_language(language)
    return [labels[normalized] for _key, labels in COLOR_THEME_OPTIONS]


def color_theme_key_from_label(language: str, label: str) -> str:
    normalized = normalize_language(language)
    for key, labels in COLOR_THEME_OPTIONS:
        if labels[normalized] == label:
            return key
    return "light"


def sort_label(language: str, key: str) -> str:
    normalized = normalize_language(language)
    for option_key, labels in SORT_OPTIONS:
        if option_key == key:
            return labels[normalized]
    return SORT_OPTIONS[0][1][normalized]


def sort_labels(language: str) -> list[str]:
    normalized = normalize_language(language)
    return [labels[normalized] for _key, labels in SORT_OPTIONS]


def sort_key_from_label(language: str, label: str) -> str:
    normalized = normalize_language(language)
    for key, labels in SORT_OPTIONS:
        if labels[normalized] == label:
            return key
    return "updated_desc"
