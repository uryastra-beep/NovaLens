from __future__ import annotations

import asyncio
import ctypes
import os
import sys
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


async def main(page: ft.Page) -> None:
    config = cargar_configuracion()
    apariencia = config["appearance"]
    audio = config["audio"]
    posicion_guardada = config["bubble_positions"]["audio"]
    duracion = audio["duration_seconds"]
    archivo_desbloqueo = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
    archivo_posicion = Path(sys.argv[3]) if len(sys.argv) >= 4 else None

    if len(sys.argv) >= 2:
        try:
            duracion = max(3, min(30, int(sys.argv[1])))
        except (TypeError, ValueError):
            pass

    izquierda, arriba, ancho, alto = obtener_area_trabajo()
    ancho_indicador = 146
    alto_indicador = 34
    margen = max(8, int(apariencia["margin"]))
    posicion_predeterminada = (
        izquierda + ancho - ancho_indicador - margen,
        (
            arriba + alto - alto_indicador - margen
            if apariencia["position"] == "top"
            else arriba + margen
        ),
    )
    posicion_inicial = resolver_posicion(
        posicion_guardada,
        posicion_predeterminada,
        obtener_escritorio_virtual((izquierda, arriba, ancho, alto)),
        (ancho_indicador, alto_indicador),
    )

    page.title = "Nova Lens Microphone"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = ft.Colors.TRANSPARENT

    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.frameless = True
    page.window.always_on_top = True
    page.window.skip_task_bar = True
    page.window.resizable = False
    page.window.shadow = False
    page.window.width = ancho_indicador
    page.window.height = alto_indicador
    page.window.left = posicion_inicial[0]
    page.window.top = posicion_inicial[1]
    page.window.ignore_mouse_events = not leer_estado_desbloqueo(
        archivo_desbloqueo
    )
    page.window.visible = False

    fondo = color_con_transparencia(
        apariencia["primary_color"],
        min(35, apariencia["transparency"]),
    )
    indicador_arrastre = ft.Icon(
        ft.Icons.DRAG_INDICATOR_ROUNDED,
        size=14,
        color=apariencia["secondary_color"],
        visible=leer_estado_desbloqueo(archivo_desbloqueo),
    )

    contenedor = ft.Container(
        expand=True,
        bgcolor=fondo,
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=17,
        padding=ft.Padding(left=11, right=11, top=5, bottom=5),
        content=ft.Row(
            controls=[
                indicador_arrastre,
                ft.Container(
                    width=9,
                    height=9,
                    bgcolor="#FF6B6B",
                    border_radius=5,
                ),
                ft.Icon(
                    ft.Icons.MIC_ROUNDED,
                    size=15,
                    color=apariencia["text_color"],
                ),
                ft.Text(
                    tr("mic_indicator").format(seconds=duracion),
                    size=11,
                    color=apariencia["text_color"],
                    weight=ft.FontWeight.W_600,
                ),
            ],
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

    async def guardar_posicion_arrastrada(e=None) -> None:
        await asyncio.sleep(0.08)
        posicion = obtener_posicion_ventana_proceso(page.title)
        if posicion is None:
            posicion = (
                int(page.window.left or posicion_inicial[0]),
                int(page.window.top or posicion_inicial[1]),
            )
        escribir_posicion(archivo_posicion, *posicion)

    page.add(
        ft.WindowDragArea(
            expand=True,
            maximizable=False,
            on_drag_end=guardar_posicion_arrastrada,
            content=contenedor,
        )
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

    ultimo_estado: bool | None = None
    while True:
        desbloqueado = leer_estado_desbloqueo(archivo_desbloqueo)
        if desbloqueado != ultimo_estado:
            ultimo_estado = desbloqueado
            page.window.ignore_mouse_events = not desbloqueado
            indicador_arrastre.visible = desbloqueado
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
