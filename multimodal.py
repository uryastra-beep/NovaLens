from __future__ import annotations

import asyncio
import argparse
import ctypes
import math
import os
import re
import sys
import time
from pathlib import Path

import flet as ft

from backend import analizar_captura_pantalla, transcribir_y_responder_audio
from bubble_layout import (
    convertir_rectangulo_a_logico,
    obtener_escala_dpi_sistema,
)
from config_manager import (
    cargar_configuracion,
    color_con_transparencia,
)
from localization import tr
from popup_layout import (
    apply_popup_window_geometry,
    wait_and_snap_native_window_geometry,
)
from screen_selector import seleccionar_region_pantalla_jpeg


if len(sys.argv) < 2 or sys.argv[1].lower() not in {"screen", "audio"}:
    raise SystemExit("Usage: multimodal.py screen|audio [audio-file]")

MODO = sys.argv[1].lower()
ARCHIVO_AUDIO: Path | None = None
ERROR_AUDIO = ""
AUDIO_DURATION = 10

if MODO == "audio":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("audio_file", nargs="?")
    parser.add_argument("--error", default="")
    parser.add_argument("--duration", type=int, default=10)
    argumentos = parser.parse_args(sys.argv[2:])
    ERROR_AUDIO = argumentos.error
    AUDIO_DURATION = max(3, min(30, argumentos.duration))
    if argumentos.audio_file:
        ARCHIVO_AUDIO = Path(argumentos.audio_file)

CONFIGURACION = cargar_configuracion()
APARIENCIA = CONFIGURACION["appearance"]
COMPORTAMIENTO = CONFIGURACION["behavior"]

COLOR_PRINCIPAL = APARIENCIA["primary_color"]
COLOR_FONDO = color_con_transparencia(
    COLOR_PRINCIPAL,
    APARIENCIA["transparency"],
)
COLOR_TEXTO = APARIENCIA["text_color"]
COLOR_SECUNDARIO = APARIENCIA["secondary_color"]
COLOR_BORDE = APARIENCIA["border_color"]

TAMANO_FUENTE = APARIENCIA["font_size"]
RADIO_BORDES = APARIENCIA["border_radius"]
MARGEN_PANTALLA = APARIENCIA["margin"]
POSICION_POPUP = APARIENCIA["position"]
TIEMPO_VISIBLE = COMPORTAMIENTO["visible_seconds"]

ALTURA_MINIMA = 150
ALTURA_MAXIMA = 420
ALTURA_CONTROLES_FIJOS = 104
ALTURA_RESPUESTA_MINIMA = 32
DURACION_SALIDA_MS = 520
TITULO_VENTANA = f"Nova Lens {MODO.title()} Popup"


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
            resultado = ctypes.windll.user32.SystemParametersInfoW(
                0x0030,
                0,
                ctypes.byref(rect),
                0,
            )

            if resultado:
                return convertir_rectangulo_a_logico(
                    int(rect.left),
                    int(rect.top),
                    int(rect.right - rect.left),
                    int(rect.bottom - rect.top),
                    obtener_escala_dpi_sistema(),
                )
        except Exception:
            pass

        return convertir_rectangulo_a_logico(
            0,
            0,
            int(ctypes.windll.user32.GetSystemMetrics(0)),
            int(ctypes.windll.user32.GetSystemMetrics(1)),
            obtener_escala_dpi_sistema(),
        )

    return 0, 0, 1280, 720


def limpiar_markdown_basico(texto: str) -> str:
    texto = re.sub(r"```(?:\w+)?\n?(.*?)```", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", texto)
    texto = re.sub(r"`([^`]*)`", r"\1", texto)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^\s*[-*]\s+", "• ", texto, flags=re.MULTILINE)
    return texto.strip()


def calcular_altura(texto: str, ancho: int) -> int:
    espacio_texto = max(ancho - 120, 300)
    caracteres_por_linea = max(
        30,
        int(espacio_texto / (TAMANO_FUENTE * 0.55)),
    )
    lineas = 0

    for parrafo in texto.splitlines() or [""]:
        lineas += max(
            1,
            math.ceil(len(parrafo) / caracteres_por_linea),
        )

    altura = 118 + lineas * (TAMANO_FUENTE + 7)
    return max(ALTURA_MINIMA, min(altura, ALTURA_MAXIMA))


def calcular_altura_respuesta(altura_popup: int | float) -> int:
    altura_segura = max(
        ALTURA_MINIMA,
        min(int(round(altura_popup)), ALTURA_MAXIMA),
    )
    return max(
        ALTURA_RESPUESTA_MINIMA,
        altura_segura - ALTURA_CONTROLES_FIJOS,
    )


def crear_zona_respuesta(
    texto: ft.Text,
    altura_popup: int | float,
    on_scroll,
) -> ft.ListView:
    # Frameless Flet windows need an explicit viewport for wheel scrolling.
    return ft.ListView(
        controls=[texto],
        height=calcular_altura_respuesta(altura_popup),
        build_controls_on_demand=False,
        scroll=ft.ScrollMode.ALWAYS,
        scroll_interval=50,
        on_scroll=on_scroll,
    )


def leer_audio_temporal() -> bytes:
    if ARCHIVO_AUDIO is None:
        return b""

    try:
        return ARCHIVO_AUDIO.read_bytes()
    finally:
        try:
            ARCHIVO_AUDIO.unlink(missing_ok=True)
        except OSError:
            pass


async def main(page: ft.Page) -> None:
    izquierda, arriba, ancho_area, alto_area = obtener_area_trabajo()
    ancho_popup = max(420, ancho_area - MARGEN_PANTALLA * 2)

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
    page.window.visible = False

    respuesta_actual = ""
    cerrando = False
    ultima_interaccion = time.monotonic()
    altura_ventana_actual = ALTURA_MINIMA

    def geometria_popup(altura: int | float) -> tuple[int, int, int, int]:
        altura_segura = max(
            ALTURA_MINIMA,
            min(int(round(float(altura))), ALTURA_MAXIMA),
        )
        top = (
            arriba + alto_area - altura_segura - MARGEN_PANTALLA
            if POSICION_POPUP == "bottom"
            else arriba + MARGEN_PANTALLA
        )
        return (
            izquierda + MARGEN_PANTALLA,
            top,
            ancho_popup,
            altura_segura,
        )

    async def ajustar_geometria(altura: int | float) -> int:
        left, top, width, height = geometria_popup(altura)
        if await wait_and_snap_native_window_geometry(
            TITULO_VENTANA,
            left,
            top,
            width,
            height,
        ):
            await asyncio.sleep(0.05)
            return height

        apply_popup_window_geometry(
            page.window,
            left,
            top,
            width,
            height,
            ALTURA_MINIMA,
            ALTURA_MAXIMA,
        )
        page.update()
        await asyncio.sleep(0.05)
        return height

    def registrar_interaccion(e=None) -> None:
        nonlocal ultima_interaccion
        ultima_interaccion = time.monotonic()

    texto_respuesta = ft.Text(
        tr("preparing"),
        color=COLOR_TEXTO,
        size=TAMANO_FUENTE,
        selectable=True,
    )
    mensaje_estado = ft.Text(
        "",
        color=COLOR_SECUNDARIO,
        size=12,
    )
    indicador = ft.ProgressRing(
        width=15,
        height=15,
        stroke_width=2,
        color=COLOR_TEXTO,
        visible=True,
    )
    texto_copiar = ft.Text(
        tr("copy"),
        color=COLOR_TEXTO,
        weight=ft.FontWeight.W_600,
    )

    async def cerrar() -> None:
        nonlocal cerrando

        if cerrando:
            return

        cerrando = True
        popup.opacity = 0
        popup.update()
        await asyncio.sleep(DURACION_SALIDA_MS / 1000)

        try:
            await page.window.destroy()
        except Exception:
            pass

        os._exit(0)

    async def copiar(e=None) -> None:
        registrar_interaccion()
        try:
            await ft.Clipboard().set(respuesta_actual)
            texto_copiar.value = tr("copied")
            mensaje_estado.value = tr("copy_done")
        except Exception:
            mensaje_estado.value = tr("copy_failed")

        page.update()

    async def boton_cerrar(e=None) -> None:
        await cerrar()

    async def mostrar_ventana() -> None:
        await ajustar_geometria(altura_ventana_actual)
        page.window.visible = True
        page.window.focused = True
        page.update()

        try:
            await page.window.to_front()
        except Exception:
            pass

        popup.opacity = 0
        popup.update()
        await asyncio.sleep(0.04)
        popup.opacity = 1
        popup.update()
        registrar_interaccion()

    async def actualizar_resultado(texto: str) -> None:
        nonlocal respuesta_actual
        nonlocal altura_ventana_actual

        respuesta_actual = (
            (texto or "").strip()
            or tr("no_text")
        )
        limpio = limpiar_markdown_basico(respuesta_actual)
        texto_respuesta.value = limpio
        indicador.visible = False
        mensaje_estado.value = tr("response_ready")

        altura_ventana_actual = calcular_altura(limpio, ancho_popup)
        zona_respuesta.height = calcular_altura_respuesta(
            altura_ventana_actual
        )

        registrar_interaccion()
        page.update()
        await ajustar_geometria(altura_ventana_actual)

        try:
            await zona_respuesta.scroll_to(offset=0, duration=1)
        except Exception:
            pass

    async def esperar_inactividad() -> None:
        while not cerrando:
            restante = TIEMPO_VISIBLE - (time.monotonic() - ultima_interaccion)
            if restante <= 0:
                await cerrar()
                return
            await asyncio.sleep(min(0.5, restante))

    encabezado = ft.Row(
        controls=[
            ft.Text(
                "Nova Lens",
                color=COLOR_TEXTO,
                size=max(18, TAMANO_FUENTE + 2),
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                tr("screen_audio"),
                color=COLOR_SECUNDARIO,
                size=12,
            ),
            ft.Container(expand=True),
            indicador,
            mensaje_estado,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    zona_respuesta = crear_zona_respuesta(
        texto_respuesta,
        ALTURA_MINIMA,
        registrar_interaccion,
    )

    barra_inferior = ft.Row(
        controls=[
            ft.Container(expand=True),
            ft.TextButton(content=texto_copiar, on_click=copiar),
            ft.TextButton(
                content=ft.Text(
                    tr("done"),
                    color=COLOR_TEXTO,
                    weight=ft.FontWeight.BOLD,
                ),
                on_click=boton_cerrar,
            ),
        ],
        spacing=6,
    )

    popup = ft.Container(
        expand=True,
        bgcolor=COLOR_FONDO,
        border=ft.Border.all(1, COLOR_BORDE),
        border_radius=ft.BorderRadius.all(RADIO_BORDES),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        padding=ft.Padding(
            left=24,
            right=24,
            top=12,
            bottom=8,
        ),
        content=ft.Column(
            controls=[encabezado, zona_respuesta, barra_inferior],
            expand=True,
            spacing=7,
        ),
        opacity=0,
        animate_opacity=ft.Animation(
            duration=DURACION_SALIDA_MS,
            curve=ft.AnimationCurve.EASE_OUT,
        ),
    )

    page.add(
        ft.GestureDetector(
            content=popup,
            on_tap_down=registrar_interaccion,
        )
    )
    page.update()

    try:
        await page.window.wait_until_ready_to_show()
    except Exception:
        pass

    await ajustar_geometria(altura_ventana_actual)

    try:
        if MODO == "screen":
            captura = await asyncio.to_thread(
                seleccionar_region_pantalla_jpeg,
                tr("select_screen_region"),
                tr("select_screen_cancel"),
            )
            if captura is None:
                try:
                    await page.window.destroy()
                except Exception:
                    pass
                os._exit(0)
            texto_respuesta.value = tr("detecting_screen")
            mensaje_estado.value = tr("analyzing_screen")
            await mostrar_ventana()
            respuesta = await asyncio.to_thread(
                analizar_captura_pantalla,
                captura,
            )

        else:
            texto_respuesta.value = tr("analyzing_audio").format(
                seconds=AUDIO_DURATION
            )
            mensaje_estado.value = tr("processing_audio")
            await mostrar_ventana()

            if ERROR_AUDIO:
                respuesta = ERROR_AUDIO
            else:
                audio = await asyncio.to_thread(leer_audio_temporal)

                if not audio:
                    respuesta = tr("audio_missing")
                else:
                    respuesta = await asyncio.to_thread(
                        transcribir_y_responder_audio,
                        audio,
                    )

        await actualizar_resultado(respuesta)
        await esperar_inactividad()

    except Exception as error:
        await mostrar_ventana()
        await actualizar_resultado(str(error))
        await esperar_inactividad()


if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.FLET_APP_HIDDEN,
    )
