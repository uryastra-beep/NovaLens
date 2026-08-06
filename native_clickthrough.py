from __future__ import annotations

import ctypes
import os
import threading
import time
from ctypes import wintypes


GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
LWA_ALPHA = 0x00000002


def _find_process_window() -> int | None:
    if os.name != "nt":
        return None

    user32 = ctypes.windll.user32
    current_pid = os.getpid()
    result: list[int] = []

    enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @enum_proc
    def callback(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        if pid.value != current_pid:
            return True

        # The popup is a real top-level Flet window. Ignore child/tool windows.
        if user32.GetParent(hwnd):
            return True

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        if rect.right - rect.left < 100 or rect.bottom - rect.top < 50:
            return True

        result.append(hwnd)
        return False

    user32.EnumWindows(callback, 0)
    return result[0] if result else None


def _window_alpha(hwnd: int) -> int | None:
    user32 = ctypes.windll.user32
    color_key = wintypes.DWORD()
    alpha = ctypes.c_ubyte(255)
    flags = wintypes.DWORD()

    ok = user32.GetLayeredWindowAttributes(
        hwnd,
        ctypes.byref(color_key),
        ctypes.byref(alpha),
        ctypes.byref(flags),
    )

    if not ok or not (flags.value & LWA_ALPHA):
        return None

    return int(alpha.value)


def _set_click_through(hwnd: int, enabled: bool) -> None:
    user32 = ctypes.windll.user32

    get_style = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
    set_style = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

    style = int(get_style(hwnd, GWL_EXSTYLE))

    if enabled:
        new_style = style | WS_EX_TRANSPARENT
    else:
        new_style = style & ~WS_EX_TRANSPARENT

    if new_style != style:
        set_style(hwnd, GWL_EXSTYLE, new_style)


def _watch_popup_window() -> None:
    hwnd: int | None = None
    last_state: bool | None = None

    while True:
        try:
            if hwnd is None or not ctypes.windll.user32.IsWindow(hwnd):
                hwnd = _find_process_window()
                last_state = None

            if hwnd is None:
                time.sleep(0.10)
                continue

            alpha = _window_alpha(hwnd)

            # Flet uses zero native opacity when the resident popup is hidden.
            # Force the Win32 transparent hit-test style so the invisible
            # window can never block clicks, even if Flet's property lags.
            click_through = alpha == 0

            if click_through != last_state:
                _set_click_through(hwnd, click_through)
                last_state = click_through

        except Exception:
            hwnd = None
            last_state = None

        time.sleep(0.05)


def start_native_clickthrough_watch() -> None:
    """Start one daemon watcher for the packaged Windows popup process."""

    if os.name != "nt":
        return

    thread = threading.Thread(
        target=_watch_popup_window,
        name="NovaLensNativeClickThrough",
        daemon=True,
    )
    thread.start()
