# Build

Clip Pocket can run from a uv-managed virtual environment during development, and the same environment can build a Windows executable.

Run build commands from the project root, where `pyproject.toml` exists:

```powershell
cd C:\Users\user\Documents\github\Clip_Pocket
```

This project assumes `uv` is installed and available on PATH.

## Development Run

```powershell
uv sync
uv run clip-pocket
```

Normal startup is hidden and resident. Use `uv run clip-pocket --show` when you want the window to appear immediately during development.

## Build Dependencies

The executable build uses PyInstaller as an optional build dependency:

```powershell
uv sync --extra build
```

PyInstaller must run on the target OS. Build the Windows executable on Windows.
The executable, Tk window, and notification-area icon use `src/clip_pocket/assets/clip-pocket.ico`.

## Build Python Package

Build wheel and source distribution:

```powershell
uv build --out-dir dist\python
```

This is useful for checking that the project metadata and package layout are valid.

## Build Executable

Default one-folder bundle:

```powershell
uv run --extra build python tools/build_exe.py --clean
```

Output:

```text
dist\windows\ClipPocket\ClipPocket.exe
```

After building, run the executable once and enable `Start when Windows starts` from the notification-area settings if you want Clip Pocket to monitor copies after login without manual startup.

Close any running `ClipPocket.exe` process before using `--clean`. The build script fails intentionally if it cannot remove old artifacts.

Debug console build:

```powershell
uv run --extra build python tools/build_exe.py --clean --console
```

Use this when a windowed executable exits immediately and you need to see the traceback.

Single-file executable:

```powershell
uv run --extra build python tools/build_exe.py --clean --onefile
```

Output:

```text
dist\windows\ClipPocket.exe
```

The one-folder bundle is the default because it is easier to inspect and tends to start more predictably. The single-file build is convenient for quick sharing, but it has more packaging behavior hidden inside the bootloader.

## License Notes

The app has no external runtime Python packages. PyInstaller is only a build-time dependency. Its license exception allows generated application bundles to be shipped under the app's chosen license, as long as the app's own dependencies permit that.
