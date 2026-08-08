from __future__ import annotations

import asyncio
import ctypes
import math
import os
from typing import Any


DISPLAY_MODES = {"normal", "compact"}
COMPACT_WIDTH = 720
MINIMUM_WIDTH = 420

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
RDW_INVALIDATE = 0x0001
RDW_ALLCHILDREN = 0x0080
RDW_UPDATENOW = 0x0100
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def logical_to_physical_geometry(
    left: int,
    top: int,
    width: int,
    height: int,
    dpi: int,
) -> tuple[int, int, int, int]:
    """Convert Flet virtual pixels to Win32 pixels for one monitor DPI."""
    try:
        scale = max(96, int(dpi)) / 96.0
    except (TypeError, ValueError, OverflowError):
        scale = 1.0

    return (
        round(int(left) * scale),
        round(int(top) * scale),
        max(1, round(int(width) * scale)),
        max(1, round(int(height) * scale)),
    )


def snap_native_window_geometry(
    title: str,
    left: int,
    top: int,
    width: int,
    height: int,
) -> bool:
    """Resize a Flet window instantly, bypassing its animated size change.

    Flet's Windows client starts every desktop surface at 1280x720 and its
    public size setter animates the transition. A large animated transition to
    a short transparent popup can leave Flutter's raster surface compressed
    while hit testing already uses the final viewport. SetWindowPos delivers
    one WM_SIZE instead and keeps the rendered surface and input geometry in
    the same coordinate system.
    """
    if os.name != "nt" or not str(title or "").strip():
        return False

    user32 = ctypes.windll.user32
    previous_context = None

    try:
        find_window = user32.FindWindowW
        find_window.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        find_window.restype = ctypes.c_void_p
        hwnd = find_window(None, str(title))
        if not hwnd:
            return False

        try:
            set_thread_dpi = user32.SetThreadDpiAwarenessContext
            set_thread_dpi.argtypes = [ctypes.c_void_p]
            set_thread_dpi.restype = ctypes.c_void_p
            previous_context = set_thread_dpi(
                ctypes.c_void_p(
                    DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
                )
            )
        except Exception:
            previous_context = None

        try:
            dpi = int(user32.GetDpiForWindow(hwnd))
        except Exception:
            try:
                dpi = int(user32.GetDpiForSystem())
            except Exception:
                dpi = 96

        native_geometry = logical_to_physical_geometry(
            left,
            top,
            width,
            height,
            dpi,
        )

        set_window_pos = user32.SetWindowPos
        set_window_pos.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_uint,
        ]
        set_window_pos.restype = ctypes.c_bool
        applied = bool(
            set_window_pos(
                hwnd,
                None,
                *native_geometry,
                SWP_NOZORDER | SWP_NOACTIVATE,
            )
        )

        if applied:
            try:
                user32.RedrawWindow(
                    hwnd,
                    None,
                    None,
                    RDW_INVALIDATE | RDW_ALLCHILDREN | RDW_UPDATENOW,
                )
            except Exception:
                pass

        return applied

    except Exception:
        return False
    finally:
        if previous_context:
            try:
                user32.SetThreadDpiAwarenessContext(previous_context)
            except Exception:
                pass


async def wait_and_snap_native_window_geometry(
    title: str,
    left: int,
    top: int,
    width: int,
    height: int,
    attempts: int = 40,
    interval: float = 0.025,
) -> bool:
    """Wait for Flet's HWND and apply one non-animated native geometry."""
    for _ in range(max(1, int(attempts))):
        if snap_native_window_geometry(title, left, top, width, height):
            return True
        await asyncio.sleep(max(0.01, float(interval)))

    return False


def apply_popup_window_geometry(
    window: Any,
    left: int,
    top: int,
    width: int,
    height: int,
    minimum_height: int,
    maximum_height: int,
) -> tuple[int, int, int, int]:
    """Restore a frameless popup and apply one bounded window geometry."""
    safe_width = max(MINIMUM_WIDTH, int(width))
    safe_minimum_height = max(1, int(minimum_height))
    safe_maximum_height = max(safe_minimum_height, int(maximum_height))
    safe_height = max(
        safe_minimum_height,
        min(int(height), safe_maximum_height),
    )
    safe_left = int(left)
    safe_top = int(top)

    # Windows can restore a hidden Flet window as maximized. Width and height
    # updates are ignored while that state is active, so clear it every time
    # before applying the requested bounds.
    window.full_screen = False
    window.maximized = False
    window.maximizable = False
    window.resizable = False
    # Width is fixed for each popup process. Height remains within a stable
    # range so response changes do not repeatedly invert equal min/max limits.
    window.min_width = safe_width
    window.max_width = safe_width
    window.min_height = safe_minimum_height
    window.max_height = safe_maximum_height
    window.width = safe_width
    window.height = safe_height
    window.left = safe_left
    window.top = safe_top

    return safe_left, safe_top, safe_width, safe_height


def normalize_display_mode(value: Any) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in DISPLAY_MODES else "normal"


def calculate_popup_horizontal_geometry(
    work_left: int,
    work_width: int,
    margin: int,
    display_mode: str,
) -> tuple[int, int]:
    """Return a safe left coordinate and width for the selected display mode."""
    safe_margin = max(0, int(margin))
    available_width = max(
        MINIMUM_WIDTH,
        int(work_width) - safe_margin * 2,
    )

    if normalize_display_mode(display_mode) == "compact":
        popup_width = min(COMPACT_WIDTH, available_width)
        popup_left = (
            int(work_left)
            + safe_margin
            + max(0, (available_width - popup_width) // 2)
        )
        return popup_left, popup_width

    return int(work_left) + safe_margin, available_width


def popup_viewport_matches(
    actual_width: Any,
    actual_height: Any,
    expected_width: int,
    expected_height: int,
    tolerance: float = 4.0,
) -> bool:
    """Return whether Flet's rendered viewport matches the requested bounds."""
    try:
        width = float(actual_width)
        height = float(actual_height)
        allowed_delta = max(0.0, float(tolerance))
    except (TypeError, ValueError):
        return False

    if not all(math.isfinite(value) for value in (width, height, allowed_delta)):
        return False

    return (
        abs(width - float(expected_width)) <= allowed_delta
        and abs(height - float(expected_height)) <= allowed_delta
    )
