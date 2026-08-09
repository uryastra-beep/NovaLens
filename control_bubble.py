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
from runtime_control import (
    ACTION_CLOSE_POPUP,
    ACTION_OPEN_POPUP,
    ACTION_RESTART_APP,
    escribir_accion_runtime,
)


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

    page.title = "Nova Lens Controls"
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

    page.add(
        contenedor
    )

    try:
        await page.window.wait_until_ready_to_show()
    except Exception:
        pass

    page.window.visible = True
    page.update()

    try:
        await page.window.to_front()
    except Exception:
        pass

    registrar_latido(archivo_salud)
    ultimo_latido = time.monotonic()
    ultimo_estado: bool | None = None
    while True:
        ahora = time.monotonic()
        if ahora - ultimo_latido >= 1.0:
            registrar_latido(archivo_salud)
            ultimo_latido = ahora

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
