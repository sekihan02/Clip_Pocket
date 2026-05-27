# OSS readiness check

Last checked: 2026-05-27

## Name

`Clip Pocket` is treated as a temporary project name.

Do not claim that the name is conflict-free just because a quick search did not reveal an obvious collision. Before public release, check at least:

- GitHub repository names
- PyPI project names
- Microsoft Store app names
- major search engines
- trademark databases in the intended release regions

## Dependencies

The current implementation uses no external runtime Python packages.

Runtime/framework dependencies:

- Python 3.11+
- tkinter, included with normal Windows Python distributions
- Windows API through Python standard-library `ctypes`
- uv for local development and deployment commands

This keeps third-party package license obligations out of the current implementation.

`hatchling` is declared as the Python build backend in `pyproject.toml`; it is not an app runtime dependency.

`pyinstaller` is declared as an optional build dependency. It is used to produce Windows executable bundles and is not imported by the app at runtime.

## License posture

The repository currently includes an MIT license. Change it before public release if a different license is desired.

References checked while preparing this note:

- Python is distributed under the PSF License Agreement.
- uv is dual-licensed under MIT or Apache-2.0.
- Hatch is distributed under the MIT license.
- PyInstaller has a GPL license with an exception for generated application bundles.
- The Windows integration uses documented Win32 APIs: `Shell_NotifyIconW`, `AddClipboardFormatListener`, and `SetWindowsHookExW`.

## Packaging direction

Development and local deployment should use uv:

```powershell
uv run clip-pocket
```

Executable packaging is currently implemented with PyInstaller through `tools/build_exe.py`.
Release builds use the one-folder Windows bundle documented in the README.
If distribution grows beyond GitHub Releases, revisit whether an installer or signed executable is needed.
