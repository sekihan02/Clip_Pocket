import unittest

from clip_pocket.constants import MAX_PREVIEW_LENGTH
from clip_pocket.settings import AppSettings

try:
    from clip_pocket.ui import ClipPocketApp, scrollbar_thumb_bounds
except ModuleNotFoundError as error:
    if error.name != "tkinter":
        raise
    ClipPocketApp = None  # type: ignore[assignment]
    scrollbar_thumb_bounds = None  # type: ignore[assignment]


@unittest.skipIf(ClipPocketApp is None, "tkinter is not available")
class UiHelpersTest(unittest.TestCase):
    def test_preview_limits_work_before_joining_lines(self) -> None:
        text = ("line\n" * 1_000) + "tail"

        preview = ClipPocketApp._preview(text)

        self.assertLessEqual(len(preview), MAX_PREVIEW_LENGTH)
        self.assertTrue(preview.endswith("..."))

    def test_window_origin_is_clamped_inside_screen_bounds(self) -> None:
        left, top = ClipPocketApp._clamp_window_origin(
            1900,
            1060,
            760,
            480,
            0,
            0,
            1920,
            1080,
        )

        self.assertEqual(left, 1152)
        self.assertEqual(top, 592)

    def test_win32_point_is_mapped_to_tk_coordinate_bounds(self) -> None:
        point = ClipPocketApp._map_point_between_bounds(
            3000,
            1500,
            (0, 0, 3840, 2160),
            (0, 0, 2560, 1440),
        )

        self.assertEqual(point, (2000, 1000))

    def test_point_mapping_rejects_empty_bounds(self) -> None:
        point = ClipPocketApp._map_point_between_bounds(
            100,
            100,
            (0, 0, 0, 1080),
            (0, 0, 1920, 1080),
        )

        self.assertIsNone(point)

    def test_point_moved_uses_tolerance(self) -> None:
        self.assertFalse(ClipPocketApp._point_moved((100, 100), (102, 103), 3))
        self.assertTrue(ClipPocketApp._point_moved((100, 100), (104, 103), 3))

    def test_auto_hide_bounds_include_margin(self) -> None:
        bounds = (100, 100, 300, 200)

        self.assertFalse(ClipPocketApp._point_is_outside_bounds(105, 95, bounds, 10))
        self.assertFalse(ClipPocketApp._point_is_outside_bounds(405, 305, bounds, 10))
        self.assertTrue(ClipPocketApp._point_is_outside_bounds(105, 89, bounds, 10))
        self.assertTrue(ClipPocketApp._point_is_outside_bounds(411, 305, bounds, 10))

    def test_scrollbar_thumb_bounds_use_visible_fraction(self) -> None:
        top, bottom = scrollbar_thumb_bounds(0.25, 0.5, 200)

        self.assertEqual((top, bottom), (51, 99))

    def test_scrollbar_thumb_bounds_keep_minimum_size(self) -> None:
        top, bottom = scrollbar_thumb_bounds(0.9, 0.91, 200)

        self.assertEqual(bottom - top, 32)
        self.assertLessEqual(bottom, 197)

    def test_position_uses_saved_window_size(self) -> None:
        class FakeRoot:
            geometry_value = ""

            def winfo_vrootx(self) -> int:
                return 0

            def winfo_vrooty(self) -> int:
                return 0

            def winfo_vrootwidth(self) -> int:
                return 1920

            def winfo_vrootheight(self) -> int:
                return 1080

            def geometry(self, value: str) -> None:
                self.geometry_value = value

        fake_root = FakeRoot()
        app = object.__new__(ClipPocketApp)
        app.root = fake_root
        app.settings = AppSettings(window_width=640, window_height=420)
        app._window_anchor_point = lambda _x, _y: (100, 100)

        ClipPocketApp._position_near_pointer(app, None, None)

        self.assertTrue(fake_root.geometry_value.startswith("640x420+"))


if __name__ == "__main__":
    unittest.main()
