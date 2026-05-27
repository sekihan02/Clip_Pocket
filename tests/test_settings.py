import tempfile
import unittest
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
                ),
                path,
            )
            settings = load_settings(path)

        self.assertEqual(settings.language, "ja")
        self.assertFalse(settings.ctrl_double_tap_enabled)
        self.assertTrue(settings.right_triple_click_enabled)
        self.assertIsNone(settings.retention_seconds)
        self.assertEqual(settings.max_items, 250)


if __name__ == "__main__":
    unittest.main()
