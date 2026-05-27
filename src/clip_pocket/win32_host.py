from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable

from ctypes import wintypes

from clip_pocket.constants import (
    APP_NAME,
    CTRL_DOUBLE_TAP_INTERVAL_MS,
    HIDDEN_WINDOW_CLASS,
    RIGHT_CLICK_SEQUENCE_COUNT,
    RIGHT_CLICK_SEQUENCE_DISTANCE_PX,
    RIGHT_CLICK_SEQUENCE_INTERVAL_MS,
)
from clip_pocket.i18n import normalize_language, text


class WindowsEventType(Enum):
    CLIPBOARD_CHANGED = auto()
    SHOW_WINDOW = auto()
    OPEN_SETTINGS = auto()
    TOGGLE_PAUSE = auto()
    EXIT_REQUESTED = auto()
    WARNING = auto()


@dataclass(frozen=True)
class WindowsEvent:
    type: WindowsEventType
    message: str = ""
    x: int | None = None
    y: int | None = None


class Guid(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NotifyIconData(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HANDLE),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", Guid),
        ("hBalloonIcon", wintypes.HANDLE),
    ]


WndProcFactory = getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE)

WndProcType = WndProcFactory(
    getattr(wintypes, "LRESULT", ctypes.c_ssize_t),
    wintypes.HWND,
    wintypes.UINT,
    getattr(wintypes, "WPARAM", ctypes.c_size_t),
    getattr(wintypes, "LPARAM", ctypes.c_ssize_t),
)


class WindowClass(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WndProcType),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class Message(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", getattr(wintypes, "WPARAM", ctypes.c_size_t)),
        ("lParam", getattr(wintypes, "LPARAM", ctypes.c_ssize_t)),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


class LowLevelMouseEvent(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)),
    ]


class LowLevelKeyboardEvent(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", getattr(wintypes, "ULONG_PTR", ctypes.c_size_t)),
    ]


LowLevelMouseProcType = WndProcFactory(
    getattr(wintypes, "LRESULT", ctypes.c_ssize_t),
    ctypes.c_int,
    getattr(wintypes, "WPARAM", ctypes.c_size_t),
    getattr(wintypes, "LPARAM", ctypes.c_ssize_t),
)


LowLevelKeyboardProcType = WndProcFactory(
    getattr(wintypes, "LRESULT", ctypes.c_ssize_t),
    ctypes.c_int,
    getattr(wintypes, "WPARAM", ctypes.c_size_t),
    getattr(wintypes, "LPARAM", ctypes.c_ssize_t),
)


def is_double_ctrl_tap(
    previous_time_ms: int | None,
    current_time_ms: int,
    *,
    interval_ms: int = CTRL_DOUBLE_TAP_INTERVAL_MS,
) -> bool:
    if previous_time_ms is None:
        return False

    elapsed_ms = (current_time_ms - previous_time_ms) % (2**32)
    return 0 < elapsed_ms <= interval_ms


def next_click_sequence_count(
    previous_count: int,
    previous_time_ms: int | None,
    previous_position: tuple[int, int] | None,
    current_time_ms: int,
    current_position: tuple[int, int],
    *,
    interval_ms: int = RIGHT_CLICK_SEQUENCE_INTERVAL_MS,
    distance_px: int = RIGHT_CLICK_SEQUENCE_DISTANCE_PX,
) -> int:
    if previous_time_ms is None or previous_position is None:
        return 1

    elapsed_ms = (current_time_ms - previous_time_ms) % (2**32)
    if elapsed_ms == 0 or elapsed_ms > interval_ms:
        return 1

    previous_x, previous_y = previous_position
    current_x, current_y = current_position
    if abs(current_x - previous_x) > distance_px or abs(current_y - previous_y) > distance_px:
        return 1

    return previous_count + 1


def tray_event_from_lparam(lparam: int) -> int:
    return int(lparam) & 0xFFFF


class SingleInstance:
    ERROR_ALREADY_EXISTS = 183

    def __init__(self, name: str) -> None:
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        self.kernel32.CreateMutexW.restype = wintypes.HANDLE
        self.kernel32.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.kernel32.ReleaseMutex.restype = wintypes.BOOL
        self.kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel32.CloseHandle.restype = wintypes.BOOL

        self.handle = self.kernel32.CreateMutexW(None, True, name)
        self.already_running = ctypes.get_last_error() == self.ERROR_ALREADY_EXISTS
        self.owns_mutex = bool(self.handle) and not self.already_running

    def close(self) -> None:
        if self.handle:
            if self.owns_mutex:
                self.kernel32.ReleaseMutex(self.handle)
            self.kernel32.CloseHandle(self.handle)
            self.handle = None
            self.owns_mutex = False


class WindowsHost:
    WM_NULL = 0x0000
    WM_DESTROY = 0x0002
    WM_CONTEXTMENU = 0x007B
    WM_RBUTTONUP = 0x0205
    WM_LBUTTONUP = 0x0202
    WM_LBUTTONDBLCLK = 0x0203
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    WM_USER = 0x0400
    WM_APP = 0x8000
    WM_TRAYICON = WM_USER + 25
    WM_STOP = WM_APP + 1
    WM_SHOW_REQUEST = WM_APP + 2
    WM_OPTIONS_CHANGED = WM_APP + 3
    WM_CLIPBOARDUPDATE = 0x031D
    NIN_SELECT = WM_USER
    NIN_KEYSELECT = WM_USER + 1

    HC_ACTION = 0
    WH_MOUSE_LL = 14
    WH_KEYBOARD_LL = 13

    VK_CONTROL = 0x11
    VK_LCONTROL = 0xA2
    VK_RCONTROL = 0xA3

    IDI_APPLICATION = 32512
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040

    NIM_ADD = 0x00000000
    NIM_DELETE = 0x00000002
    NIM_SETVERSION = 0x00000004
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004
    NOTIFYICON_VERSION_4 = 4

    MF_STRING = 0x00000000
    MF_SEPARATOR = 0x00000800
    TPM_RIGHTBUTTON = 0x0002
    TPM_RETURNCMD = 0x0100

    MENU_OPEN = 1
    MENU_SETTINGS = 2
    MENU_PAUSE = 3
    MENU_EXIT = 4

    def __init__(
        self,
        emit: Callable[[WindowsEvent], None],
        *,
        ctrl_double_tap_enabled: bool = True,
        right_triple_click_enabled: bool = False,
        language: str = "en",
        icon_path: str | None = None,
    ) -> None:
        self.emit = emit
        self.hwnd: int | None = None
        self.instance: int | None = None
        self.notification_data: NotifyIconData | None = None
        self.clipboard_listener_registered = False
        self.keyboard_hook_registered = False
        self.keyboard_hook: int | None = None
        self.mouse_hook_registered = False
        self.mouse_hook: int | None = None
        self.ctrl_double_tap_enabled = ctrl_double_tap_enabled
        self.right_triple_click_enabled = right_triple_click_enabled
        self.language = normalize_language(language)
        self.paused = False
        self.icon_path = icon_path
        self.tray_icon_handle: int | None = None
        self.ctrl_is_down = False
        self.ctrl_tap_contaminated = False
        self.last_ctrl_tap_time_ms: int | None = None
        self.right_click_count = 0
        self.last_right_click_time_ms: int | None = None
        self.last_right_click_position: tuple[int, int] | None = None
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, name="ClipPocketWin32Host", daemon=True)

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.wnd_proc = WndProcType(self._wnd_proc)
        self.mouse_proc = LowLevelMouseProcType(self._mouse_proc)
        self.keyboard_proc = LowLevelKeyboardProcType(self._keyboard_proc)
        self._configure_api()

    def _configure_api(self) -> None:
        lresult = getattr(wintypes, "LRESULT", ctypes.c_ssize_t)
        wparam = getattr(wintypes, "WPARAM", ctypes.c_size_t)
        lparam = getattr(wintypes, "LPARAM", ctypes.c_ssize_t)

        self.kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self.kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        self.user32.RegisterClassW.argtypes = [ctypes.POINTER(WindowClass)]
        self.user32.RegisterClassW.restype = wintypes.ATOM
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        self.user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wparam, lparam]
        self.user32.DefWindowProcW.restype = lresult
        self.user32.DestroyWindow.argtypes = [wintypes.HWND]
        self.user32.DestroyWindow.restype = wintypes.BOOL
        self.user32.GetMessageW.argtypes = [
            ctypes.POINTER(Message),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        self.user32.GetMessageW.restype = wintypes.BOOL
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(Message)]
        self.user32.TranslateMessage.restype = wintypes.BOOL
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(Message)]
        self.user32.DispatchMessageW.restype = lresult
        self.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wparam, lparam]
        self.user32.PostMessageW.restype = wintypes.BOOL
        self.user32.PostQuitMessage.argtypes = [ctypes.c_int]
        self.user32.PostQuitMessage.restype = None

        self.user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        self.user32.LoadIconW.restype = wintypes.HICON
        self.user32.LoadImageW.argtypes = [
            wintypes.HINSTANCE,
            wintypes.LPCWSTR,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.UINT,
        ]
        self.user32.LoadImageW.restype = wintypes.HANDLE
        self.user32.DestroyIcon.argtypes = [wintypes.HICON]
        self.user32.DestroyIcon.restype = wintypes.BOOL
        self.user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL

        self.user32.CreatePopupMenu.argtypes = []
        self.user32.CreatePopupMenu.restype = wintypes.HMENU
        self.user32.AppendMenuW.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_size_t,
            wintypes.LPCWSTR,
        ]
        self.user32.AppendMenuW.restype = wintypes.BOOL
        self.user32.TrackPopupMenu.argtypes = [
            wintypes.HMENU,
            wintypes.UINT,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.LPVOID,
        ]
        self.user32.TrackPopupMenu.restype = wintypes.UINT
        self.user32.DestroyMenu.argtypes = [wintypes.HMENU]
        self.user32.DestroyMenu.restype = wintypes.BOOL

        self.user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        self.user32.SetWindowsHookExW.restype = wintypes.HANDLE
        self.user32.CallNextHookEx.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            wparam,
            lparam,
        ]
        self.user32.CallNextHookEx.restype = lresult
        self.user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
        self.user32.UnhookWindowsHookEx.restype = wintypes.BOOL

        self.user32.AddClipboardFormatListener.argtypes = [wintypes.HWND]
        self.user32.AddClipboardFormatListener.restype = wintypes.BOOL
        self.user32.RemoveClipboardFormatListener.argtypes = [wintypes.HWND]
        self.user32.RemoveClipboardFormatListener.restype = wintypes.BOOL

        self.shell32.Shell_NotifyIconW.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(NotifyIconData),
        ]
        self.shell32.Shell_NotifyIconW.restype = wintypes.BOOL

    def start(self) -> None:
        self.thread.start()
        if not self.ready.wait(timeout=5):
            raise RuntimeError("Timed out while starting the Windows host.")

    def stop(self) -> None:
        if self.hwnd:
            self.user32.PostMessageW(self.hwnd, self.WM_STOP, 0, 0)
        if self.thread.is_alive():
            self.thread.join(timeout=3)

    def _run(self) -> None:
        instance = self.kernel32.GetModuleHandleW(None)
        self.instance = int(instance)

        window_class = WindowClass()
        window_class.lpfnWndProc = self.wnd_proc
        window_class.hInstance = instance
        window_class.lpszClassName = HIDDEN_WINDOW_CLASS

        self.user32.RegisterClassW(ctypes.byref(window_class))
        hwnd = self.user32.CreateWindowExW(
            0,
            HIDDEN_WINDOW_CLASS,
            APP_NAME,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            self.ready.set()
            self.emit(
                WindowsEvent(
                    WindowsEventType.WARNING,
                    self.tr("warning_windows_host"),
                )
            )
            return

        self.hwnd = int(hwnd)
        self._register_clipboard_listener()
        self._sync_hooks()
        self._add_tray_icon()
        self.ready.set()

        message = Message()
        while self.user32.GetMessageW(ctypes.byref(message), None, 0, 0) != 0:
            self.user32.TranslateMessage(ctypes.byref(message))
            self.user32.DispatchMessageW(ctypes.byref(message))

    def _wnd_proc(self, hwnd: int, message: int, wparam: int, lparam: int) -> int:
        if message == self.WM_CLIPBOARDUPDATE:
            self.emit(WindowsEvent(WindowsEventType.CLIPBOARD_CHANGED))
            return 0

        if message == self.WM_TRAYICON:
            tray_event = tray_event_from_lparam(lparam)
            if tray_event in (self.WM_LBUTTONUP, self.WM_LBUTTONDBLCLK, self.NIN_SELECT):
                self.emit(self._show_event_at_cursor())
                return 0
            if tray_event in (self.WM_RBUTTONUP, self.WM_CONTEXTMENU, self.NIN_KEYSELECT):
                self._show_tray_menu(hwnd)
                return 0

        if message == self.WM_STOP:
            self.user32.DestroyWindow(hwnd)
            return 0

        if message == self.WM_SHOW_REQUEST:
            self.emit(self._show_event_at_cursor())
            return 0

        if message == self.WM_OPTIONS_CHANGED:
            self._sync_hooks()
            return 0

        if message == self.WM_DESTROY:
            self._cleanup(hwnd)
            self.user32.PostQuitMessage(0)
            return 0

        return int(self.user32.DefWindowProcW(hwnd, message, wparam, lparam))

    def _register_clipboard_listener(self) -> None:
        if self.hwnd and self.user32.AddClipboardFormatListener(self.hwnd):
            self.clipboard_listener_registered = True
        else:
            self.emit(
                WindowsEvent(
                    WindowsEventType.WARNING,
                    self.tr("warning_clipboard_listener"),
                )
            )

    def set_shortcut_options(
        self,
        *,
        ctrl_double_tap_enabled: bool,
        right_triple_click_enabled: bool,
    ) -> None:
        self.ctrl_double_tap_enabled = ctrl_double_tap_enabled
        self.right_triple_click_enabled = right_triple_click_enabled
        self._reset_ctrl_sequence()
        self._reset_right_click_sequence()
        if self.hwnd:
            self.user32.PostMessageW(self.hwnd, self.WM_OPTIONS_CHANGED, 0, 0)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused

    def _sync_hooks(self) -> None:
        if self.ctrl_double_tap_enabled and not self.keyboard_hook_registered:
            self._register_keyboard_hook()
        elif not self.ctrl_double_tap_enabled and self.keyboard_hook_registered:
            self._unregister_keyboard_hook()

        if self.right_triple_click_enabled and not self.mouse_hook_registered:
            self._register_mouse_hook()
        elif not self.right_triple_click_enabled and self.mouse_hook_registered:
            self._unregister_mouse_hook()

    def _register_keyboard_hook(self) -> None:
        hook = self.user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            ctypes.cast(self.keyboard_proc, ctypes.c_void_p),
            self.instance or 0,
            0,
        )
        if hook:
            self.keyboard_hook = int(hook)
            self.keyboard_hook_registered = True
        else:
            self.emit(
                WindowsEvent(
                    WindowsEventType.WARNING,
                    self.tr("warning_ctrl_hook"),
                )
            )

    def _unregister_keyboard_hook(self) -> None:
        if self.keyboard_hook_registered and self.keyboard_hook:
            self.user32.UnhookWindowsHookEx(self.keyboard_hook)
        self.keyboard_hook_registered = False
        self.keyboard_hook = None
        self._reset_ctrl_sequence()

    def _register_mouse_hook(self) -> None:
        hook = self.user32.SetWindowsHookExW(
            self.WH_MOUSE_LL,
            ctypes.cast(self.mouse_proc, ctypes.c_void_p),
            self.instance or 0,
            0,
        )
        if hook:
            self.mouse_hook = int(hook)
            self.mouse_hook_registered = True
        else:
            self.emit(
                WindowsEvent(
                    WindowsEventType.WARNING,
                    self.tr("warning_mouse_hook"),
                )
            )

    def _unregister_mouse_hook(self) -> None:
        if self.mouse_hook_registered and self.mouse_hook:
            self.user32.UnhookWindowsHookEx(self.mouse_hook)
        self.mouse_hook_registered = False
        self.mouse_hook = None
        self._reset_right_click_sequence()

    def _keyboard_proc(self, code: int, wparam: int, lparam: int) -> int:
        if code == self.HC_ACTION and self.ctrl_double_tap_enabled and lparam:
            event = ctypes.cast(lparam, ctypes.POINTER(LowLevelKeyboardEvent)).contents
            message = int(wparam)
            key = int(event.vkCode)

            if message in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN):
                if self._is_ctrl_key(key):
                    if not self.ctrl_is_down:
                        self.ctrl_is_down = True
                        self.ctrl_tap_contaminated = False
                elif self.ctrl_is_down:
                    self.ctrl_tap_contaminated = True
                    self.last_ctrl_tap_time_ms = None

            elif message in (self.WM_KEYUP, self.WM_SYSKEYUP) and self._is_ctrl_key(key):
                if self.ctrl_is_down and not self.ctrl_tap_contaminated:
                    event_time = int(event.time)
                    if is_double_ctrl_tap(self.last_ctrl_tap_time_ms, event_time):
                        self._reset_ctrl_sequence()
                        self.emit(self._show_event_at_cursor())
                    else:
                        self.last_ctrl_tap_time_ms = event_time
                        self.ctrl_is_down = False
                else:
                    self._reset_ctrl_sequence()

        return int(self.user32.CallNextHookEx(self.keyboard_hook or 0, code, wparam, lparam))

    def _mouse_proc(self, code: int, wparam: int, lparam: int) -> int:
        if (
            code == self.HC_ACTION
            and self.right_triple_click_enabled
            and int(wparam) == self.WM_RBUTTONUP
            and lparam
        ):
            event = ctypes.cast(lparam, ctypes.POINTER(LowLevelMouseEvent)).contents
            position = (int(event.pt.x), int(event.pt.y))
            event_time = int(event.time)

            self.right_click_count = next_click_sequence_count(
                self.right_click_count,
                self.last_right_click_time_ms,
                self.last_right_click_position,
                event_time,
                position,
            )
            self.last_right_click_time_ms = event_time
            self.last_right_click_position = position

            if self.right_click_count >= RIGHT_CLICK_SEQUENCE_COUNT:
                self._reset_right_click_sequence()
                self.emit(
                    WindowsEvent(
                        WindowsEventType.SHOW_WINDOW,
                        x=position[0],
                        y=position[1],
                    )
                )

        return int(self.user32.CallNextHookEx(self.mouse_hook or 0, code, wparam, lparam))

    def _is_ctrl_key(self, key: int) -> bool:
        return key in (self.VK_CONTROL, self.VK_LCONTROL, self.VK_RCONTROL)

    def _reset_ctrl_sequence(self) -> None:
        self.ctrl_is_down = False
        self.ctrl_tap_contaminated = False
        self.last_ctrl_tap_time_ms = None

    def _reset_right_click_sequence(self) -> None:
        self.right_click_count = 0
        self.last_right_click_time_ms = None
        self.last_right_click_position = None

    def _show_event_at_cursor(self) -> WindowsEvent:
        point = wintypes.POINT()
        if self.user32.GetCursorPos(ctypes.byref(point)):
            return WindowsEvent(WindowsEventType.SHOW_WINDOW, x=int(point.x), y=int(point.y))
        return WindowsEvent(WindowsEventType.SHOW_WINDOW)

    def _add_tray_icon(self) -> None:
        if not self.hwnd:
            return

        data = NotifyIconData()
        data.cbSize = ctypes.sizeof(NotifyIconData)
        data.hWnd = self.hwnd
        data.uID = 1
        data.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        data.uCallbackMessage = self.WM_TRAYICON
        data.hIcon = self._load_icon()
        data.szTip = APP_NAME

        if not self.shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(data)):
            self.emit(
                WindowsEvent(
                    WindowsEventType.WARNING,
                    self.tr("warning_tray_icon"),
                )
            )
            return

        data.uTimeoutOrVersion = self.NOTIFYICON_VERSION_4
        self.shell32.Shell_NotifyIconW(self.NIM_SETVERSION, ctypes.byref(data))
        self.notification_data = data

    def _load_icon(self) -> int:
        if self.icon_path:
            icon = self.user32.LoadImageW(
                None,
                self.icon_path,
                self.IMAGE_ICON,
                0,
                0,
                self.LR_LOADFROMFILE | self.LR_DEFAULTSIZE,
            )
            if icon:
                self.tray_icon_handle = int(icon)
                return int(icon)

        return int(self.user32.LoadIconW(None, ctypes.c_void_p(self.IDI_APPLICATION)))

    def _show_tray_menu(self, hwnd: int) -> None:
        menu = self.user32.CreatePopupMenu()
        if not menu:
            return

        self.user32.AppendMenuW(menu, self.MF_STRING, self.MENU_OPEN, self.tr("menu_open"))
        self.user32.AppendMenuW(
            menu,
            self.MF_STRING,
            self.MENU_SETTINGS,
            self.tr("menu_settings"),
        )
        pause_label = self.tr("menu_resume") if self.paused else self.tr("menu_pause")
        self.user32.AppendMenuW(menu, self.MF_STRING, self.MENU_PAUSE, pause_label)
        self.user32.AppendMenuW(menu, self.MF_SEPARATOR, 0, None)
        self.user32.AppendMenuW(menu, self.MF_STRING, self.MENU_EXIT, self.tr("menu_exit"))

        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        self.user32.SetForegroundWindow(hwnd)
        command = self.user32.TrackPopupMenu(
            menu,
            self.TPM_RIGHTBUTTON | self.TPM_RETURNCMD,
            point.x,
            point.y,
            0,
            hwnd,
            None,
        )
        self.user32.DestroyMenu(menu)
        self.user32.PostMessageW(hwnd, self.WM_NULL, 0, 0)

        if command == self.MENU_OPEN:
            self.emit(self._show_event_at_cursor())
        elif command == self.MENU_SETTINGS:
            self.emit(WindowsEvent(WindowsEventType.OPEN_SETTINGS))
        elif command == self.MENU_PAUSE:
            self.emit(WindowsEvent(WindowsEventType.TOGGLE_PAUSE))
        elif command == self.MENU_EXIT:
            self.emit(WindowsEvent(WindowsEventType.EXIT_REQUESTED))

    def _cleanup(self, hwnd: int) -> None:
        self._unregister_mouse_hook()
        self._unregister_keyboard_hook()

        if self.clipboard_listener_registered:
            self.user32.RemoveClipboardFormatListener(hwnd)
            self.clipboard_listener_registered = False

        if self.notification_data is not None:
            self.shell32.Shell_NotifyIconW(
                self.NIM_DELETE,
                ctypes.byref(self.notification_data),
            )
            self.notification_data = None

        if self.tray_icon_handle:
            self.user32.DestroyIcon(self.tray_icon_handle)
            self.tray_icon_handle = None

    def tr(self, key: str) -> str:
        return text(self.language, key)


def request_existing_instance_window() -> bool:
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user32.FindWindowW.restype = wintypes.HWND
    user32.PostMessageW.argtypes = [
        wintypes.HWND,
        wintypes.UINT,
        getattr(wintypes, "WPARAM", ctypes.c_size_t),
        getattr(wintypes, "LPARAM", ctypes.c_ssize_t),
    ]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.MessageBoxW.argtypes = [
        wintypes.HWND,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.UINT,
    ]
    user32.MessageBoxW.restype = ctypes.c_int

    hwnd = user32.FindWindowW(HIDDEN_WINDOW_CLASS, APP_NAME)
    if hwnd:
        return bool(user32.PostMessageW(hwnd, WindowsHost.WM_SHOW_REQUEST, 0, 0))

    user32.MessageBoxW(
        None,
        f"{APP_NAME} is already running.",
        APP_NAME,
        0x40,
    )
    return False
