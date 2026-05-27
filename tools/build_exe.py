from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = PROJECT_ROOT / "src" / "clip_pocket" / "app.py"
ICON_PATH = PROJECT_ROOT / "src" / "clip_pocket" / "assets" / "clip-pocket.ico"
DIST_ROOT = PROJECT_ROOT / "dist"
DIST_DIR = DIST_ROOT / "windows"
WORK_DIR = PROJECT_ROOT / "build" / "pyinstaller"
APP_NAME = "ClipPocket"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows executable.")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="build a single executable instead of the default one-folder bundle",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="remove previous PyInstaller build output before building",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="build a console executable for debugging startup errors",
    )
    args = parser.parse_args()

    if sys.platform != "win32":
        print("Executable builds must run on Windows.", file=sys.stderr)
        return 2

    if args.clean:
        if not remove_tree(DIST_DIR):
            return 1
        if not remove_tree(WORK_DIR):
            return 1

    try:
        import PyInstaller.__main__
    except ModuleNotFoundError:
        print(
            "PyInstaller is not installed. Run: uv sync --extra build",
            file=sys.stderr,
        )
        return 2

    mode = "--onefile" if args.onefile else "--onedir"
    command = [
        str(ENTRYPOINT),
        "--name",
        APP_NAME,
        mode,
        "--clean",
        "--noconfirm",
        "--noupx",
        "--paths",
        str(PROJECT_ROOT / "src"),
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(WORK_DIR),
        "--specpath",
        str(WORK_DIR),
        "--hidden-import",
        "clip_pocket.ui",
        "--hidden-import",
        "clip_pocket.win32_host",
    ]
    if ICON_PATH.exists():
        command.extend(["--icon", str(ICON_PATH)])
        command.extend(["--add-data", f"{ICON_PATH}{';'}assets"])
    if not args.console:
        command.append("--windowed")

    PyInstaller.__main__.run(command)

    artifact = DIST_DIR / f"{APP_NAME}.exe"
    if not args.onefile:
        artifact = DIST_DIR / APP_NAME / f"{APP_NAME}.exe"

    if not artifact.exists():
        print(f"Build finished, but expected artifact was not found: {artifact}", file=sys.stderr)
        return 1

    print(f"Built: {artifact}")
    return 0


def remove_tree(path: Path) -> bool:
    if not path.exists():
        return True

    try:
        shutil.rmtree(path)
    except OSError as exc:
        print(
            f"Could not remove {path}: {exc}\n"
            "Close any running ClipPocket.exe processes and try again.",
            file=sys.stderr,
        )
        return False

    return True


if __name__ == "__main__":
    raise SystemExit(main())
