import unittest
from unittest.mock import patch

from clip_pocket.startup import build_startup_command


class StartupTest(unittest.TestCase):
    def test_source_startup_command_uses_pythonw_when_available(self) -> None:
        with patch("sys.executable", r"C:\App\.venv\Scripts\python.exe"):
            with patch("pathlib.Path.exists", return_value=True):
                command = build_startup_command()

        self.assertIn("pythonw.exe", command)
        self.assertIn("-m clip_pocket.app --hidden", command)

    def test_frozen_startup_command_uses_current_executable(self) -> None:
        with patch("sys.executable", r"C:\Program Files\ClipPocket\ClipPocket.exe"):
            with patch("sys.frozen", True, create=True):
                command = build_startup_command()

        self.assertIn("ClipPocket.exe", command)
        self.assertIn("--hidden", command)
