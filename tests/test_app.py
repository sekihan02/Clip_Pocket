import sys
import unittest

from clip_pocket.app import main


class AppTest(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "Windows starts the desktop app.")
    def test_non_windows_exits_before_importing_desktop_ui(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main([])

        self.assertIn("Windows-only", str(context.exception))


if __name__ == "__main__":
    unittest.main()
