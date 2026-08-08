from __future__ import annotations

from typing import Any


DISPLAY_MODES = {"normal", "compact"}
COMPACT_WIDTH = 720
MINIMUM_WIDTH = 420


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


def apply_popup_width_constraints(window: Any, width: int) -> int:
    """Pin a frameless popup to one width before its first rendered frame."""
    safe_width = max(MINIMUM_WIDTH, int(width))

    # Flet can restore a desktop window using its default/maximized viewport
    # before a later width update arrives. Pinning every width property keeps
    # the native window and Flutter surface in the same coordinate space.
    window.full_screen = False
    window.maximized = False
    window.min_width = safe_width
    window.max_width = safe_width
    window.width = safe_width
    return safe_width
