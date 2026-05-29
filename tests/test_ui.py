import unittest

from clip_pocket.constants import MAX_PREVIEW_LENGTH
from clip_pocket.history import ClipboardItem, fingerprint
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
    def make_item(self, text: str, updated_at: float) -> ClipboardItem:
        return ClipboardItem(
            text=text,
            text_hash=fingerprint(text),
            created_at=updated_at,
            updated_at=updated_at,
        )

    def test_preview_limits_work_before_joining_lines(self) -> None:
        text = ("line\n" * 1_000) + "tail"

        preview = ClipPocketApp._preview(text)

        self.assertLessEqual(len(preview), MAX_PREVIEW_LENGTH)
        self.assertTrue(preview.endswith("..."))

    def test_preview_collapses_whitespace_to_one_line(self) -> None:
        preview = ClipPocketApp._preview("first line\r\n\tsecond   line")

        self.assertEqual(preview, "first line second line")

    def test_history_view_filters_case_insensitively(self) -> None:
        items = [
            self.make_item("Banana", 1),
            self.make_item("Apple", 3),
            self.make_item("apricot", 2),
        ]

        indices = ClipPocketApp._history_indices_for_view(items, "AP", "updated_desc")

        self.assertEqual(indices, [1, 2])

    def test_history_view_filters_across_line_breaks(self) -> None:
        items = [
            self.make_item("first line\nsecond line", 1),
            self.make_item("other text", 2),
        ]

        indices = ClipPocketApp._history_indices_for_view(items, "line second", "updated_desc")

        self.assertEqual(indices, [0])

    def test_history_view_sorts_by_text(self) -> None:
        items = [
            self.make_item("Banana", 1),
            self.make_item("Apple", 3),
            self.make_item("apricot", 2),
        ]

        indices = ClipPocketApp._history_indices_for_view(items, "", "text_asc")

        self.assertEqual(indices, [1, 2, 0])

    def test_history_view_sorts_by_oldest_first(self) -> None:
        items = [
            self.make_item("first", 20),
            self.make_item("second", 10),
            self.make_item("third", 30),
        ]

        indices = ClipPocketApp._history_indices_for_view(items, "", "updated_asc")

        self.assertEqual(indices, [1, 0, 2])

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

    def test_win32_point_inside_tk_bounds_is_not_remapped(self) -> None:
        class FakeRoot:
            def winfo_vrootx(self) -> int:
                return 0

            def winfo_vrooty(self) -> int:
                return 0

            def winfo_vrootwidth(self) -> int:
                return 3840

            def winfo_vrootheight(self) -> int:
                return 2160

        app = object.__new__(ClipPocketApp)
        app.root = FakeRoot()
        app._win32_virtual_screen_bounds = lambda: (0, 0, 3840, 2160)

        point = ClipPocketApp._convert_win32_point_to_tk_coordinates(app, 3000, 1500)

        self.assertEqual(point, (3000, 1500))

    def test_win32_point_outside_tk_bounds_falls_back_to_mapping(self) -> None:
        class FakeRoot:
            def winfo_vrootx(self) -> int:
                return 0

            def winfo_vrooty(self) -> int:
                return 0

            def winfo_vrootwidth(self) -> int:
                return 2560

            def winfo_vrootheight(self) -> int:
                return 1440

        app = object.__new__(ClipPocketApp)
        app.root = FakeRoot()
        app._win32_virtual_screen_bounds = lambda: (0, 0, 3840, 2160)

        point = ClipPocketApp._convert_win32_point_to_tk_coordinates(app, 3000, 1500)

        self.assertEqual(point, (2000, 1000))

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
