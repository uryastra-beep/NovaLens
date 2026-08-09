from __future__ import annotations

import asyncio
import ctypes
import os
import sys
import time
from pathlib import Path


def _preparar_dpi_temprano() -> None:
    if os.name != "nt":
        return

    try:
        establecer = ctypes.windll.user32.SetProcessDpiAwarenessContext
        establecer.restype = ctypes.c_bool
        if establecer(ctypes.c_void_p(-4)):
            return
    except Exception:
        pass

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass


_preparar_dpi_temprano()

import flet as ft

from bubble_layout import (
    convertir_rectangulo_a_logico,
    escribir_posicion,
    leer_estado_desbloqueo,
    obtener_escala_dpi_sistema,
    obtener_escritorio_virtual,
    obtener_posicion_ventana_proceso,
    resolver_posicion,
)
from config_manager import cargar_configuracion, color_con_transparencia
from localization import tr
from popup_layout import wait_and_snap_native_window_geometry
from runtime_control import (
    ACTION_CLOSE_POPUP,
    ACTION_OPEN_POPUP,
    ACTION_RESTART_APP,
    escribir_accion_runtime,
)


TITULO_VENTANA = "Nova Lens Controls"
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def obtener_area_trabajo() -> tuple[int, int, int, int]:
    if os.name == "nt":
        rect = RECT()

        try:
            if ctypes.windll.user32.SystemParametersInfoW(
                0x0030,
                0,
                ctypes.byref(rect),
                0,
            ):
                return convertir_rectangulo_a_logico(
                    int(rect.left),
                    int(rect.top),
                    int(rect.right - rect.left),
                    int(rect.bottom - rect.top),
                    obtener_escala_dpi_sistema(),
                )
        except Exception:
            pass

    return 0, 0, 1280, 720


def registrar_latido(ruta: Path) -> None:
    try:
        ruta.touch()
    except OSError:
        pass


def forzar_ventana_visible_nativa(titulo: str) -> bool:
    """Show the bubble's HWND without stealing focus on Windows.

    Flet can keep a frameless hidden app alive and responsive even when its
    native window never becomes visible. A heartbeat alone cannot detect that
    state, so explicitly restore and show the HWND after the first layout.
    """
    if os.name != "nt" or not str(titulo or "").strip():
        return False

    try:
        user32 = ctypes.windll.user32
        encontrar = user32.FindWindowW
        encontrar.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
        encontrar.restype = ctypes.c_void_p
        hwnd = encontrar(None, str(titulo))
        if not hwnd:
            return False

        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) != os.getpid():
            return False

        user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
        mostrado = bool(
            user32.SetWindowPos(
                hwnd,
                ctypes.c_void_p(HWND_TOPMOST),
                0,
                0,
                0,
                0,
                SWP_NOMOVE
                | SWP_NOSIZE
                | SWP_NOACTIVATE
                | SWP_SHOWWINDOW,
            )
        )
        return mostrado and bool(user32.IsWindowVisible(hwnd))
    except Exception:
        return False


async def asegurar_ventana_visible_nativa(
    titulo: str,
    intentos: int = 30,
    intervalo: float = 0.05,
) -> bool:
    """Wait briefly for Flet's HWND and force it visible when available."""
    if os.name != "nt":
        return True

    for _ in range(max(1, int(intentos))):
        if forzar_ventana_visible_nativa(titulo):
            return True
        await asyncio.sleep(max(0.01, float(intervalo)))

    return False


async def main(page: ft.Page) -> None:
    if len(sys.argv) < 5:
        raise SystemExit(
            "Usage: control_bubble.py "
            "<action-file> <unlock-file> <position-file> <health-file>"
        )

    archivo_acciones = Path(sys.argv[1])
    archivo_desbloqueo = Path(sys.argv[2])
    archivo_posicion = Path(sys.argv[3])
    archivo_salud = Path(sys.argv[4])
    config = cargar_configuracion()
    apariencia = config["appearance"]
    posicion_guardada = config["bubble_positions"]["control"]

    izquierda, arriba, ancho, alto = obtener_area_trabajo()
    ancho_burbuja = 374
    alto_burbuja = 58
    margen = max(8, int(apariencia["margin"]))
    posicion_predeterminada = (
        izquierda + margen,
        arriba + alto - alto_burbuja - margen,
    )
    posicion_inicial = resolver_posicion(
        posicion_guardada,
        posicion_predeterminada,
        obtener_escritorio_virtual((izquierda, arriba, ancho, alto)),
        (ancho_burbuja, alto_burbuja),
    )

    page.title = TITULO_VENTANA
    page.padding = 0
    page.spacing = 0
    page.bgcolor = ft.Colors.TRANSPARENT

    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.frameless = True
    page.window.always_on_top = True
    page.window.skip_task_bar = True
    page.window.resizable = False
    page.window.shadow = False
    page.window.width = ancho_burbuja
    page.window.height = alto_burbuja
    page.window.min_width = ancho_burbuja
    page.window.max_width = ancho_burbuja
    page.window.min_height = alto_burbuja
    page.window.max_height = alto_burbuja
    page.window.left = posicion_inicial[0]
    page.window.top = posicion_inicial[1]
    page.window.visible = False

    fondo = color_con_transparencia(
        apariencia["primary_color"],
        apariencia["transparency"],
    )
    fondo_boton = color_con_transparencia(
        apariencia["border_color"],
        28,
    )

    def abrir_popup(e=None) -> None:
        escribir_accion_runtime(archivo_acciones, ACTION_OPEN_POPUP)

    def cerrar_popup(e=None) -> None:
        escribir_accion_runtime(archivo_acciones, ACTION_CLOSE_POPUP)

    def reiniciar_app(e=None) -> None:
        escribir_accion_runtime(archivo_acciones, ACTION_RESTART_APP)

    async def guardar_posicion_arrastrada(e=None) -> None:
        await asyncio.sleep(0.08)
        posicion = obtener_posicion_ventana_proceso(page.title)
        if posicion is None:
            posicion = (
                int(page.window.left or posicion_inicial[0]),
                int(page.window.top or posicion_inicial[1]),
            )
        escribir_posicion(archivo_posicion, *posicion)

    asa_arrastre = ft.WindowDragArea(
        visible=False,
        maximizable=False,
        on_drag_end=guardar_posicion_arrastrada,
        content=ft.Container(
            width=24,
            height=40,
            alignment=ft.Alignment.CENTER,
            border_radius=12,
            bgcolor=fondo_boton,
            content=ft.Icon(
                ft.Icons.DRAG_INDICATOR_ROUNDED,
                size=18,
                color=apariencia["secondary_color"],
            ),
        ),
    )

    contenedor = ft.Container(
        expand=True,
        bgcolor=fondo,
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=29,
        padding=ft.Padding(left=7, right=7, top=6, bottom=6),
        content=ft.Row(
            controls=[
                asa_arrastre,
                ft.Button(
                    width=104,
                    height=40,
                    content=ft.Text(tr("bubble_open")),
                    icon=ft.Icons.OPEN_IN_NEW_ROUNDED,
                    bgcolor=fondo_boton,
                    color=apariencia["text_color"],
                    on_click=abrir_popup,
                ),
                ft.Button(
                    width=104,
                    height=40,
                    content=ft.Text(tr("bubble_close")),
                    icon=ft.Icons.CLOSE_ROUNDED,
                    bgcolor=fondo_boton,
                    color=apariencia["text_color"],
                    on_click=cerrar_popup,
                ),
                ft.Button(
                    width=104,
                    height=40,
                    content=ft.Text(tr("bubble_reset")),
                    icon=ft.Icons.RESTART_ALT_ROUNDED,
                    bgcolor=fondo_boton,
                    color=apariencia["text_color"],
                    on_click=reiniciar_app,
                ),
            ],
            spacing=5,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    page.add(contenedor)
    page.update()

    # Start the heartbeat before waiting for the desktop client. Otherwise a
    # slow first Flet frame can make the supervisor restart a healthy child.
    registrar_latido(archivo_salud)

    try:
        await asyncio.wait_for(
            page.window.wait_until_ready_to_show(),
            timeout=4.0,
        )
    except Exception:
        pass

    # Avoid Flet's animated resize from its initial 1280x720 surface to this
    # short frameless window. This is the same native geometry strategy used
    # by the stable text popup.
    await wait_and_snap_native_window_geometry(
        page.title,
        posicion_inicial[0],
        posicion_inicial[1],
        ancho_burbuja,
        alto_burbuja,
    )

    page.window.visible = True
    page.update()

    await asegurar_ventana_visible_nativa(page.title)

    try:
        await page.window.to_front()
    except Exception:
        pass

    ultimo_latido = time.monotonic()
    ultimo_forzado_visibilidad = 0.0
    ultimo_estado: bool | None = None
    while True:
        ahora = time.monotonic()
        if ahora - ultimo_latido >= 1.0:
            registrar_latido(archivo_salud)
            ultimo_latido = ahora

        if ahora - ultimo_forzado_visibilidad >= 2.0:
            forzar_ventana_visible_nativa(page.title)
            ultimo_forzado_visibilidad = ahora

        desbloqueado = leer_estado_desbloqueo(archivo_desbloqueo)
        if desbloqueado != ultimo_estado:
            ultimo_estado = desbloqueado
            asa_arrastre.visible = desbloqueado
            contenedor.border = ft.Border.all(
                2 if desbloqueado else 1,
                (
                    apariencia["secondary_color"]
                    if desbloqueado
                    else apariencia["border_color"]
                ),
            )
            page.update()
        await asyncio.sleep(0.15)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
