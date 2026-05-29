import sys
import unittest

from clip_pocket.app import main, parse_args


class AppTest(unittest.TestCase):
    def test_show_and_hidden_are_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit) as context:
            parse_args(["--show", "--hidden"])

        self.assertEqual(context.exception.code, 2)

    def test_startup_actions_are_mutually_exclusive(self) -> None:
        with self.assertRaises(SystemExit) as context:
            parse_args(["--install-startup", "--uninstall-startup"])

        self.assertEqual(context.exception.code, 2)

    def test_startup_actions_reject_launch_visibility_options(self) -> None:
        with self.assertRaises(SystemExit) as context:
            parse_args(["--install-startup", "--hidden"])

        self.assertEqual(context.exception.code, 2)

    def test_show_option_sets_show_flag(self) -> None:
        args = parse_args(["--show"])

        self.assertTrue(args.show)
        self.assertFalse(args.hidden)

    @unittest.skipIf(sys.platform == "win32", "Windows starts the desktop app.")
    def test_non_windows_exits_before_importing_desktop_ui(self) -> None:
        with self.assertRaises(SystemExit) as context:
            main([])

        self.assertIn("Windows-only", str(context.exception))


if __name__ == "__main__":
    unittest.main()
