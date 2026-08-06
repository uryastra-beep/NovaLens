from __future__ import annotations

import asyncio
import ctypes
import os
from ctypes import wintypes

import flet as ft

import popup


WINDOW_TITLE = "Nova Lens"


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def obtener_area_trabajo_fisica() -> tuple[int, int, int, int]:
    """Return the primary Windows work area in native pixels."""

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
            return (
                int(rect.left),
                int(rect.top),
                int(rect.right - rect.left),
                int(rect.bottom - rect.top),
            )
    except Exception:
        pass

    return (
        0,
        0,
        int(ctypes.windll.user32.GetSystemMetrics(0)),
        int(ctypes.windll.user32.GetSystemMetrics(1)),
    )


def obtener_escala_dpi(hwnd: int | None = None) -> float:
    if os.name != "nt":
        return 1.0

    dpi = 96

    if hwnd:
        try:
            dpi = int(ctypes.windll.user32.GetDpiForWindow(hwnd))
        except Exception:
            pass

    if dpi <= 0:
        try:
            dpi = int(ctypes.windll.user32.GetDpiForSystem())
        except Exception:
            dpi = 96

    return max(dpi / 96.0, 1.0)


def obtener_area_trabajo_virtual() -> tuple[int, int, int, int]:
    """Return the Windows work area using Flet virtual pixels."""

    izquierda, arriba, ancho, alto = obtener_area_trabajo_fisica()
    escala = obtener_escala_dpi()

    return (
        round(izquierda / escala),
        round(arriba / escala),
        round(ancho / escala),
        round(alto / escala),
    )


def obtener_titulo_ventana(hwnd: int) -> str:
    if os.name != "nt":
        return ""

    user32 = ctypes.windll.user32

    try:
        longitud = int(user32.GetWindowTextLengthW(hwnd))
        buffer = ctypes.create_unicode_buffer(max(longitud + 1, 2))
        user32.GetWindowTextW(hwnd, buffer, len(buffer))
        return buffer.value.strip()
    except Exception:
        return ""


def encontrar_ventana_novalens() -> int | None:
    """Find the Flet window even when it belongs to another process.

    In packaged Flet apps, the desktop window can be owned by the Flet client
    process instead of the Python child process. Selecting only windows owned
    by os.getpid() therefore misses the real popup and leaves the collapsed
    native window untouched.
    """

    if os.name != "nt":
        return None

    user32 = ctypes.windll.user32
    process_id = os.getpid()
    candidatos_titulo_visibles: list[tuple[int, int]] = []
    candidatos_titulo: list[tuple[int, int]] = []
    candidatos_proceso: list[tuple[int, int]] = []

    callback_type = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @callback_type
    def enumerar(hwnd, _lparam):
        rect = RECT()

        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        ancho = max(0, int(rect.right - rect.left))
        alto = max(0, int(rect.bottom - rect.top))
        area = ancho * alto

        if area <= 0:
            return True

        titulo = obtener_titulo_ventana(int(hwnd))
        visible = bool(user32.IsWindowVisible(hwnd))

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        candidato = (area, int(hwnd))

        if titulo == WINDOW_TITLE:
            candidatos_titulo.append(candidato)

            if visible:
                candidatos_titulo_visibles.append(candidato)

        if pid.value == process_id:
            candidatos_proceso.append(candidato)

        return True

    try:
        user32.EnumWindows(enumerar, 0)
    except Exception:
        return None

    for candidatos in (
        candidatos_titulo_visibles,
        candidatos_titulo,
        candidatos_proceso,
    ):
        if candidatos:
            candidatos.sort(reverse=True)
            return candidatos[0][1]

    return None


def forzar_geometria_nativa(page: ft.Page) -> bool:
    """Force the real Win32 window rectangle, bypassing Flet size races."""

    if os.name != "nt":
        return False

    hwnd = encontrar_ventana_novalens()

    if not hwnd:
        return False

    escala = obtener_escala_dpi(hwnd)
    izquierda, arriba, ancho_area, alto_area = obtener_area_trabajo_fisica()

    margen = max(0, round(float(popup.MARGEN_PANTALLA) * escala))

    try:
        ancho_virtual = float(page.window.width or 0)
    except (TypeError, ValueError):
        ancho_virtual = 0

    try:
        alto_virtual = float(page.window.height or popup.ALTURA_MINIMA)
    except (TypeError, ValueError):
        alto_virtual = float(popup.ALTURA_MINIMA)

    alto_virtual = max(
        float(popup.ALTURA_MINIMA),
        min(alto_virtual, float(popup.ALTURA_MAXIMA)),
    )

    ancho_objetivo = (
        round(ancho_virtual * escala)
        if ancho_virtual > 0
        else ancho_area - margen * 2
    )
    alto_objetivo = round(alto_virtual * escala)

    ancho_disponible = max(420, ancho_area - margen * 2)
    alto_disponible = max(
        round(popup.ALTURA_MINIMA * escala),
        alto_area - margen * 2,
    )

    ancho_objetivo = max(420, min(ancho_objetivo, ancho_disponible))
    alto_objetivo = max(
        round(popup.ALTURA_MINIMA * escala),
        min(alto_objetivo, alto_disponible),
    )

    x = izquierda + margen

    if popup.POSICION_POPUP == "bottom":
        y = arriba + alto_area - alto_objetivo - margen
    else:
        y = arriba + margen

    HWND_TOPMOST = -1
    SWP_NOACTIVATE = 0x0010
    SWP_NOOWNERZORDER = 0x0200
    SWP_FRAMECHANGED = 0x0020
    SWP_SHOWWINDOW = 0x0040

    try:
        resultado = ctypes.windll.user32.SetWindowPos(
            hwnd,
            HWND_TOPMOST,
            int(x),
            int(y),
            int(ancho_objetivo),
            int(alto_objetivo),
            SWP_NOACTIVATE
            | SWP_NOOWNERZORDER
            | SWP_FRAMECHANGED
            | SWP_SHOWWINDOW,
        )
        return bool(resultado)
    except Exception:
        return False


async def vigilar_geometria(page: ft.Page) -> None:
    """Keep the packaged native window synced with Nova Lens geometry."""

    await asyncio.sleep(0.20)

    while True:
        try:
            if bool(page.window.visible):
                forzar_geometria_nativa(page)
        except Exception:
            pass

        await asyncio.sleep(0.05)


async def main_empaquetado(page: ft.Page) -> None:
    await popup.main(page)
    asyncio.create_task(vigilar_geometria(page))


# popup.py is also used directly during development. Override packaged-only
# behavior so the source workflow remains unchanged.
popup.obtener_area_trabajo = obtener_area_trabajo_virtual

# Disable the packaged slide translation. The native guard below also forces
# the real Win32 rectangle while the popup is visible.
popup.DESPLAZAMIENTO_INICIAL = 0.0


if __name__ == "__main__":
    ft.run(
        main_empaquetado,
        view=ft.AppView.FLET_APP_HIDDEN,
    )
