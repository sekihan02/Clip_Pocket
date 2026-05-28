# Architecture

Clip Pocket is split into small modules so the app can be reviewed and tested before being published.

## Modules

- `clip_pocket.app`
  - Parses CLI arguments.
  - Enforces the Windows-only runtime check.
  - Starts the single-instance guard and UI.

- `clip_pocket.history`
  - Owns clipboard-history behavior.
  - Has no UI or Windows API dependency.
  - Covered by unit tests.

- `clip_pocket.ui`
  - Owns the Tkinter window.
  - Reads and writes clipboard text on the Tk thread.
  - Receives host events from a thread-safe queue.

- `clip_pocket.win32_host`
  - Owns Windows integration.
  - Creates a dedicated hidden Win32 window for `WM_CLIPBOARDUPDATE`, notification-area callbacks, and duplicate-launch show requests.
  - Uses a low-level keyboard hook to detect the Ctrl-double-tap show gesture.
  - Uses a low-level mouse hook only when the experimental right-click-triple gesture is enabled.
  - Does not subclass or replace Tkinter's window procedure.

- `clip_pocket.settings`
  - Owns lightweight local settings persisted under the current user's local app-data directory.
  - Stores UI language, gesture options, color theme, window opacity, font size, window size, retention period, and maximum item count.
  - Startup registration itself stays in `clip_pocket.startup`.

- `clip_pocket.startup`
  - Owns per-user login startup registration.
  - Uses the current user's `Run` registry key and starts the app with `--hidden`.

- `clip_pocket.resources`
  - Resolves bundled assets such as the app icon in both source and PyInstaller builds.

- `tools/build_exe.py`
  - Builds a Windows executable through PyInstaller.
  - Keeps packaging commands out of README-only manual steps.

## Current Step1 boundaries

- History is in memory only.
- No SQLite or persistent storage.
- No automatic paste into other applications.
- No classification, search, item pinning, memo, or sync behavior.

## Release checklist

- Recheck the product name before wider distribution.
- Verify the Windows release ZIP on a clean Windows machine.
- Confirm the notification-area icon, Ctrl double-tap, and clipboard monitoring.
- Keep README, release notes, and version numbers in sync.
- Add more release automation if releases become frequent.
