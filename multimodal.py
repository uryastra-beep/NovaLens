from __future__ import annotations

import asyncio
import ctypes
import io
import math
import os
import re
import sys
from pathlib import Path

import flet as ft
from PIL import ImageGrab

from backend import analizar_captura_pantalla, transcribir_y_responder_audio
from config_manager import (
    cargar_configuracion,
    color_con_transparencia,
)


if len(sys.argv) < 2 or sys.argv[1].lower() not in {"screen", "audio"}:
    raise SystemExit("Usage: multimodal.py screen|audio [audio-file]")

MODO = sys.argv[1].lower()
ARCHIVO_AUDIO: Path | None = None
ERROR_AUDIO = ""

if MODO == "audio":
    if len(sys.argv) >= 4 and sys.argv[2] == "--error":
        ERROR_AUDIO = sys.argv[3]
    elif len(sys.argv) >= 3:
        ARCHIVO_AUDIO = Path(sys.argv[2])

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
DURACION_ENTRADA_MS = 420
DURACION_SALIDA_MS = 520


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def preparar_dpi() -> None:
    if os.name != "nt":
        return

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def obtener_area_trabajo() -> tuple[int, int, int, int]:
    preparar_dpi()

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


def capturar_pantalla_jpeg() -> bytes:
    imagen = ImageGrab.grab(all_screens=True)

    if imagen.mode != "RGB":
        imagen = imagen.convert("RGB")

    with io.BytesIO() as buffer:
        imagen.save(
            buffer,
            format="JPEG",
            quality=82,
            optimize=True,
        )
        return buffer.getvalue()


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

    page.title = "Nova Lens"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = ft.Colors.TRANSPARENT

    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.frameless = True
    page.window.always_on_top = True
    page.window.skip_task_bar = True
    page.window.resizable = False
    page.window.shadow = False
    page.window.width = ancho_popup
    page.window.height = ALTURA_MINIMA
    page.window.min_height = ALTURA_MINIMA
    page.window.max_height = ALTURA_MAXIMA
    page.window.left = izquierda + MARGEN_PANTALLA
    page.window.visible = False

    if POSICION_POPUP == "bottom":
        page.window.top = (
            arriba + alto_area - ALTURA_MINIMA - MARGEN_PANTALLA
        )
    else:
        page.window.top = arriba + MARGEN_PANTALLA

    respuesta_actual = ""
    cerrando = False

    texto_respuesta = ft.Text(
        "Preparing…",
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
        "Copy",
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
        try:
            await ft.Clipboard().set(respuesta_actual)
            texto_copiar.value = "Copied"
            mensaje_estado.value = "Response copied."
        except Exception:
            mensaje_estado.value = "I could not copy the response."

        page.update()

    async def boton_cerrar(e=None) -> None:
        await cerrar()

    async def mostrar_ventana() -> None:
        page.window.visible = True
        page.window.focused = True
        page.update()

        try:
            await page.window.to_front()
        except Exception:
            pass

        popup.opacity = 0
        popup.offset = ft.Offset(
            0,
            -0.75 if POSICION_POPUP == "top" else 0.75,
        )
        popup.update()
        await asyncio.sleep(0.04)
        popup.opacity = 1
        popup.offset = ft.Offset(0, 0)
        popup.update()

    async def actualizar_resultado(texto: str) -> None:
        nonlocal respuesta_actual

        respuesta_actual = (
            (texto or "").strip()
            or "Gemini did not return any text."
        )
        limpio = limpiar_markdown_basico(respuesta_actual)
        texto_respuesta.value = limpio
        indicador.visible = False
        mensaje_estado.value = "Response ready."

        nueva_altura = calcular_altura(limpio, ancho_popup)
        page.window.height = nueva_altura

        if POSICION_POPUP == "bottom":
            page.window.top = (
                arriba + alto_area - nueva_altura - MARGEN_PANTALLA
            )

        page.update()

    encabezado = ft.Row(
        controls=[
            ft.Text(
                "Nova Lens",
                color=COLOR_TEXTO,
                size=max(18, TAMANO_FUENTE + 2),
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Screen & Audio",
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

    zona_respuesta = ft.Column(
        controls=[texto_respuesta],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    barra_inferior = ft.Row(
        controls=[
            ft.Container(expand=True),
            ft.TextButton(content=texto_copiar, on_click=copiar),
            ft.TextButton(
                content=ft.Text(
                    "Done",
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
        offset=ft.Offset(
            0,
            -0.75 if POSICION_POPUP == "top" else 0.75,
        ),
        animate_opacity=ft.Animation(
            duration=DURACION_SALIDA_MS,
            curve=ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            duration=DURACION_ENTRADA_MS,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        ),
    )

    page.add(popup)
    page.update()

    try:
        if MODO == "screen":
            # Capture before showing the popup so Nova Lens is not included.
            captura = await asyncio.to_thread(capturar_pantalla_jpeg)
            texto_respuesta.value = (
                "Detecting the question visible on the screen…"
            )
            mensaje_estado.value = "Analyzing screen…"
            await mostrar_ventana()
            respuesta = await asyncio.to_thread(
                analizar_captura_pantalla,
                captura,
            )

        else:
            texto_respuesta.value = (
                "Analyzing the previous 10 seconds of microphone audio…"
            )
            mensaje_estado.value = "Processing recent audio…"
            await mostrar_ventana()

            if ERROR_AUDIO:
                respuesta = ERROR_AUDIO
            else:
                audio = await asyncio.to_thread(leer_audio_temporal)

                if not audio:
                    respuesta = (
                        "I could not find recent microphone audio to analyze."
                    )
                else:
                    respuesta = await asyncio.to_thread(
                        transcribir_y_responder_audio,
                        audio,
                    )

        await actualizar_resultado(respuesta)
        await asyncio.sleep(TIEMPO_VISIBLE)
        await cerrar()

    except Exception as error:
        await mostrar_ventana()
        await actualizar_resultado(
            "I could not complete the request.\n\n"
            f"Error type: {type(error).__name__}\n"
            f"Details: {error}"
        )


if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.FLET_APP_HIDDEN,
    )
