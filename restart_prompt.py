from __future__ import annotations

import asyncio
import os
import webbrowser

import flet as ft

from config_manager import cargar_configuracion, color_con_transparencia
from localization import tr
from reporting import build_bug_report_url


async def main(page: ft.Page) -> None:
    config = cargar_configuracion()
    apariencia = config["appearance"]

    page.title = tr("restart_report_title")
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.Colors.TRANSPARENT
    page.padding = 0

    page.window.width = 480
    page.window.height = 210
    page.window.min_width = 480
    page.window.max_width = 480
    page.window.min_height = 210
    page.window.max_height = 210
    page.window.resizable = False
    page.window.maximizable = False
    page.window.always_on_top = True
    page.window.skip_task_bar = False
    page.window.visible = False

    async def cerrar(e=None) -> None:
        try:
            await page.window.destroy()
        except Exception:
            try:
                page.window.visible = False
                page.update()
            except Exception:
                pass

        await asyncio.sleep(0.05)
        os._exit(0)

    async def reportar(e=None) -> None:
        try:
            webbrowser.open(build_bug_report_url(), new=2)
        except Exception:
            pass
        await cerrar()

    panel = ft.Container(
        expand=True,
        bgcolor=color_con_transparencia(
            apariencia["primary_color"],
            apariencia["transparency"],
        ),
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=ft.BorderRadius.all(20),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        padding=24,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.RESTART_ALT_ROUNDED,
                            color=apariencia["secondary_color"],
                            size=32,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    tr("restart_complete"),
                                    color=apariencia["text_color"],
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                ),
                                ft.Text(
                                    tr("restart_report_question"),
                                    color=apariencia["secondary_color"],
                                    size=14,
                                ),
                            ],
                            spacing=3,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            content=tr("no"),
                            on_click=cerrar,
                        ),
                        ft.Button(
                            content=tr("report_error"),
                            icon=ft.Icons.BUG_REPORT_ROUNDED,
                            bgcolor=apariencia["border_color"],
                            color=apariencia["text_color"],
                            on_click=reportar,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    spacing=10,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    page.add(panel)

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


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
