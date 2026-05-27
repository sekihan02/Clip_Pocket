from __future__ import annotations

import queue
import time
import tkinter as tk
from tkinter import ttk

from clip_pocket.constants import (
    APP_NAME,
    AUTO_HIDE_MARGIN_PX,
    CLIPBOARD_RETRY_DELAYS_MS,
    MAX_ITEMS,
    MAX_PREVIEW_LENGTH,
    MAX_TEXT_LENGTH,
    MIN_TEXT_LENGTH,
    RETENTION_SECONDS,
    WINDOW_MIN_SIZE,
    WINDOW_SIZE,
)
from clip_pocket.history import ClipboardHistory, ClipboardItem, HistoryChange
from clip_pocket.i18n import (
    LANGUAGE_NAMES,
    normalize_language,
    retention_key_from_label,
    retention_key_from_seconds,
    retention_label,
    retention_labels,
    retention_seconds_from_key,
    text,
)
from clip_pocket.resources import app_icon_path
from clip_pocket.settings import load_settings, save_settings
from clip_pocket.startup import is_startup_enabled, set_startup_enabled
from clip_pocket.win32_host import WindowsEvent, WindowsEventType, WindowsHost


class ClipPocketApp:
    def __init__(self, show_on_start: bool = False) -> None:
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(*WINDOW_MIN_SIZE)
        self.icon_path = app_icon_path()
        if self.icon_path is not None:
            try:
                self.root.iconbitmap(str(self.icon_path))
            except tk.TclError:
                pass

        self.settings = load_settings()
        self.language = normalize_language(self.settings.language)
        self.history = ClipboardHistory(
            retention_seconds=RETENTION_SECONDS,
            min_text_length=MIN_TEXT_LENGTH,
            max_items=self.settings.max_items,
            max_text_length=MAX_TEXT_LENGTH,
        )
        self.history.retention_seconds = self.settings.retention_seconds
        self.events: queue.SimpleQueue[WindowsEvent] = queue.SimpleQueue()
        self.last_seen_clipboard_text = self._get_clipboard_text()
        self.is_exiting = False
        self.main_widgets: dict[str, tk.Misc] = {}
        self.startup_enabled_var = tk.BooleanVar(value=is_startup_enabled())
        self.language_var = tk.StringVar(value=LANGUAGE_NAMES[self.language])
        self.ctrl_double_tap_var = tk.BooleanVar(value=self.settings.ctrl_double_tap_enabled)
        self.right_triple_click_var = tk.BooleanVar(value=self.settings.right_triple_click_enabled)
        self.retention_var = tk.StringVar(
            value=retention_label(
                self.language,
                retention_key_from_seconds(self.settings.retention_seconds),
            )
        )
        self.max_items_var = tk.StringVar(value=str(self.settings.max_items))
        self.keep_open_var = tk.BooleanVar(value=False)
        self.auto_hide_after_id: str | None = None
        self.settings_window: tk.Toplevel | None = None
        self.settings_widgets: dict[str, tk.Misc] = {}

        self._build_ui()
        self._apply_language()
        self.root.update_idletasks()

        self.host = WindowsHost(
            self.events.put,
            ctrl_double_tap_enabled=self.settings.ctrl_double_tap_enabled,
            right_triple_click_enabled=self.settings.right_triple_click_enabled,
            language=self.language,
            icon_path=str(self.icon_path) if self.icon_path is not None else None,
        )
        self.host.start()

        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.bind("<Unmap>", self._hide_when_minimized)
        self.root.after(100, self._drain_host_events)
        self.root.after(60_000, self._expire_items)

        if show_on_start:
            self.show_window()
        else:
            self.root.withdraw()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        title_label = ttk.Label(
            self.root,
            text=APP_NAME,
            font=("Yu Gothic UI", 18, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w", padx=18, pady=(16, 8))
        self.main_widgets["title"] = title_label

        body = ttk.Frame(self.root, padding=(18, 0, 18, 14))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(1, weight=1)

        heading = ttk.Label(body, font=("Yu Gothic UI", 11, "bold"))
        heading.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.main_widgets["heading"] = heading

        list_frame = ttk.Frame(body)
        list_frame.grid(row=1, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(
            list_frame,
            activestyle="dotbox",
            font=("Yu Gothic UI", 10),
            height=12,
            selectmode=tk.EXTENDED,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<Double-Button-1>", self.restore_selected_to_clipboard)
        self.listbox.bind("<Delete>", self.delete_selected_items)
        self.listbox.bind("<Button-3>", self._show_item_context_menu)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(body)
        button_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        button_row.columnconfigure(4, weight=1)

        restore_button = ttk.Button(
            button_row,
            command=self.restore_selected_to_clipboard,
        )
        restore_button.grid(row=0, column=0, padx=(0, 8))
        self.main_widgets["restore_button"] = restore_button

        delete_button = ttk.Button(
            button_row,
            command=self.delete_selected_items,
        )
        delete_button.grid(row=0, column=1)
        self.main_widgets["delete_button"] = delete_button

        keep_open_check = ttk.Checkbutton(
            button_row,
            variable=self.keep_open_var,
            command=self._toggle_keep_open,
        )
        keep_open_check.grid(row=0, column=2, padx=(16, 0), sticky="w")
        self.main_widgets["keep_open_check"] = keep_open_check

        settings_button = ttk.Button(
            button_row,
            command=self.show_settings_window,
        )
        settings_button.grid(row=0, column=3, padx=(12, 0))
        self.main_widgets["settings_button"] = settings_button

        self.count_label = ttk.Label(button_row, text="0件")
        self.count_label.grid(row=0, column=5, sticky="e")

        self.status_var = tk.StringVar(value="")
        status = ttk.Label(body, textvariable=self.status_var, foreground="#555555")
        status.grid(row=3, column=0, sticky="w", pady=(8, 0))

        self.item_menu = tk.Menu(self.root, tearoff=False)
        self.item_menu.add_command(
            label="",
            command=self.restore_selected_to_clipboard,
        )
        self.item_menu.add_command(label="", command=self.delete_selected_items)

    def run(self) -> None:
        self.root.mainloop()

    def tr(self, key: str, **values: object) -> str:
        return text(self.language, key, **values)

    def _apply_language(self) -> None:
        self.root.title(APP_NAME)
        self.main_widgets["heading"].configure(text=self.tr("copied_items"))
        self.main_widgets["restore_button"].configure(text=self.tr("restore"))
        self.main_widgets["delete_button"].configure(text=self.tr("delete"))
        self.main_widgets["keep_open_check"].configure(text=self.tr("keep_open"))
        self.main_widgets["settings_button"].configure(text=self.tr("menu_settings"))
        self.item_menu.entryconfigure(0, label=self.tr("restore"))
        self.item_menu.entryconfigure(1, label=self.tr("delete"))
        self.count_label.configure(text=self.tr("count", count=len(self.history.items)))
        if not self.status_var.get():
            self.status_var.set(self.tr("status_ready"))
        self._refresh_list()
        self._apply_settings_language()

    def _apply_settings_language(self) -> None:
        if self.settings_window is None or not self.settings_window.winfo_exists():
            return

        self.settings_window.title(self.tr("app_settings"))
        self.settings_widgets["title"].configure(text=self.tr("settings_title"))
        self.settings_widgets["language_label"].configure(text=self.tr("language"))
        self.settings_widgets["startup_check"].configure(text=self.tr("startup"))
        self.settings_widgets["ctrl_check"].configure(text=self.tr("ctrl_double_tap"))
        self.settings_widgets["right_check"].configure(text=self.tr("right_triple_click"))
        self.settings_widgets["retention_label"].configure(text=self.tr("retention"))
        self.settings_widgets["max_items_label"].configure(text=self.tr("max_items"))
        self.settings_widgets["apply_button"].configure(text=self.tr("apply"))
        self.settings_widgets["exit_button"].configure(text=self.tr("exit_app"))
        self.settings_widgets["close_button"].configure(text=self.tr("close"))

        retention_combo = self.settings_widgets["retention_combo"]
        retention_key = retention_key_from_seconds(self.settings.retention_seconds)
        retention_combo.configure(values=retention_labels(self.language))
        self.retention_var.set(retention_label(self.language, retention_key))

    def _drain_host_events(self) -> None:
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_host_event(event)

        if not self.is_exiting:
            self.root.after(100, self._drain_host_events)

    def _handle_host_event(self, event: WindowsEvent) -> None:
        if event.type is WindowsEventType.CLIPBOARD_CHANGED:
            self.capture_clipboard_text()
        elif event.type is WindowsEventType.SHOW_WINDOW:
            self.show_window(event.x, event.y)
        elif event.type is WindowsEventType.OPEN_SETTINGS:
            self.show_settings_window()
        elif event.type is WindowsEventType.EXIT_REQUESTED:
            self.exit_app()
        elif event.type is WindowsEventType.WARNING:
            self.status_var.set(event.message)

    def capture_clipboard_text(self) -> None:
        self._capture_clipboard_text_with_retries(0)

    def _capture_clipboard_text_with_retries(self, retry_index: int) -> None:
        text = self._get_clipboard_text()
        if text is None:
            if retry_index < len(CLIPBOARD_RETRY_DELAYS_MS):
                delay = CLIPBOARD_RETRY_DELAYS_MS[retry_index]
                self.root.after(
                    delay,
                    lambda: self._capture_clipboard_text_with_retries(retry_index + 1),
                )
            return

        if text == self.last_seen_clipboard_text:
            return

        self.last_seen_clipboard_text = text
        self._record_text(text)

    def _get_clipboard_text(self) -> str | None:
        try:
            return self.root.clipboard_get()
        except tk.TclError:
            return None

    def _record_text(self, text: str) -> None:
        result = self.history.add_or_refresh(text, time.time())
        if result is HistoryChange.IGNORED:
            return

        if result is HistoryChange.REFRESHED:
            self.status_var.set(self.tr("status_duplicate"))
        else:
            self.status_var.set(self.tr("status_added"))

        self._refresh_list()

    def restore_selected_to_clipboard(self, _event: tk.Event | None = None) -> None:
        selected = self.listbox.curselection()
        if not selected:
            return

        item = self.history.items[selected[0]]

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(item.text)
            self.root.update_idletasks()
        except tk.TclError:
            self.status_var.set(self.tr("status_restore_failed"))
            return

        self.last_seen_clipboard_text = item.text
        new_index = self.history.touch(selected[0], time.time())
        self._refresh_list(select_index=new_index)
        self.status_var.set(self.tr("status_restored"))

    def delete_selected_items(self, _event: tk.Event | None = None) -> None:
        selected = list(self.listbox.curselection())
        if not selected:
            return

        self.history.delete_indices(selected)
        self._refresh_list()
        self.status_var.set(self.tr("status_deleted"))

    def _toggle_startup(self) -> None:
        enabled = self.startup_enabled_var.get()
        try:
            set_startup_enabled(enabled)
        except OSError:
            self.startup_enabled_var.set(not enabled)
            self.status_var.set(self.tr("status_startup_failed"))
            return

        if enabled:
            self.status_var.set(self.tr("status_startup_enabled"))
        else:
            self.status_var.set(self.tr("status_startup_disabled"))

    def _toggle_keep_open(self) -> None:
        if self.keep_open_var.get():
            self._cancel_auto_hide_watch()
            self.status_var.set(self.tr("status_pinned"))
        elif self.root.state() == "normal":
            self.status_var.set(self.tr("status_unpinned"))
            self._start_auto_hide_watch()

    def show_settings_window(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self.startup_enabled_var.set(is_startup_enabled())
        self.language_var.set(LANGUAGE_NAMES[self.language])
        self.ctrl_double_tap_var.set(self.settings.ctrl_double_tap_enabled)
        self.right_triple_click_var.set(self.settings.right_triple_click_enabled)
        self.retention_var.set(
            retention_label(
                self.language,
                retention_key_from_seconds(self.settings.retention_seconds),
            )
        )
        self.max_items_var.set(str(self.settings.max_items))

        window = tk.Toplevel(self.root)
        window.title(self.tr("app_settings"))
        window.resizable(False, False)
        if self.icon_path is not None:
            try:
                window.iconbitmap(str(self.icon_path))
            except tk.TclError:
                pass

        self.settings_window = window
        window.protocol("WM_DELETE_WINDOW", self._close_settings_window)

        frame = ttk.Frame(window, padding=18)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        title = ttk.Label(frame, font=("Yu Gothic UI", 14, "bold"))
        title.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )
        self.settings_widgets["title"] = title

        language_label = ttk.Label(frame)
        language_label.grid(row=1, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["language_label"] = language_label

        language_combo = ttk.Combobox(
            frame,
            textvariable=self.language_var,
            values=[LANGUAGE_NAMES["en"], LANGUAGE_NAMES["ja"]],
            state="readonly",
            width=18,
        )
        language_combo.grid(row=1, column=1, sticky="ew", pady=4)
        language_combo.bind("<<ComboboxSelected>>", self._change_language)
        self.settings_widgets["language_combo"] = language_combo

        startup_check = ttk.Checkbutton(
            frame,
            variable=self.startup_enabled_var,
            command=self._toggle_startup,
        )
        startup_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["startup_check"] = startup_check

        ctrl_check = ttk.Checkbutton(
            frame,
            variable=self.ctrl_double_tap_var,
            command=self._toggle_ctrl_double_tap,
        )
        ctrl_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["ctrl_check"] = ctrl_check

        right_check = ttk.Checkbutton(
            frame,
            variable=self.right_triple_click_var,
            command=self._toggle_right_triple_click,
        )
        right_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["right_check"] = right_check

        retention_label_widget = ttk.Label(frame)
        retention_label_widget.grid(row=5, column=0, sticky="w", pady=(10, 4), padx=(0, 12))
        self.settings_widgets["retention_label"] = retention_label_widget

        retention_combo = ttk.Combobox(
            frame,
            textvariable=self.retention_var,
            values=retention_labels(self.language),
            state="readonly",
            width=18,
        )
        retention_combo.grid(row=5, column=1, sticky="ew", pady=(10, 4))
        self.settings_widgets["retention_combo"] = retention_combo

        max_items_label = ttk.Label(frame)
        max_items_label.grid(row=6, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["max_items_label"] = max_items_label

        max_items_spinbox = tk.Spinbox(
            frame,
            from_=10,
            to=1000,
            increment=10,
            textvariable=self.max_items_var,
            width=8,
        )
        max_items_spinbox.grid(row=6, column=1, sticky="w", pady=4)
        self.settings_widgets["max_items_spinbox"] = max_items_spinbox

        button_row = ttk.Frame(frame)
        button_row.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        button_row.columnconfigure(0, weight=1)

        apply_button = ttk.Button(
            button_row,
            command=self._apply_settings_from_window,
        )
        apply_button.grid(row=0, column=0, sticky="w")
        self.settings_widgets["apply_button"] = apply_button

        exit_button = ttk.Button(
            button_row,
            command=self.exit_app,
        )
        exit_button.grid(row=0, column=1, padx=(8, 0))
        self.settings_widgets["exit_button"] = exit_button

        close_button = ttk.Button(
            button_row,
            command=self._close_settings_window,
        )
        close_button.grid(row=0, column=2, padx=(8, 0), sticky="e")
        self.settings_widgets["close_button"] = close_button

        self._apply_settings_language()

        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
        left = self.root.winfo_pointerx() - 24
        top = self.root.winfo_pointery() - 24
        window.geometry(f"{width}x{height}+{left}+{top}")
        window.lift()
        window.focus_force()

    def _close_settings_window(self) -> None:
        if self.settings_window is not None:
            self.settings_window.destroy()
            self.settings_window = None

    def _toggle_ctrl_double_tap(self) -> None:
        self.settings.ctrl_double_tap_enabled = self.ctrl_double_tap_var.get()
        self._save_shortcut_settings()

    def _toggle_right_triple_click(self) -> None:
        self.settings.right_triple_click_enabled = self.right_triple_click_var.get()
        self._save_shortcut_settings()

    def _change_language(self, _event: tk.Event | None = None) -> None:
        selected = self.language_var.get()
        language = "ja" if selected == LANGUAGE_NAMES["ja"] else "en"
        self.settings.language = language
        self.language = language
        saved = self._save_settings()
        self.host.set_language(language)
        self._apply_language()
        if saved:
            self.status_var.set(self.tr("status_settings_saved"))

    def _apply_settings_from_window(self) -> None:
        retention_key = retention_key_from_label(self.language, self.retention_var.get())
        max_items = self._parse_max_items()

        self.settings.retention_seconds = retention_seconds_from_key(retention_key)
        self.settings.max_items = max_items
        self.history.retention_seconds = self.settings.retention_seconds
        self.history.max_items = max_items
        changed = self.history.enforce_max_items()
        changed = self.history.prune(time.time()) or changed
        if changed:
            self._refresh_list()

        if self._save_settings():
            self.status_var.set(self.tr("status_settings_saved"))

    def _parse_max_items(self) -> int:
        try:
            value = int(self.max_items_var.get())
        except ValueError:
            value = self.settings.max_items
        value = min(max(value, 10), 1000)
        self.max_items_var.set(str(value))
        return value

    def _save_shortcut_settings(self) -> None:
        if not self._save_settings():
            return
        self.host.set_shortcut_options(
            ctrl_double_tap_enabled=self.settings.ctrl_double_tap_enabled,
            right_triple_click_enabled=self.settings.right_triple_click_enabled,
        )
        self.status_var.set(self.tr("status_settings_saved"))

    def _save_settings(self) -> bool:
        try:
            save_settings(self.settings)
        except OSError:
            self.status_var.set(self.tr("status_settings_failed"))
            return False
        return True

    def _expire_items(self, now: float | None = None) -> None:
        if now is None:
            now = time.time()
        if self.history.prune(now):
            self._refresh_list()
            self.status_var.set(self.tr("status_expired"))

        if not self.is_exiting:
            self.root.after(60_000, self._expire_items)

    def _refresh_list(self, select_index: int | None = None) -> None:
        self.listbox.delete(0, tk.END)
        for index, item in enumerate(self.history.items, start=1):
            self.listbox.insert(tk.END, f"[{index}] {self._format_item(item)}")

        if select_index is not None and self.history.items:
            self.listbox.selection_set(select_index)
            self.listbox.activate(select_index)

        self.count_label.configure(text=self.tr("count", count=len(self.history.items)))

    def _format_item(self, item: ClipboardItem) -> str:
        remaining_minutes = self.history.remaining_minutes(item, time.time())
        preview = self._preview(item.text)
        if remaining_minutes is None:
            return self.tr("remaining_unlimited", preview=preview)
        return self.tr("remaining", preview=preview, minutes=remaining_minutes)

    @staticmethod
    def _preview(text: str) -> str:
        single_line = " ".join(text.splitlines())
        if len(single_line) <= MAX_PREVIEW_LENGTH:
            return single_line
        return f"{single_line[: MAX_PREVIEW_LENGTH - 3]}..."

    def _show_item_context_menu(self, event: tk.Event) -> None:
        clicked_index = self.listbox.nearest(event.y)
        if clicked_index >= 0:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(clicked_index)
            self.listbox.activate(clicked_index)
        self.item_menu.tk_popup(event.x_root, event.y_root)
        self.item_menu.grab_release()

    def show_window(self, x: int | None = None, y: int | None = None) -> None:
        self.root.deiconify()
        self.root.update_idletasks()
        self._position_near_pointer(x, y)
        self.root.lift()
        self.root.focus_force()
        self.status_var.set(self.tr("status_window_visible"))
        self._start_auto_hide_watch()

    def hide_window(self) -> None:
        self._cancel_auto_hide_watch()
        self.root.withdraw()

    def _hide_when_minimized(self, _event: tk.Event) -> None:
        if self.root.state() == "iconic":
            self.root.after(0, self.hide_window)

    def _position_near_pointer(self, x: int | None, y: int | None) -> None:
        pointer_x = x if x is not None else self.root.winfo_pointerx()
        pointer_y = y if y is not None else self.root.winfo_pointery()

        width = max(self.root.winfo_width(), self.root.winfo_reqwidth())
        height = max(self.root.winfo_height(), self.root.winfo_reqheight())
        bounds_x = self.root.winfo_vrootx()
        bounds_y = self.root.winfo_vrooty()
        bounds_width = self.root.winfo_vrootwidth()
        bounds_height = self.root.winfo_vrootheight()

        left = pointer_x - 36
        top = pointer_y - 36
        max_left = max(bounds_x, bounds_x + bounds_width - width)
        max_top = max(bounds_y, bounds_y + bounds_height - height)

        left = min(max(left, bounds_x), max_left)
        top = min(max(top, bounds_y), max_top)
        self.root.geometry(f"{width}x{height}+{left}+{top}")

    def _start_auto_hide_watch(self) -> None:
        self._cancel_auto_hide_watch()
        if not self.keep_open_var.get() and self.root.state() == "normal":
            self.auto_hide_after_id = self.root.after(300, self._auto_hide_if_pointer_left)

    def _cancel_auto_hide_watch(self) -> None:
        if self.auto_hide_after_id is not None:
            self.root.after_cancel(self.auto_hide_after_id)
            self.auto_hide_after_id = None

    def _auto_hide_if_pointer_left(self) -> None:
        self.auto_hide_after_id = None
        if self.is_exiting or self.keep_open_var.get() or self.root.state() != "normal":
            return

        pointer_x = self.root.winfo_pointerx()
        pointer_y = self.root.winfo_pointery()
        left = self.root.winfo_rootx()
        top = self.root.winfo_rooty()
        right = left + self.root.winfo_width()
        bottom = top + self.root.winfo_height()
        margin = AUTO_HIDE_MARGIN_PX

        pointer_is_outside = (
            pointer_x < left - margin
            or pointer_x > right + margin
            or pointer_y < top - margin
            or pointer_y > bottom + margin
        )
        if pointer_is_outside:
            self.hide_window()
            return

        self.auto_hide_after_id = self.root.after(180, self._auto_hide_if_pointer_left)

    def exit_app(self) -> None:
        self.is_exiting = True
        self._cancel_auto_hide_watch()
        self.host.stop()
        self.root.destroy()
