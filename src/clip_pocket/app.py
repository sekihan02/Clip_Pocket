from __future__ import annotations

import argparse
import logging
import sys

from clip_pocket.constants import APP_MUTEX_NAME, APP_NAME
from clip_pocket.diagnostics import configure_logging, show_startup_error
from clip_pocket.startup import disable_startup, enable_startup, is_startup_enabled


def main(argv: list[str] | None = None) -> None:
    if sys.platform != "win32":
        raise SystemExit(f"{APP_NAME} is a Windows-only resident desktop app.")

    from clip_pocket.ui import ClipPocketApp
    from clip_pocket.win32_host import SingleInstance

    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument(
        "--show",
        action="store_true",
        help="show the window immediately after startup",
    )
    parser.add_argument(
        "--hidden",
        action="store_true",
        help="start resident in the notification area without showing the window",
    )
    parser.add_argument(
        "--install-startup",
        action="store_true",
        help="start Clip Pocket automatically when the current user logs in",
    )
    parser.add_argument(
        "--uninstall-startup",
        action="store_true",
        help="remove Clip Pocket from the current user's login startup",
    )
    parser.add_argument(
        "--startup-status",
        action="store_true",
        help="print whether login startup is enabled",
    )
    args = parser.parse_args(argv)
    show_on_start = args.show and not args.hidden

    if args.install_startup:
        enable_startup()
        print("Startup enabled.")
        return

    if args.uninstall_startup:
        disable_startup()
        print("Startup disabled.")
        return

    if args.startup_status:
        print("Startup enabled." if is_startup_enabled() else "Startup disabled.")
        return

    configure_logging()

    single_instance = SingleInstance(APP_MUTEX_NAME)
    try:
        if single_instance.already_running:
            from clip_pocket.win32_host import request_existing_instance_window

            request_existing_instance_window()
            return

        app = ClipPocketApp(show_on_start=show_on_start)
        app.run()
    except Exception as exc:
        logging.exception("Unhandled startup/runtime error")
        show_startup_error(exc)
        raise
    finally:
        single_instance.close()


if __name__ == "__main__":
    main()
