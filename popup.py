"""Development entry point for the packaged Nova Lens text popup.

The popup implementation lives in ``popup_exe.py`` for both source and frozen
builds. Keeping this file as a thin entry point prevents the two launch paths
from drifting into different geometry, animation, and visibility behavior.
"""

from __future__ import annotations

import flet as ft

from popup_exe import main


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
