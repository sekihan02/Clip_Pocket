import unittest

from clip_pocket.win32_host import is_double_ctrl_tap, next_click_sequence_count, tray_event_from_lparam


class Win32HostTest(unittest.TestCase):
    def test_double_ctrl_tap_matches_within_interval(self) -> None:
        self.assertTrue(is_double_ctrl_tap(100, 300))

    def test_double_ctrl_tap_rejects_slow_taps(self) -> None:
        self.assertFalse(is_double_ctrl_tap(100, 700))

    def test_double_ctrl_tap_rejects_zero_elapsed_time(self) -> None:
        self.assertFalse(is_double_ctrl_tap(100, 100))

    def test_double_ctrl_tap_handles_tick_count_rollover(self) -> None:
        self.assertTrue(is_double_ctrl_tap((2**32) - 100, 50))

    def test_click_sequence_counts_nearby_clicks_within_interval(self) -> None:
        first = next_click_sequence_count(0, None, None, 100, (10, 10))
        second = next_click_sequence_count(first, 100, (10, 10), 300, (16, 18))
        third = next_click_sequence_count(second, 300, (16, 18), 500, (14, 16))

        self.assertEqual(first, 1)
        self.assertEqual(second, 2)
        self.assertEqual(third, 3)

    def test_click_sequence_restarts_on_slow_or_distant_click(self) -> None:
        self.assertEqual(next_click_sequence_count(2, 100, (10, 10), 900, (10, 10)), 1)
        self.assertEqual(next_click_sequence_count(2, 100, (10, 10), 300, (40, 10)), 1)

    def test_tray_event_from_lparam_uses_low_word(self) -> None:
        self.assertEqual(tray_event_from_lparam(0x0001_007B), 0x007B)
        self.assertEqual(tray_event_from_lparam(-0xFFFF_FF85), 0x007B)


if __name__ == "__main__":
    unittest.main()
