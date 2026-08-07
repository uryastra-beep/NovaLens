from __future__ import annotations

import asyncio
import ctypes
import os
import sys

import flet as ft

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
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        rect = RECT()
        try:
            if ctypes.windll.user32.SystemParametersInfoW(
                0x0030,
                0,
                ctypes.byref(rect),
                0,
            ):
                return (
                    int(rect.left),
                    int(rect.top),
                    int(rect.right - rect.left),
                    int(rect.bottom - rect.top),
                )
        except Exception:
            pass

    return 0, 0, 1280, 720


async def main(page: ft.Page) -> None:
    config = cargar_configuracion()
    apariencia = config["appearance"]
    audio = config["audio"]
    duracion = audio["duration_seconds"]

    if len(sys.argv) >= 2:
        try:
            duracion = max(3, min(30, int(sys.argv[1])))
        except (TypeError, ValueError):
            pass

    izquierda, arriba, ancho, alto = obtener_area_trabajo()
    ancho_indicador = 124
    alto_indicador = 34
    margen = max(8, int(apariencia["margin"]))

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
    page.window.left = izquierda + ancho - ancho_indicador - margen
    page.window.top = (
        arriba + alto - alto_indicador - margen
        if apariencia["position"] == "top"
        else arriba + margen
    )
    page.window.ignore_mouse_events = True
    page.window.visible = False

    fondo = color_con_transparencia(
        apariencia["primary_color"],
        min(35, apariencia["transparency"]),
    )

    page.add(
        ft.Container(
            expand=True,
            bgcolor=fondo,
            border=ft.Border.all(1, apariencia["border_color"]),
            border_radius=17,
            padding=ft.Padding(left=11, right=11, top=5, bottom=5),
            content=ft.Row(
                controls=[
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
    )
    page.window.visible = True
    page.update()

    try:
        await page.window.to_front()
    except Exception:
        pass

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
