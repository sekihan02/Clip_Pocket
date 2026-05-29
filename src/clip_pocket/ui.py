from __future__ import annotations

from dataclasses import replace
import queue
import time
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from clip_pocket.constants import (
    APP_NAME,
    AUTO_HIDE_INITIAL_DELAY_MS,
    AUTO_HIDE_MARGIN_PX,
    AUTO_HIDE_POLL_INTERVAL_MS,
    AUTO_HIDE_STILL_POINTER_TOLERANCE_PX,
    CLIPBOARD_RETRY_DELAYS_MS,
    MAX_FONT_SIZE,
    MAX_HISTORY_TEXT_LENGTH,
    MAX_PREVIEW_LENGTH,
    MAX_ITEM_TEXT_LENGTH,
    MIN_FONT_SIZE,
    MIN_TEXT_LENGTH,
    RETENTION_SECONDS,
    WINDOW_SCREEN_MARGIN_PX,
    WINDOW_MAX_SIZE,
    WINDOW_MIN_SIZE,
)
from clip_pocket.history import ClipboardHistory, ClipboardItem, HistoryChange
from clip_pocket.i18n import (
    LANGUAGE_NAMES,
    color_theme_key_from_label,
    color_theme_label,
    color_theme_labels,
    normalize_language,
    retention_key_from_label,
    retention_key_from_seconds,
    retention_label,
    retention_labels,
    retention_seconds_from_key,
    text,
)
from clip_pocket.resources import app_icon_path
from clip_pocket.settings import (
    AppSettings,
    load_settings,
    normalize_color_theme,
    normalize_font_size,
    normalize_window_height,
    normalize_window_width,
    normalize_max_items,
    normalize_window_opacity,
    save_settings,
)
from clip_pocket.startup import is_startup_enabled, set_startup_enabled
from clip_pocket.win32_host import WindowsEvent, WindowsEventType, WindowsHost


MIN_VISIBLE_WINDOW_OPACITY = 0.08


THEME_PALETTES = {
    "light": {
        "background": "#f7f7f7",
        "surface": "#ffffff",
        "foreground": "#202124",
        "muted": "#555555",
        "border": "#d9d9d9",
        "selection": "#2563eb",
        "selection_text": "#ffffff",
        "button": "#f2f2f2",
        "button_active": "#e7e7e7",
    },
    "dark": {
        "background": "#202124",
        "surface": "#111315",
        "foreground": "#f5f5f5",
        "muted": "#c7c7c7",
        "border": "#3a3a3a",
        "selection": "#3b82f6",
        "selection_text": "#ffffff",
        "button": "#2b2d31",
        "button_active": "#34373d",
    },
}


def scrollbar_thumb_bounds(
    first: float,
    last: float,
    length: int,
    *,
    padding: int = 3,
    minimum_thumb_length: int = 32,
) -> tuple[int, int]:
    track_length = max(0, length - (padding * 2))
    if track_length <= 0:
        return padding, padding

    first = min(max(float(first), 0.0), 1.0)
    last = min(max(float(last), first), 1.0)
    thumb_length = max(minimum_thumb_length, round((last - first) * track_length))
    thumb_length = min(thumb_length, track_length)
    max_top = padding + track_length - thumb_length
    top = padding + round(first * track_length)
    top = min(max(padding, top), max_top)
    return top, top + thumb_length


class ModernScrollbar(tk.Canvas):
    def __init__(self, master: tk.Misc, command: object) -> None:
        super().__init__(
            master,
            width=14,
            borderwidth=0,
            highlightthickness=0,
            takefocus=0,
        )
        self.command = command
        self.first = 0.0
        self.last = 1.0
        self.track_color = "#f7f7f7"
        self.thumb_color = "#9ca3af"
        self.active_thumb_color = "#6b7280"
        self.is_active = False
        self.drag_offset = 0
        self.bind("<Configure>", self._redraw)
        self.bind("<Enter>", self._set_active)
        self.bind("<Leave>", self._clear_active)
        self.bind("<Button-1>", self._handle_press)
        self.bind("<B1-Motion>", self._handle_drag)
        self.bind("<ButtonRelease-1>", self._clear_active)
        self.bind("<MouseWheel>", self._handle_mouse_wheel)

    def set(self, first: object, last: object) -> None:
        try:
            self.first = float(first)
            self.last = float(last)
        except (TypeError, ValueError):
            self.first = 0.0
            self.last = 1.0
        self._redraw()

    def configure_colors(
        self,
        *,
        track: str,
        thumb: str,
        active_thumb: str,
    ) -> None:
        self.track_color = track
        self.thumb_color = thumb
        self.active_thumb_color = active_thumb
        self.configure(background=track)
        self._redraw()

    def _set_active(self, _event: tk.Event) -> None:
        self.is_active = True
        self._redraw()

    def _clear_active(self, _event: tk.Event) -> None:
        self.is_active = False
        self.drag_offset = 0
        self._redraw()

    def _handle_press(self, event: tk.Event) -> str:
        self.is_active = True
        top, bottom = self._thumb_bounds()
        if top <= event.y <= bottom:
            self.drag_offset = event.y - top
        else:
            self.drag_offset = max(0, (bottom - top) // 2)
            self._move_thumb_to(event.y)
        self._redraw()
        return "break"

    def _handle_drag(self, event: tk.Event) -> str:
        self._move_thumb_to(event.y)
        return "break"

    def _handle_mouse_wheel(self, event: tk.Event) -> str:
        units = -1 if event.delta > 0 else 1
        self.command("scroll", units, "units")
        return "break"

    def _move_thumb_to(self, y: int) -> None:
        top, bottom = self._thumb_bounds()
        thumb_length = bottom - top
        track_length = max(1, self.winfo_height() - 6)
        minimum_top = 3
        maximum_top = minimum_top + track_length - thumb_length
        new_top = min(max(minimum_top, y - self.drag_offset), maximum_top)
        self.command("moveto", (new_top - minimum_top) / track_length)

    def _thumb_bounds(self) -> tuple[int, int]:
        return scrollbar_thumb_bounds(self.first, self.last, self.winfo_height())

    def _redraw(self, _event: tk.Event | None = None) -> None:
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        self.create_rectangle(0, 0, width, height, fill=self.track_color, outline="")
        if self.first <= 0.0 and self.last >= 1.0:
            return
        top, bottom = self._thumb_bounds()
        color = self.active_thumb_color if self.is_active else self.thumb_color
        self.create_line(
            width // 2,
            top,
            width // 2,
            bottom,
            width=8,
            fill=color,
            capstyle=tk.ROUND,
        )


class ClipPocketApp:
    def __init__(self, show_on_start: bool = False) -> None:
        self.root = tk.Tk()
        self.style = ttk.Style(self.root)
        self.settings = load_settings()
        self.root.title(APP_NAME)
        self.root.geometry(self._settings_window_geometry())
        self.root.minsize(*WINDOW_MIN_SIZE)
        self.root.maxsize(*WINDOW_MAX_SIZE)
        self.icon_path = app_icon_path()
        if self.icon_path is not None:
            try:
                self.root.iconbitmap(str(self.icon_path))
            except tk.TclError:
                pass

        self.language = normalize_language(self.settings.language)
        self.history = ClipboardHistory(
            retention_seconds=RETENTION_SECONDS,
            min_text_length=MIN_TEXT_LENGTH,
            max_items=self.settings.max_items,
            max_item_text_length=MAX_ITEM_TEXT_LENGTH,
            max_history_text_length=MAX_HISTORY_TEXT_LENGTH,
        )
        self.history.retention_seconds = self.settings.retention_seconds
        self.events: queue.SimpleQueue[WindowsEvent] = queue.SimpleQueue()
        self.suppress_next_clipboard_text: str | None = None
        self.suppress_clear_after_id: str | None = None
        self.capture_paused = False
        self.is_exiting = False
        self.main_widgets: dict[str, tk.Misc] = {}
        self.startup_enabled_var = tk.BooleanVar(value=is_startup_enabled())
        self.language_var = tk.StringVar(value=LANGUAGE_NAMES[self.language])
        self.ctrl_double_tap_var = tk.BooleanVar(value=self.settings.ctrl_double_tap_enabled)
        self.right_triple_click_var = tk.BooleanVar(value=self.settings.right_triple_click_enabled)
        self.color_theme_var = tk.StringVar(
            value=color_theme_label(self.language, self.settings.color_theme)
        )
        self.opacity_var = tk.DoubleVar(value=self.settings.window_opacity * 100)
        self.opacity_value_var = tk.StringVar()
        self.font_size_var = tk.StringVar(value=str(self.settings.font_size))
        self.window_width_var = tk.StringVar(value=str(self.settings.window_width))
        self.window_height_var = tk.StringVar(value=str(self.settings.window_height))
        self.retention_var = tk.StringVar(
            value=retention_label(
                self.language,
                retention_key_from_seconds(self.settings.retention_seconds),
            )
        )
        self.max_items_var = tk.StringVar(value=str(self.settings.max_items))
        self.keep_open_var = tk.BooleanVar(value=False)
        self.auto_hide_after_id: str | None = None
        self.auto_hide_anchor_position: tuple[int, int] | None = None
        self.window_size_save_after_id: str | None = None
        self.is_applying_window_size = False
        self.settings_window: tk.Toplevel | None = None
        self.settings_widgets: dict[str, tk.Misc] = {}

        self._build_ui()
        self._apply_language()
        self._apply_visual_settings()
        self._apply_font_settings()
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
        self.root.bind("<Configure>", self._handle_root_configure)
        self.root.after(100, self._drain_host_events)
        self.root.after(60_000, self._expire_items)

        if show_on_start:
            self.show_window()
        else:
            self.root.withdraw()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        body = ttk.Frame(self.root, padding=(18, 14, 18, 14))
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.main_widgets["body"] = body

        list_frame = ttk.Frame(body)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        self.main_widgets["list_frame"] = list_frame

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

        scrollbar = ModernScrollbar(list_frame, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.main_widgets["history_scrollbar"] = scrollbar

        button_row = ttk.Frame(body)
        button_row.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        button_row.columnconfigure(4, weight=1)
        self.main_widgets["button_row"] = button_row

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

        monitoring_label = ttk.Label(button_row, foreground="#555555")
        monitoring_label.grid(row=0, column=4, sticky="e", padx=(12, 10))
        self.main_widgets["monitoring_label"] = monitoring_label

        self.count_label = ttk.Label(button_row, text="0件")
        self.count_label.grid(row=0, column=5, sticky="e")

        self.status_var = tk.StringVar(value="")
        status = ttk.Label(body, textvariable=self.status_var, foreground="#555555")
        status.grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.main_widgets["status"] = status

        size_grip = ttk.Sizegrip(body)
        size_grip.grid(row=2, column=0, sticky="se", pady=(8, 0))
        self.main_widgets["size_grip"] = size_grip

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
        self.main_widgets["restore_button"].configure(text=self.tr("restore"))
        self.main_widgets["delete_button"].configure(text=self.tr("delete"))
        self.main_widgets["keep_open_check"].configure(text=self.tr("keep_open"))
        self.main_widgets["settings_button"].configure(text=self.tr("menu_settings"))
        self._update_monitoring_label()
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
        self.settings_widgets["right_hint"].configure(text=self.tr("right_triple_click_hint"))
        self.settings_widgets["color_theme_label"].configure(text=self.tr("color_theme"))
        self.settings_widgets["opacity_label"].configure(text=self.tr("opacity"))
        self.settings_widgets["font_size_label"].configure(text=self.tr("font_size"))
        self.settings_widgets["window_width_label"].configure(text=self.tr("window_width"))
        self.settings_widgets["window_height_label"].configure(text=self.tr("window_height"))
        self.settings_widgets["retention_label"].configure(text=self.tr("retention"))
        self.settings_widgets["max_items_label"].configure(text=self.tr("max_items"))
        self.settings_widgets["apply_button"].configure(text=self.tr("apply"))
        self.settings_widgets["exit_button"].configure(text=self.tr("exit_app"))
        self.settings_widgets["close_button"].configure(text=self.tr("close"))

        color_theme_combo = self.settings_widgets["color_theme_combo"]
        color_theme_key = normalize_color_theme(self.settings.color_theme)
        color_theme_combo.configure(values=color_theme_labels(self.language))
        self.color_theme_var.set(color_theme_label(self.language, color_theme_key))

        retention_combo = self.settings_widgets["retention_combo"]
        retention_key = retention_key_from_seconds(self.settings.retention_seconds)
        retention_combo.configure(values=retention_labels(self.language))
        self.retention_var.set(retention_label(self.language, retention_key))
        self._update_opacity_value_label()

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
        elif event.type is WindowsEventType.TOGGLE_PAUSE:
            self._toggle_capture_paused()
        elif event.type is WindowsEventType.EXIT_REQUESTED:
            self.exit_app()
        elif event.type is WindowsEventType.WARNING:
            self.status_var.set(event.message)
            self.show_window()

    def capture_clipboard_text(self) -> None:
        if self.capture_paused:
            return
        self._capture_clipboard_text_with_retries(0)

    def _capture_clipboard_text_with_retries(self, retry_index: int) -> None:
        if self.capture_paused:
            return

        text = self._get_clipboard_text()
        if text is None:
            if retry_index < len(CLIPBOARD_RETRY_DELAYS_MS):
                delay = CLIPBOARD_RETRY_DELAYS_MS[retry_index]
                self.root.after(
                    delay,
                    lambda: self._capture_clipboard_text_with_retries(retry_index + 1),
                )
            return

        if self.suppress_next_clipboard_text is not None:
            if text == self.suppress_next_clipboard_text:
                self._clear_clipboard_suppression()
                return
            self._clear_clipboard_suppression()

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

        self._suppress_next_clipboard_update(item.text)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(item.text)
            self.root.update_idletasks()
        except tk.TclError:
            self._clear_clipboard_suppression()
            self.status_var.set(self.tr("status_restore_failed"))
            return

        new_index = self.history.touch(selected[0], time.time())
        self._refresh_list(select_index=new_index)
        self.status_var.set(self.tr("status_restored"))

    def _suppress_next_clipboard_update(self, text: str) -> None:
        self._cancel_clipboard_suppression_timer()
        self.suppress_next_clipboard_text = text
        self.suppress_clear_after_id = self.root.after(
            1_500,
            self._expire_clipboard_suppression,
        )

    def _clear_clipboard_suppression(self) -> None:
        self._cancel_clipboard_suppression_timer()
        self.suppress_next_clipboard_text = None

    def _expire_clipboard_suppression(self) -> None:
        self.suppress_clear_after_id = None
        self.suppress_next_clipboard_text = None

    def _cancel_clipboard_suppression_timer(self) -> None:
        if self.suppress_clear_after_id is not None:
            try:
                self.root.after_cancel(self.suppress_clear_after_id)
            except tk.TclError:
                pass
            self.suppress_clear_after_id = None

    def delete_selected_items(self, _event: tk.Event | None = None) -> None:
        selected = list(self.listbox.curselection())
        if not selected:
            return

        self.history.delete_indices(selected)
        self._refresh_list()
        self.status_var.set(self.tr("status_deleted"))

    def _toggle_keep_open(self) -> None:
        if self.keep_open_var.get():
            self._cancel_auto_hide_watch()
            self.status_var.set(self.tr("status_pinned"))
        elif self.root.state() == "normal":
            self.status_var.set(self.tr("status_unpinned"))
            self._start_auto_hide_watch()

    def _toggle_capture_paused(self) -> None:
        self.capture_paused = not self.capture_paused
        self.host.set_paused(self.capture_paused)
        self._update_monitoring_label()
        if self.capture_paused:
            self.status_var.set(self.tr("status_paused"))
        else:
            self.status_var.set(self.tr("status_resumed"))

    def _update_monitoring_label(self) -> None:
        if "monitoring_label" not in self.main_widgets:
            return
        key = "monitoring_paused" if self.capture_paused else "monitoring_active"
        self.main_widgets["monitoring_label"].configure(text=self.tr(key))

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
        self.color_theme_var.set(color_theme_label(self.language, self.settings.color_theme))
        self.opacity_var.set(self.settings.window_opacity * 100)
        self._update_opacity_value_label()
        self.font_size_var.set(str(self.settings.font_size))
        self.window_width_var.set(str(self.settings.window_width))
        self.window_height_var.set(str(self.settings.window_height))
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
        self.settings_widgets["language_combo"] = language_combo

        startup_check = ttk.Checkbutton(
            frame,
            variable=self.startup_enabled_var,
        )
        startup_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["startup_check"] = startup_check

        ctrl_check = ttk.Checkbutton(
            frame,
            variable=self.ctrl_double_tap_var,
        )
        ctrl_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["ctrl_check"] = ctrl_check

        right_check = ttk.Checkbutton(
            frame,
            variable=self.right_triple_click_var,
        )
        right_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=4)
        self.settings_widgets["right_check"] = right_check

        right_hint = ttk.Label(frame, foreground="#666666", wraplength=360)
        right_hint.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.settings_widgets["right_hint"] = right_hint

        color_theme_label_widget = ttk.Label(frame)
        color_theme_label_widget.grid(row=6, column=0, sticky="w", pady=(10, 4), padx=(0, 12))
        self.settings_widgets["color_theme_label"] = color_theme_label_widget

        color_theme_combo = ttk.Combobox(
            frame,
            textvariable=self.color_theme_var,
            values=color_theme_labels(self.language),
            state="readonly",
            width=18,
        )
        color_theme_combo.grid(row=6, column=1, sticky="ew", pady=(10, 4))
        self.settings_widgets["color_theme_combo"] = color_theme_combo

        opacity_label_widget = ttk.Label(frame)
        opacity_label_widget.grid(row=7, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["opacity_label"] = opacity_label_widget

        opacity_row = ttk.Frame(frame)
        opacity_row.grid(row=7, column=1, sticky="ew", pady=4)
        opacity_row.columnconfigure(0, weight=1)
        self.settings_widgets["opacity_row"] = opacity_row

        opacity_scale = ttk.Scale(
            opacity_row,
            from_=0,
            to=100,
            variable=self.opacity_var,
            command=self._on_opacity_scale_changed,
        )
        opacity_scale.grid(row=0, column=0, sticky="ew")
        self.settings_widgets["opacity_scale"] = opacity_scale

        opacity_value_label = ttk.Label(opacity_row, textvariable=self.opacity_value_var, width=5)
        opacity_value_label.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.settings_widgets["opacity_value_label"] = opacity_value_label

        font_size_label = ttk.Label(frame)
        font_size_label.grid(row=8, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["font_size_label"] = font_size_label

        font_size_spinbox = tk.Spinbox(
            frame,
            from_=MIN_FONT_SIZE,
            to=MAX_FONT_SIZE,
            increment=1,
            textvariable=self.font_size_var,
            width=8,
        )
        font_size_spinbox.grid(row=8, column=1, sticky="w", pady=4)
        self.settings_widgets["font_size_spinbox"] = font_size_spinbox

        window_width_label = ttk.Label(frame)
        window_width_label.grid(row=9, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["window_width_label"] = window_width_label

        window_width_spinbox = tk.Spinbox(
            frame,
            from_=WINDOW_MIN_SIZE[0],
            to=WINDOW_MAX_SIZE[0],
            increment=20,
            textvariable=self.window_width_var,
            width=8,
        )
        window_width_spinbox.grid(row=9, column=1, sticky="w", pady=4)
        self.settings_widgets["window_width_spinbox"] = window_width_spinbox

        window_height_label = ttk.Label(frame)
        window_height_label.grid(row=10, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["window_height_label"] = window_height_label

        window_height_spinbox = tk.Spinbox(
            frame,
            from_=WINDOW_MIN_SIZE[1],
            to=WINDOW_MAX_SIZE[1],
            increment=20,
            textvariable=self.window_height_var,
            width=8,
        )
        window_height_spinbox.grid(row=10, column=1, sticky="w", pady=4)
        self.settings_widgets["window_height_spinbox"] = window_height_spinbox

        retention_label_widget = ttk.Label(frame)
        retention_label_widget.grid(row=11, column=0, sticky="w", pady=(10, 4), padx=(0, 12))
        self.settings_widgets["retention_label"] = retention_label_widget

        retention_combo = ttk.Combobox(
            frame,
            textvariable=self.retention_var,
            values=retention_labels(self.language),
            state="readonly",
            width=18,
        )
        retention_combo.grid(row=11, column=1, sticky="ew", pady=(10, 4))
        self.settings_widgets["retention_combo"] = retention_combo

        max_items_label = ttk.Label(frame)
        max_items_label.grid(row=12, column=0, sticky="w", pady=4, padx=(0, 12))
        self.settings_widgets["max_items_label"] = max_items_label

        max_items_spinbox = tk.Spinbox(
            frame,
            from_=10,
            to=1000,
            increment=10,
            textvariable=self.max_items_var,
            width=8,
        )
        max_items_spinbox.grid(row=12, column=1, sticky="w", pady=4)
        self.settings_widgets["max_items_spinbox"] = max_items_spinbox

        button_row = ttk.Frame(frame)
        button_row.grid(row=13, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        button_row.columnconfigure(0, weight=1)
        self.settings_widgets["button_row"] = button_row

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
        self._apply_visual_settings()
        self._apply_font_settings()

        window.update_idletasks()
        self._position_settings_window(window)
        window.lift()
        window.focus_force()

    def _close_settings_window(self) -> None:
        if self.settings_window is not None:
            self.settings_window.destroy()
            self.settings_window = None

    def _position_settings_window(self, window: tk.Toplevel) -> None:
        width = window.winfo_width()
        height = window.winfo_height()
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        left = self.root.winfo_pointerx() - 24
        top = self.root.winfo_pointery() - 24
        left = min(max(0, left), max(0, screen_width - width))
        top = min(max(0, top), max(0, screen_height - height))
        window.geometry(f"{width}x{height}+{left}+{top}")

    def _apply_settings_from_window(self) -> None:
        selected_language = self.language_var.get()
        language = "ja" if selected_language == LANGUAGE_NAMES["ja"] else "en"
        startup_enabled = self.startup_enabled_var.get()
        ctrl_double_tap_enabled = self.ctrl_double_tap_var.get()
        right_triple_click_enabled = self.right_triple_click_var.get()
        color_theme = normalize_color_theme(
            color_theme_key_from_label(self.language, self.color_theme_var.get())
        )
        window_opacity = normalize_window_opacity(self.opacity_var.get() / 100)
        font_size = self._parse_font_size()
        window_width = self._parse_window_width()
        window_height = self._parse_window_height()
        retention_key = retention_key_from_label(self.language, self.retention_var.get())
        max_items = self._parse_max_items()
        retention_seconds = retention_seconds_from_key(retention_key)
        new_settings = AppSettings(
            language=language,
            ctrl_double_tap_enabled=ctrl_double_tap_enabled,
            right_triple_click_enabled=right_triple_click_enabled,
            retention_seconds=retention_seconds,
            max_items=max_items,
            color_theme=color_theme,
            window_opacity=window_opacity,
            font_size=font_size,
            window_width=window_width,
            window_height=window_height,
        )
        previous_startup_enabled = is_startup_enabled()

        if startup_enabled != previous_startup_enabled:
            try:
                set_startup_enabled(startup_enabled)
            except OSError:
                self.startup_enabled_var.set(previous_startup_enabled)
                self.status_var.set(self.tr("status_startup_failed"))
                return

        try:
            save_settings(new_settings)
        except OSError:
            if startup_enabled != previous_startup_enabled:
                try:
                    set_startup_enabled(previous_startup_enabled)
                except OSError:
                    pass
                self.startup_enabled_var.set(previous_startup_enabled)
            self.status_var.set(self.tr("status_settings_failed"))
            return

        self.settings = new_settings
        self.language = language
        self.opacity_var.set(self.settings.window_opacity * 100)
        self.font_size_var.set(str(font_size))
        self._apply_window_size(window_width, window_height)
        self.history.retention_seconds = self.settings.retention_seconds
        self.history.max_items = max_items
        changed = self.history.enforce_max_items()
        changed = self.history.enforce_total_text_length() or changed
        changed = self.history.prune(time.time()) or changed
        if changed:
            self._refresh_list()

        self.host.set_language(language)
        self.host.set_shortcut_options(
            ctrl_double_tap_enabled=ctrl_double_tap_enabled,
            right_triple_click_enabled=right_triple_click_enabled,
        )
        self._apply_language()
        self._apply_visual_settings()
        self._apply_font_settings()
        self.status_var.set(self.tr("status_settings_saved"))
        self._close_settings_window()

    def _parse_font_size(self) -> int:
        try:
            value = int(self.font_size_var.get())
        except ValueError:
            value = self.settings.font_size
        value = normalize_font_size(value)
        self.font_size_var.set(str(value))
        return value

    def _parse_max_items(self) -> int:
        try:
            value = int(self.max_items_var.get())
        except ValueError:
            value = self.settings.max_items
        value = normalize_max_items(value)
        self.max_items_var.set(str(value))
        return value

    def _parse_window_width(self) -> int:
        try:
            value = int(self.window_width_var.get())
        except ValueError:
            value = self.settings.window_width
        value = normalize_window_width(value)
        self.window_width_var.set(str(value))
        return value

    def _parse_window_height(self) -> int:
        try:
            value = int(self.window_height_var.get())
        except ValueError:
            value = self.settings.window_height
        value = normalize_window_height(value)
        self.window_height_var.set(str(value))
        return value

    def _settings_window_geometry(self) -> str:
        width, height = self._configured_window_size()
        return f"{width}x{height}"

    def _configured_window_size(self) -> tuple[int, int]:
        return self._normalize_window_size(
            self.settings.window_width,
            self.settings.window_height,
        )

    @staticmethod
    def _normalize_window_size(width: object, height: object) -> tuple[int, int]:
        return normalize_window_width(width), normalize_window_height(height)

    def _apply_window_size(self, width: int, height: int) -> None:
        width = normalize_window_width(width)
        height = normalize_window_height(height)
        self.is_applying_window_size = True
        try:
            if self.root.state() == "normal":
                self.root.geometry(
                    f"{width}x{height}+{self.root.winfo_x()}+{self.root.winfo_y()}"
                )
            else:
                self.root.geometry(f"{width}x{height}")
            self.root.update_idletasks()
        finally:
            self.is_applying_window_size = False

    def _apply_visual_settings(self) -> None:
        theme = normalize_color_theme(self.settings.color_theme)
        palette = THEME_PALETTES[theme]
        opacity = normalize_window_opacity(self.settings.window_opacity)

        self._configure_ttk_style(palette)
        self._configure_main_window_visuals(palette, opacity)
        self._configure_settings_window_visuals(palette, opacity)

    def _apply_font_settings(self) -> None:
        base_size = normalize_font_size(self.settings.font_size)
        family = "Yu Gothic UI"
        default_font = (family, base_size)
        title_font = (family, base_size + 4, "bold")

        for name in (
            "TkDefaultFont",
            "TkTextFont",
            "TkMenuFont",
            "TkCaptionFont",
            "TkSmallCaptionFont",
            "TkIconFont",
        ):
            try:
                tkfont.nametofont(name).configure(family=family, size=base_size)
            except tk.TclError:
                pass

        self.style.configure(".", font=default_font)
        self.style.configure("TLabel", font=default_font)
        self.style.configure("TButton", font=default_font)
        self.style.configure("TCheckbutton", font=default_font)
        self.style.configure("TCombobox", font=default_font)
        self.listbox.configure(font=default_font)
        self.item_menu.configure(font=default_font)

        if self.settings_window is not None and self.settings_window.winfo_exists():
            title = self.settings_widgets.get("title")
            if isinstance(title, ttk.Label):
                title.configure(font=title_font)
            for key in (
                "font_size_spinbox",
                "window_width_spinbox",
                "window_height_spinbox",
                "max_items_spinbox",
            ):
                spinbox = self.settings_widgets.get(key)
                if isinstance(spinbox, tk.Spinbox):
                    spinbox.configure(font=default_font)

    def _configure_ttk_style(self, palette: dict[str, str]) -> None:
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        self.style.configure(
            ".",
            background=palette["background"],
            foreground=palette["foreground"],
            fieldbackground=palette["surface"],
        )
        self.style.configure("TFrame", background=palette["background"])
        self.style.configure(
            "TLabel",
            background=palette["background"],
            foreground=palette["foreground"],
        )
        self.style.configure(
            "TCheckbutton",
            background=palette["background"],
            foreground=palette["foreground"],
        )
        self.style.map(
            "TCheckbutton",
            background=[("active", palette["background"])],
            foreground=[("active", palette["foreground"])],
        )
        self.style.configure(
            "TButton",
            background=palette["button"],
            foreground=palette["foreground"],
            bordercolor=palette["border"],
            focusthickness=1,
            focuscolor=palette["selection"],
        )
        self.style.map(
            "TButton",
            background=[
                ("active", palette["button_active"]),
                ("pressed", palette["button_active"]),
            ],
            foreground=[("disabled", palette["muted"])],
        )
        self.style.configure(
            "TCombobox",
            fieldbackground=palette["surface"],
            background=palette["button"],
            foreground=palette["foreground"],
            arrowcolor=palette["foreground"],
            bordercolor=palette["border"],
        )
        self.style.map(
            "TCombobox",
            fieldbackground=[("readonly", palette["surface"])],
            selectbackground=[("readonly", palette["surface"])],
            selectforeground=[("readonly", palette["foreground"])],
        )
        self.style.configure(
            "Horizontal.TScale",
            background=palette["background"],
            troughcolor=palette["surface"],
            bordercolor=palette["border"],
            lightcolor=palette["selection"],
            darkcolor=palette["selection"],
        )
        self.root.option_add("*TCombobox*Listbox.background", palette["surface"])
        self.root.option_add("*TCombobox*Listbox.foreground", palette["foreground"])
        self.root.option_add("*TCombobox*Listbox.selectBackground", palette["selection"])
        self.root.option_add("*TCombobox*Listbox.selectForeground", palette["selection_text"])

    def _configure_main_window_visuals(self, palette: dict[str, str], opacity: float) -> None:
        self.root.configure(background=palette["background"])
        self._apply_window_opacity(self.root, opacity)
        self.listbox.configure(
            background=palette["surface"],
            foreground=palette["foreground"],
            selectbackground=palette["selection"],
            selectforeground=palette["selection_text"],
            highlightbackground=palette["border"],
            highlightcolor=palette["selection"],
        )
        history_scrollbar = self.main_widgets.get("history_scrollbar")
        if isinstance(history_scrollbar, ModernScrollbar):
            history_scrollbar.configure_colors(
                track=palette["surface"],
                thumb=palette["muted"],
                active_thumb=palette["selection"],
            )
        self.item_menu.configure(
            background=palette["surface"],
            foreground=palette["foreground"],
            activebackground=palette["selection"],
            activeforeground=palette["selection_text"],
        )
        for key in ("monitoring_label", "status"):
            if key in self.main_widgets:
                self.main_widgets[key].configure(foreground=palette["muted"])

    def _configure_settings_window_visuals(self, palette: dict[str, str], opacity: float) -> None:
        if self.settings_window is None or not self.settings_window.winfo_exists():
            return

        self.settings_window.configure(background=palette["background"])
        self._apply_window_opacity(self.settings_window, opacity)
        for key in ("right_hint", "opacity_value_label"):
            if key in self.settings_widgets:
                self.settings_widgets[key].configure(foreground=palette["muted"])

        for key in (
            "font_size_spinbox",
            "window_width_spinbox",
            "window_height_spinbox",
            "max_items_spinbox",
        ):
            spinbox = self.settings_widgets.get(key)
            if not isinstance(spinbox, tk.Spinbox):
                continue
            try:
                spinbox.configure(
                    background=palette["surface"],
                    foreground=palette["foreground"],
                    buttonbackground=palette["button"],
                    insertbackground=palette["foreground"],
                    highlightbackground=palette["border"],
                    highlightcolor=palette["selection"],
                    selectbackground=palette["selection"],
                    selectforeground=palette["selection_text"],
                )
            except tk.TclError:
                spinbox.configure(
                    background=palette["surface"],
                    foreground=palette["foreground"],
                    insertbackground=palette["foreground"],
                    highlightbackground=palette["border"],
                    highlightcolor=palette["selection"],
                    selectbackground=palette["selection"],
                    selectforeground=palette["selection_text"],
                )

    @staticmethod
    def _apply_window_opacity(window: tk.Misc, opacity: float) -> None:
        effective_opacity = max(opacity, MIN_VISIBLE_WINDOW_OPACITY)
        try:
            window.attributes("-alpha", effective_opacity)  # type: ignore[attr-defined]
        except tk.TclError:
            pass

    def _on_opacity_scale_changed(self, _value: str) -> None:
        self._update_opacity_value_label()

    def _update_opacity_value_label(self) -> None:
        try:
            percent = round(float(self.opacity_var.get()))
        except tk.TclError:
            percent = 100
        percent = min(max(percent, 0), 100)
        self.opacity_value_var.set(self.tr("opacity_value", percent=percent))

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
        source = text[: MAX_PREVIEW_LENGTH * 4]
        single_line = " ".join(source.split())
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
        self._cancel_auto_hide_watch()
        self.root.update_idletasks()
        self._position_near_pointer(x, y)
        self.root.deiconify()
        self.root.update_idletasks()
        self.auto_hide_anchor_position = self._current_pointer_position()
        self._bring_window_to_front()
        self.status_var.set(self.tr("status_window_visible"))
        self._start_auto_hide_watch()

    def hide_window(self) -> None:
        self._cancel_auto_hide_watch()
        self.auto_hide_anchor_position = None
        self._capture_current_window_size()
        self._flush_window_size_save()
        self.root.withdraw()

    def _hide_when_minimized(self, _event: tk.Event) -> None:
        if self.root.state() == "iconic":
            self.root.after(0, self.hide_window)

    def _handle_root_configure(self, event: tk.Event) -> None:
        if (
            self.is_exiting
            or self.is_applying_window_size
            or event.widget is not self.root
            or self.root.state() != "normal"
        ):
            return

        self._capture_window_size(event.width, event.height)

    def _capture_current_window_size(self) -> None:
        if (
            self.is_exiting
            or self.is_applying_window_size
            or self.root.state() != "normal"
        ):
            return
        self._capture_window_size(self.root.winfo_width(), self.root.winfo_height())

    def _capture_window_size(self, width: int, height: int) -> None:
        width, height = self._normalize_window_size(width, height)
        if width == self.settings.window_width and height == self.settings.window_height:
            return

        self.settings = replace(self.settings, window_width=width, window_height=height)
        self.window_width_var.set(str(width))
        self.window_height_var.set(str(height))
        self._schedule_window_size_save()

    def _schedule_window_size_save(self) -> None:
        if self.window_size_save_after_id is not None:
            self.root.after_cancel(self.window_size_save_after_id)
        self.window_size_save_after_id = self.root.after(700, self._save_window_size_setting)

    def _save_window_size_setting(self) -> None:
        self.window_size_save_after_id = None
        try:
            save_settings(self.settings)
        except OSError:
            self.status_var.set(self.tr("status_settings_failed"))

    def _flush_window_size_save(self) -> None:
        if self.window_size_save_after_id is None:
            return
        try:
            self.root.after_cancel(self.window_size_save_after_id)
        except tk.TclError:
            pass
        self.window_size_save_after_id = None
        self._save_window_size_setting()

    def _cancel_window_size_save(self) -> None:
        if self.window_size_save_after_id is not None:
            try:
                self.root.after_cancel(self.window_size_save_after_id)
            except tk.TclError:
                pass
            self.window_size_save_after_id = None

    def _position_near_pointer(self, x: int | None, y: int | None) -> None:
        pointer_x, pointer_y = self._window_anchor_point(x, y)

        width, height = self._configured_window_size()
        bounds_x = self.root.winfo_vrootx()
        bounds_y = self.root.winfo_vrooty()
        bounds_width = self.root.winfo_vrootwidth()
        bounds_height = self.root.winfo_vrootheight()

        left = pointer_x - 36
        top = pointer_y - 36
        left, top = self._clamp_window_origin(
            left,
            top,
            width,
            height,
            bounds_x,
            bounds_y,
            bounds_width,
            bounds_height,
        )
        self.root.geometry(f"{width}x{height}+{left}+{top}")

    def _window_anchor_point(self, x: int | None, y: int | None) -> tuple[int, int]:
        if x is not None and y is not None:
            converted = self._convert_win32_point_to_tk_coordinates(x, y)
            if converted is not None:
                return converted
        return self.root.winfo_pointerx(), self.root.winfo_pointery()

    def _convert_win32_point_to_tk_coordinates(self, x: int, y: int) -> tuple[int, int] | None:
        tk_bounds = (
            self.root.winfo_vrootx(),
            self.root.winfo_vrooty(),
            self.root.winfo_vrootwidth(),
            self.root.winfo_vrootheight(),
        )
        if self._bounds_contain_point(x, y, tk_bounds):
            return (x, y)

        win32_bounds = self._win32_virtual_screen_bounds()
        if win32_bounds is None:
            return None

        return self._map_point_between_bounds(x, y, win32_bounds, tk_bounds)

    @staticmethod
    def _win32_virtual_screen_bounds() -> tuple[int, int, int, int] | None:
        try:
            import ctypes

            user32 = ctypes.windll.user32
            left = int(user32.GetSystemMetrics(76))
            top = int(user32.GetSystemMetrics(77))
            width = int(user32.GetSystemMetrics(78))
            height = int(user32.GetSystemMetrics(79))
        except (AttributeError, OSError):
            return None

        if width <= 0 or height <= 0:
            return None
        return (left, top, width, height)

    @staticmethod
    def _map_point_between_bounds(
        x: int,
        y: int,
        source_bounds: tuple[int, int, int, int],
        target_bounds: tuple[int, int, int, int],
    ) -> tuple[int, int] | None:
        source_x, source_y, source_width, source_height = source_bounds
        target_x, target_y, target_width, target_height = target_bounds
        if source_width <= 0 or source_height <= 0 or target_width <= 0 or target_height <= 0:
            return None

        mapped_x = target_x + round((x - source_x) * (target_width / source_width))
        mapped_y = target_y + round((y - source_y) * (target_height / source_height))
        return (mapped_x, mapped_y)

    @staticmethod
    def _bounds_contain_point(
        x: int,
        y: int,
        bounds: tuple[int, int, int, int],
    ) -> bool:
        left, top, width, height = bounds
        if width <= 0 or height <= 0:
            return False
        return left <= x < left + width and top <= y < top + height

    @staticmethod
    def _clamp_window_origin(
        left: int,
        top: int,
        width: int,
        height: int,
        bounds_x: int,
        bounds_y: int,
        bounds_width: int,
        bounds_height: int,
    ) -> tuple[int, int]:
        margin = WINDOW_SCREEN_MARGIN_PX
        min_left = bounds_x + margin
        min_top = bounds_y + margin
        max_left = bounds_x + max(0, bounds_width - width - margin)
        max_top = bounds_y + max(0, bounds_height - height - margin)

        if max_left < min_left:
            min_left = max_left = bounds_x
        if max_top < min_top:
            min_top = max_top = bounds_y

        return (
            min(max(left, min_left), max_left),
            min(max(top, min_top), max_top),
        )

    def _bring_window_to_front(self) -> None:
        try:
            self.root.attributes("-topmost", True)
        except tk.TclError:
            pass
        self.root.lift()
        self.root.focus_force()
        self.root.after(700, self._release_temporary_topmost)

    def _release_temporary_topmost(self) -> None:
        if self.is_exiting or self.root.state() != "normal":
            return
        try:
            self.root.attributes("-topmost", False)
        except tk.TclError:
            pass

    def _start_auto_hide_watch(self) -> None:
        self._cancel_auto_hide_watch()
        if not self.keep_open_var.get() and self.root.state() == "normal":
            self.auto_hide_after_id = self.root.after(
                AUTO_HIDE_INITIAL_DELAY_MS,
                self._auto_hide_if_pointer_left,
            )

    def _cancel_auto_hide_watch(self) -> None:
        if self.auto_hide_after_id is not None:
            self.root.after_cancel(self.auto_hide_after_id)
            self.auto_hide_after_id = None

    def _auto_hide_if_pointer_left(self) -> None:
        self.auto_hide_after_id = None
        if self.is_exiting or self.keep_open_var.get() or self.root.state() != "normal":
            return
        if self._is_primary_mouse_button_down():
            self.auto_hide_after_id = self.root.after(
                AUTO_HIDE_POLL_INTERVAL_MS,
                self._auto_hide_if_pointer_left,
            )
            return

        pointer_x, pointer_y = self._current_pointer_position()
        if self._pointer_is_outside_auto_hide_bounds(pointer_x, pointer_y):
            if self._pointer_has_not_moved_since_show(pointer_x, pointer_y):
                self.auto_hide_after_id = self.root.after(
                    AUTO_HIDE_POLL_INTERVAL_MS,
                    self._auto_hide_if_pointer_left,
                )
                return
            self.hide_window()
            return

        self.auto_hide_anchor_position = None
        self.auto_hide_after_id = self.root.after(
            AUTO_HIDE_POLL_INTERVAL_MS,
            self._auto_hide_if_pointer_left,
        )

    def _pointer_is_outside_auto_hide_bounds(self, pointer_x: int, pointer_y: int) -> bool:
        bounds = self._outer_window_bounds()
        if bounds is None:
            bounds = (
                self.root.winfo_rootx(),
                self.root.winfo_rooty(),
                self.root.winfo_width(),
                self.root.winfo_height(),
            )
        return self._point_is_outside_bounds(pointer_x, pointer_y, bounds, AUTO_HIDE_MARGIN_PX)

    def _outer_window_bounds(self) -> tuple[int, int, int, int] | None:
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = int(self.root.winfo_id())
            user32 = ctypes.windll.user32
            user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user32.GetAncestor.restype = wintypes.HWND
            user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
            user32.GetWindowRect.restype = wintypes.BOOL
            root_hwnd = user32.GetAncestor(hwnd, 2) or hwnd
            rect = wintypes.RECT()
            if not user32.GetWindowRect(root_hwnd, ctypes.byref(rect)):
                return None
        except (AttributeError, OSError, tk.TclError, ValueError):
            return None

        width = int(rect.right - rect.left)
        height = int(rect.bottom - rect.top)
        if width <= 0 or height <= 0:
            return None
        return int(rect.left), int(rect.top), width, height

    @staticmethod
    def _point_is_outside_bounds(
        pointer_x: int,
        pointer_y: int,
        bounds: tuple[int, int, int, int],
        margin: int,
    ) -> bool:
        left, top, width, height = bounds
        right = left + width
        bottom = top + height
        return (
            pointer_x < left - margin
            or pointer_x > right + margin
            or pointer_y < top - margin
            or pointer_y > bottom + margin
        )

    def _current_pointer_position(self) -> tuple[int, int]:
        return (self.root.winfo_pointerx(), self.root.winfo_pointery())

    def _pointer_has_not_moved_since_show(self, pointer_x: int, pointer_y: int) -> bool:
        if self.auto_hide_anchor_position is None:
            return False
        return not self._point_moved(
            self.auto_hide_anchor_position,
            (pointer_x, pointer_y),
            AUTO_HIDE_STILL_POINTER_TOLERANCE_PX,
        )

    @staticmethod
    def _point_moved(
        origin: tuple[int, int],
        current: tuple[int, int],
        tolerance_px: int,
    ) -> bool:
        return (
            abs(current[0] - origin[0]) > tolerance_px
            or abs(current[1] - origin[1]) > tolerance_px
        )

    @staticmethod
    def _is_primary_mouse_button_down() -> bool:
        try:
            import ctypes

            return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        except (AttributeError, OSError):
            return False

    def exit_app(self) -> None:
        self.is_exiting = True
        self._cancel_auto_hide_watch()
        self._cancel_clipboard_suppression_timer()
        self._flush_window_size_save()
        self.host.stop()
        self.root.destroy()
