from __future__ import annotations

import ctypes
import os

import flet as ft

import popup


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def obtener_area_trabajo_virtual() -> tuple[int, int, int, int]:
    """Return the Windows work area using Flet virtual pixels.

    Packaged Windows executables are DPI-aware, so Win32 reports physical
    pixels while Flet positions windows using virtual pixels. Mixing both
    coordinate systems can place most of the popup outside the screen.
    """

    if os.name != "nt":
        return 0, 0, 1280, 720

    rect = RECT()

    try:
        resultado = ctypes.windll.user32.SystemParametersInfoW(
            0x0030,
            0,
            ctypes.byref(rect),
            0,
        )

        if resultado:
            try:
                dpi = int(ctypes.windll.user32.GetDpiForSystem())
            except Exception:
                dpi = 96

            escala = max(dpi / 96.0, 1.0)

            izquierda = round(rect.left / escala)
            arriba = round(rect.top / escala)
            ancho = round((rect.right - rect.left) / escala)
            alto = round((rect.bottom - rect.top) / escala)

            return izquierda, arriba, ancho, alto
    except Exception:
        pass

    try:
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        dpi = 96

    escala = max(dpi / 96.0, 1.0)

    ancho = round(ctypes.windll.user32.GetSystemMetrics(0) / escala)
    alto = round(ctypes.windll.user32.GetSystemMetrics(1) / escala)
    return 0, 0, ancho, alto


# popup.py is also used directly during development. Override packaged-only
# behavior so the source workflow remains unchanged.
popup.obtener_area_trabajo = obtener_area_trabajo_virtual

# In the packaged Flet app, the slide offset can occasionally remain at its
# hidden position after an interrupted animation. The window keeps its normal
# size, but almost the entire popup content is translated outside the window,
# leaving only a thin strip visible. Keep the fade animation and disable only
# the packaged slide translation.
popup.DESPLAZAMIENTO_INICIAL = 0.0


if __name__ == "__main__":
    ft.run(
        popup.main,
        view=ft.AppView.FLET_APP_HIDDEN,
    )
