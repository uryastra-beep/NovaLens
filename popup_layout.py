from __future__ import annotations

import math
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
