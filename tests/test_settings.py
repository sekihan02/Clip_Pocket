import tempfile
import unittest
import json
from pathlib import Path

from clip_pocket.settings import AppSettings, load_settings, save_settings


class SettingsTest(unittest.TestCase):
    def test_load_settings_uses_defaults_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = load_settings(Path(directory) / "missing.json")

        self.assertTrue(settings.ctrl_double_tap_enabled)
        self.assertFalse(settings.right_triple_click_enabled)
        self.assertEqual(settings.language, "en")
        self.assertEqual(settings.retention_seconds, 24 * 60 * 60)
        self.assertEqual(settings.max_items, 100)
        self.assertEqual(settings.color_theme, "light")
        self.assertEqual(settings.window_opacity, 1.0)
        self.assertEqual(settings.window_width, 560)
        self.assertEqual(settings.window_height, 360)

    def test_save_and_load_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_settings(
                AppSettings(
                    language="ja",
                    ctrl_double_tap_enabled=False,
                    right_triple_click_enabled=True,
                    retention_seconds=None,
                    max_items=250,
                    color_theme="dark",
                    window_opacity=0.75,
                    window_width=640,
                    window_height=420,
                ),
                path,
            )
            settings = load_settings(path)

        self.assertEqual(settings.language, "ja")
        self.assertFalse(settings.ctrl_double_tap_enabled)
        self.assertTrue(settings.right_triple_click_enabled)
        self.assertIsNone(settings.retention_seconds)
        self.assertEqual(settings.max_items, 250)
        self.assertEqual(settings.color_theme, "dark")
        self.assertEqual(settings.window_opacity, 0.75)
        self.assertEqual(settings.window_width, 640)
        self.assertEqual(settings.window_height, 420)

    def test_load_settings_ignores_non_bool_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps(
                    {
                        "ctrl_double_tap_enabled": "false",
                        "right_triple_click_enabled": "true",
                    }
                ),
                encoding="utf-8",
            )
            settings = load_settings(path)

        self.assertTrue(settings.ctrl_double_tap_enabled)
        self.assertFalse(settings.right_triple_click_enabled)

    def test_load_settings_uses_default_for_non_positive_retention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"retention_seconds": -1}), encoding="utf-8")
            settings = load_settings(path)

        self.assertEqual(settings.retention_seconds, 24 * 60 * 60)

    def test_load_settings_clamps_max_items(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"max_items": 5}), encoding="utf-8")
            low_settings = load_settings(path)

            path.write_text(json.dumps({"max_items": 5000}), encoding="utf-8")
            high_settings = load_settings(path)

        self.assertEqual(low_settings.max_items, 10)
        self.assertEqual(high_settings.max_items, 1000)

    def test_load_settings_normalizes_unknown_language(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"language": "fr"}), encoding="utf-8")
            settings = load_settings(path)

        self.assertEqual(settings.language, "en")

    def test_load_settings_normalizes_visual_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(
                json.dumps({"color_theme": "neon", "window_opacity": 0.2}),
                encoding="utf-8",
            )
            low_settings = load_settings(path)

            path.write_text(json.dumps({"color_theme": "dark", "window_opacity": 2}), encoding="utf-8")
            high_settings = load_settings(path)

            path.write_text(json.dumps({"window_opacity": "not a number"}), encoding="utf-8")
            invalid_settings = load_settings(path)

            path.write_text(json.dumps({"window_opacity": -1}), encoding="utf-8")
            minimum_settings = load_settings(path)

        self.assertEqual(low_settings.color_theme, "light")
        self.assertEqual(low_settings.window_opacity, 0.2)
        self.assertEqual(high_settings.color_theme, "dark")
        self.assertEqual(high_settings.window_opacity, 1.0)
        self.assertEqual(invalid_settings.window_opacity, 1.0)
        self.assertEqual(minimum_settings.window_opacity, 0.0)

    def test_load_settings_normalizes_window_size(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({"window_width": 100, "window_height": 100}), encoding="utf-8")
            low_settings = load_settings(path)

            path.write_text(
                json.dumps({"window_width": 5000, "window_height": 5000}),
                encoding="utf-8",
            )
            high_settings = load_settings(path)

            path.write_text(
                json.dumps({"window_width": "wide", "window_height": "tall"}),
                encoding="utf-8",
            )
            invalid_settings = load_settings(path)

        self.assertEqual(low_settings.window_width, 420)
        self.assertEqual(low_settings.window_height, 280)
        self.assertEqual(high_settings.window_width, 1200)
        self.assertEqual(high_settings.window_height, 900)
        self.assertEqual(invalid_settings.window_width, 560)
        self.assertEqual(invalid_settings.window_height, 360)

    def test_save_settings_replaces_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{broken", encoding="utf-8")

            save_settings(AppSettings(language="ja"), path)

            self.assertFalse(path.with_name("settings.json.tmp").exists())
            self.assertEqual(load_settings(path).language, "ja")


if __name__ == "__main__":
    unittest.main()
