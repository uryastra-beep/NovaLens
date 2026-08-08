from __future__ import annotations

import math
from typing import Any


DISPLAY_MODES = {"normal", "compact"}
COMPACT_WIDTH = 720
MINIMUM_WIDTH = 420


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
    # Pin both dimensions to the requested viewport. Leaving a range here
    # allows Windows/Flet to restore an older hidden-window size that is still
    # technically valid (for example 720x378 instead of 720x165). Flutter then
    # lays out the expanded popup against one surface while Windows displays
    # another, which clips the UI into a thin strip.
    window.min_width = safe_width
    window.max_width = safe_width
    window.min_height = safe_height
    window.max_height = safe_height
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
