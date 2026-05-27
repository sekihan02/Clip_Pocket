import unittest

from clip_pocket.constants import MAX_PREVIEW_LENGTH

try:
    from clip_pocket.ui import ClipPocketApp
except ModuleNotFoundError as error:
    if error.name != "tkinter":
        raise
    ClipPocketApp = None  # type: ignore[assignment]


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


if __name__ == "__main__":
    unittest.main()
