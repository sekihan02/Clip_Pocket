from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from clip_pocket.constants import APP_NAME

if sys.platform == "win32":
    import winreg
else:
    winreg = None


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "ClipPocket"


def build_startup_command() -> str:
    if getattr(sys, "frozen", False):
        parts = [sys.executable, "--hidden"]
    else:
        executable = Path(sys.executable)
        pythonw = executable.with_name("pythonw.exe")
        parts = [
            str(pythonw if pythonw.exists() else executable),
            "-m",
            "clip_pocket.app",
            "--hidden",
        ]

    return subprocess.list2cmdline(parts)


def is_startup_enabled() -> bool:
    if winreg is None:
        return False

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False


def enable_startup() -> None:
    if winreg is None:
        raise RuntimeError(f"{APP_NAME} startup registration is only available on Windows.")

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
        winreg.SetValueEx(
            key,
            RUN_VALUE_NAME,
            0,
            winreg.REG_SZ,
            build_startup_command(),
        )


def disable_startup() -> None:
    if winreg is None:
        return

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        return


def set_startup_enabled(enabled: bool) -> None:
    if enabled:
        enable_startup()
    else:
        disable_startup()
