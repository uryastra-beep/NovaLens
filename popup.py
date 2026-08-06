from __future__ import annotations

import asyncio
import ctypes
import json
import math
import os
import re
import sys
from pathlib import Path

import flet as ft

from backend import preguntar_a_novalens
from config_manager import (
    cargar_configuracion,
    color_con_opacidad,
    color_con_transparencia,
)


# ══════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════

CONFIGURACION = cargar_configuracion()
APARIENCIA = CONFIGURACION["appearance"]
COMPORTAMIENTO = CONFIGURACION["behavior"]

COLOR_PRINCIPAL = APARIENCIA["primary_color"]
COLOR_FONDO = color_con_transparencia(
    COLOR_PRINCIPAL,
    APARIENCIA["transparency"],
)
COLOR_CAMPO = color_con_opacidad(COLOR_PRINCIPAL, 55)

COLOR_TEXTO = APARIENCIA["text_color"]
COLOR_SECUNDARIO = APARIENCIA["secondary_color"]
COLOR_BORDE = APARIENCIA["border_color"]

TAMANO_FUENTE = APARIENCIA["font_size"]
RADIO_BORDES = APARIENCIA["border_radius"]
MARGEN_PANTALLA = APARIENCIA["margin"]
POSICION_POPUP = APARIENCIA["position"]

TIEMPO_VISIBLE = COMPORTAMIENTO["visible_seconds"]
OCULTAR_AL_PERDER_FOCO = COMPORTAMIENTO[
    "click_through_on_blur"
]

ALTURA_MINIMA = 145
ALTURA_MAXIMA = 378

DURACION_ENTRADA_MS = 550
DURACION_SALIDA_MS = 650
RETRASO_OCULTAR_POR_BLUR = 0.16

DESPLAZAMIENTO_INICIAL = (
    1.10 if POSICION_POPUP == "bottom" else -1.10
)


# ══════════════════════════════════════════════
# CONTROL FILE
# ══════════════════════════════════════════════

if len(sys.argv) < 2:
    raise SystemExit(
        "popup.py necesita la ruta del archivo de control."
    )

ARCHIVO_CONTROL = Path(sys.argv[1])


# ══════════════════════════════════════════════
# TEXT HELPERS
# ══════════════════════════════════════════════

RESPUESTA_INICIAL = (
    "Nova Lens está listo. "
    "Escribí una pregunta en el campo inferior."
)


def limpiar_markdown_basico(texto: str) -> str:
    texto = re.sub(
        r"```(?:\w+)?\n?(.*?)```",
        r"\1",
        texto,
        flags=re.DOTALL,
    )
    texto = re.sub(
        r"\*\*(.*?)\*\*",
        r"\1",
        texto,
        flags=re.DOTALL,
    )
    texto = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"\1",
        texto,
    )
    texto = re.sub(r"`([^`]*)`", r"\1", texto)
    texto = re.sub(
        r"^#{1,6}\s*",
        "",
        texto,
        flags=re.MULTILINE,
    )
    texto = re.sub(
        r"^\s*[-*]\s+",
        "• ",
        texto,
        flags=re.MULTILINE,
    )
    return texto.strip()


# ══════════════════════════════════════════════
# SCREEN GEOMETRY
# ══════════════════════════════════════════════

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


def limitar_altura(altura: int | float) -> int:
    try:
        valor = int(round(float(altura)))
    except (TypeError, ValueError):
        valor = ALTURA_MINIMA

    return max(ALTURA_MINIMA, min(valor, ALTURA_MAXIMA))


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

    return limitar_altura(
        120 + lineas * (TAMANO_FUENTE + 7)
    )


# ══════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════

async def main(page: ft.Page) -> None:
    _, _, ancho_area, _ = obtener_area_trabajo()
    ancho_popup = max(420, ancho_area - MARGEN_PANTALLA * 2)

    altura_actual = calcular_altura(
        RESPUESTA_INICIAL,
        ancho_popup,
    )
    respuesta_actual = RESPUESTA_INICIAL
    historial: list[tuple[str, str]] = []

    popup_visible = False
    procesando = False
    cerrando = False
    ocultando = False
    ventana_enfocada = False

    ultimo_comando_id = -1
    numero_transicion = 0

    temporizador: asyncio.Task | None = None
    tarea_ocultar_blur: asyncio.Task | None = None

    campo_pregunta: ft.TextField
    boton_enviar: ft.TextButton
    boton_listo: ft.TextButton
    popup: ft.Container

    def aplicar_geometria(altura: int | float) -> int:
        """Restore a complete, valid window rectangle every time."""
        altura_segura = limitar_altura(altura)
        izquierda, arriba, ancho, alto = obtener_area_trabajo()
        ancho_seguro = max(420, ancho - MARGEN_PANTALLA * 2)

        page.window.min_height = ALTURA_MINIMA
        page.window.max_height = ALTURA_MAXIMA
        page.window.width = ancho_seguro
        page.window.height = altura_segura
        page.window.left = izquierda + MARGEN_PANTALLA

        if POSICION_POPUP == "bottom":
            page.window.top = max(
                arriba + MARGEN_PANTALLA,
                arriba + alto - altura_segura - MARGEN_PANTALLA,
            )
        else:
            page.window.top = arriba + MARGEN_PANTALLA

        return altura_segura

    # ══════════════════════════════════════════
    # WINDOW
    # ══════════════════════════════════════════

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
    page.window.visible = False
    page.window.ignore_mouse_events = True

    aplicar_geometria(altura_actual)

    # ══════════════════════════════════════════
    # DYNAMIC CONTROLS
    # ══════════════════════════════════════════

    texto_respuesta = ft.Text(
        limpiar_markdown_basico(RESPUESTA_INICIAL),
        color=COLOR_TEXTO,
        size=TAMANO_FUENTE,
        selectable=True,
    )

    texto_boton_copiar = ft.Text(
        "Copiar",
        color=COLOR_TEXTO,
        weight=ft.FontWeight.W_600,
    )

    mensaje_estado = ft.Text(
        "",
        size=12,
        color=COLOR_SECUNDARIO,
    )

    indicador = ft.ProgressRing(
        width=15,
        height=15,
        stroke_width=2,
        color=COLOR_TEXTO,
        visible=False,
    )

    # ══════════════════════════════════════════
    # TASK MANAGEMENT
    # ══════════════════════════════════════════

    def cancelar_tarea(tarea: asyncio.Task | None) -> None:
        if tarea is None or tarea.done():
            return

        if tarea is asyncio.current_task():
            return

        tarea.cancel()

    def cancelar_temporizador() -> None:
        nonlocal temporizador
        cancelar_tarea(temporizador)
        temporizador = None

    def cancelar_ocultado_por_blur() -> None:
        nonlocal tarea_ocultar_blur
        cancelar_tarea(tarea_ocultar_blur)
        tarea_ocultar_blur = None

    async def ocultar_con_fade() -> None:
        nonlocal popup_visible
        nonlocal ocultando
        nonlocal numero_transicion

        if (
            not popup_visible
            or procesando
            or cerrando
            or ocultando
        ):
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        ocultando = True
        numero_transicion += 1
        transicion_actual = numero_transicion

        popup.opacity = 0
        popup.update()

        try:
            await asyncio.sleep(DURACION_SALIDA_MS / 1000)
        except asyncio.CancelledError:
            ocultando = False
            return

        if transicion_actual != numero_transicion or cerrando:
            ocultando = False
            return

        popup_visible = False
        ocultando = False

        page.window.visible = False
        page.window.ignore_mouse_events = True
        page.update()

        aplicar_geometria(altura_actual)
        page.update()

    async def cierre_automatico() -> None:
        try:
            await asyncio.sleep(TIEMPO_VISIBLE)

            if not procesando:
                await ocultar_con_fade()
        except asyncio.CancelledError:
            return

    def reiniciar_temporizador() -> None:
        nonlocal temporizador

        if (
            cerrando
            or procesando
            or not popup_visible
            or ocultando
        ):
            return

        cancelar_temporizador()
        temporizador = asyncio.create_task(cierre_automatico())

    async def ocultar_despues_de_blur() -> None:
        try:
            await asyncio.sleep(RETRASO_OCULTAR_POR_BLUR)

            if (
                OCULTAR_AL_PERDER_FOCO
                and popup_visible
                and not ventana_enfocada
                and not procesando
                and not cerrando
            ):
                await ocultar_con_fade()
        except asyncio.CancelledError:
            return

    def registrar_interaccion(e=None) -> None:
        reiniciar_temporizador()

    # ══════════════════════════════════════════
    # SHOW / REACTIVATE
    # ══════════════════════════════════════════

    async def activar_popup() -> None:
        nonlocal popup_visible
        nonlocal ocultando
        nonlocal ventana_enfocada
        nonlocal numero_transicion

        if cerrando:
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        numero_transicion += 1
        ocultando = False
        estaba_oculto = not popup_visible
        popup_visible = True
        ventana_enfocada = True

        aplicar_geometria(altura_actual)

        if estaba_oculto:
            popup.opacity = 0
            popup.offset = ft.Offset(0, DESPLAZAMIENTO_INICIAL)
        else:
            popup.opacity = 1
            popup.offset = ft.Offset(0, 0)

        page.window.ignore_mouse_events = False
        page.window.visible = True
        page.update()

        await asyncio.sleep(0.05)
        aplicar_geometria(altura_actual)
        page.window.ignore_mouse_events = False
        page.window.focused = True
        page.update()

        try:
            await page.window.to_front()
        except Exception:
            pass

        if estaba_oculto:
            popup.opacity = 1
            popup.offset = ft.Offset(0, 0)
            popup.update()
            await asyncio.sleep(DURACION_ENTRADA_MS / 1000)
        else:
            popup.update()

        if not procesando:
            reiniciar_temporizador()

            try:
                await campo_pregunta.focus()
            except Exception:
                pass

    # ══════════════════════════════════════════
    # FOCUS EVENTS
    # ══════════════════════════════════════════

    async def evento_ventana(e: ft.WindowEvent) -> None:
        nonlocal ventana_enfocada
        nonlocal tarea_ocultar_blur

        if e.type == ft.WindowEventType.BLUR:
            ventana_enfocada = False

            page.window.ignore_mouse_events = False
            page.update()

            if (
                OCULTAR_AL_PERDER_FOCO
                and popup_visible
                and not procesando
                and not cerrando
            ):
                cancelar_ocultado_por_blur()
                tarea_ocultar_blur = asyncio.create_task(
                    ocultar_despues_de_blur()
                )

        elif e.type == ft.WindowEventType.FOCUS:
            ventana_enfocada = True
            cancelar_ocultado_por_blur()

            if popup_visible:
                page.window.ignore_mouse_events = False
                aplicar_geometria(altura_actual)
                reiniciar_temporizador()
            else:
                page.window.ignore_mouse_events = True

            page.update()

    page.window.on_event = evento_ventana

    # ══════════════════════════════════════════
    # CONVERSATION CONTEXT
    # ══════════════════════════════════════════

    def construir_pregunta_con_contexto(
        nueva_pregunta: str,
    ) -> str:
        partes = [
            "El usuario está haciendo una pregunta desde el popup de Nova Lens."
        ]

        for numero, (pregunta, respuesta) in enumerate(
            historial[-4:],
            start=1,
        ):
            partes.append(
                f"Pregunta anterior {numero}:\n{pregunta}"
            )
            partes.append(
                f"Respuesta anterior {numero}:\n{respuesta}"
            )

        partes.append(f"Nueva pregunta:\n{nueva_pregunta}")
        partes.append(
            "Respondé solamente la nueva pregunta. "
            "Usá el contexto anterior solo si es necesario."
        )
        return "\n\n".join(partes)

    # ══════════════════════════════════════════
    # QUESTIONS
    # ══════════════════════════════════════════

    async def enviar_pregunta(e=None) -> None:
        nonlocal procesando
        nonlocal respuesta_actual
        nonlocal altura_actual

        if procesando or cerrando:
            return

        nueva_pregunta = (campo_pregunta.value or "").strip()

        if not nueva_pregunta:
            mensaje_estado.value = "Escribí una pregunta primero."
            page.update()
            reiniciar_temporizador()
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()
        procesando = True

        campo_pregunta.disabled = True
        boton_enviar.disabled = True
        boton_listo.disabled = True
        indicador.visible = True
        mensaje_estado.value = "Analizando…"
        page.update()

        consulta = construir_pregunta_con_contexto(
            nueva_pregunta
        )

        try:
            nueva_respuesta = await asyncio.to_thread(
                preguntar_a_novalens,
                consulta,
            )
            nueva_respuesta = (nueva_respuesta or "").strip()

            if not nueva_respuesta:
                nueva_respuesta = "Gemini no devolvió ningún texto."

            respuesta_actual = nueva_respuesta
            historial.append((nueva_pregunta, nueva_respuesta))

            if len(historial) > 8:
                del historial[:-8]

            respuesta_limpia = limpiar_markdown_basico(
                nueva_respuesta
            )
            texto_respuesta.value = respuesta_limpia
            campo_pregunta.value = ""
            mensaje_estado.value = "Respuesta lista."

            altura_actual = calcular_altura(
                respuesta_limpia,
                int(page.window.width or ancho_popup),
            )
            aplicar_geometria(altura_actual)

        except Exception as error:
            respuesta_actual = (
                "No pude procesar la pregunta.\n"
                f"Error: {error}"
            )
            texto_respuesta.value = respuesta_actual
            mensaje_estado.value = "Ocurrió un error."

        finally:
            procesando = False
            campo_pregunta.disabled = False
            boton_enviar.disabled = False
            boton_listo.disabled = False
            indicador.visible = False
            page.window.ignore_mouse_events = False
            page.update()
            reiniciar_temporizador()

            try:
                await campo_pregunta.focus()
            except Exception:
                pass

    # ══════════════════════════════════════════
    # BUTTONS
    # ══════════════════════════════════════════

    async def copiar_respuesta(e=None) -> None:
        registrar_interaccion()

        try:
            await ft.Clipboard().set(respuesta_actual)
            texto_boton_copiar.value = "Copiado"
            mensaje_estado.value = "Respuesta copiada."
        except Exception:
            mensaje_estado.value = "No pude copiar la respuesta."

        page.update()

    async def informar_error(e=None) -> None:
        registrar_interaccion()
        mensaje_estado.value = (
            "El sistema para informar errores se agregará después."
        )
        page.update()

    async def boton_ocultar(e=None) -> None:
        if procesando:
            mensaje_estado.value = (
                "Esperá a que termine la respuesta."
            )
            page.update()
            return

        await ocultar_con_fade()

    # ══════════════════════════════════════════
    # CLOSE PROCESS
    # ══════════════════════════════════════════

    async def cerrar_totalmente() -> None:
        nonlocal cerrando

        if cerrando:
            return

        cerrando = True
        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        if popup_visible:
            popup.opacity = 0
            popup.update()
            await asyncio.sleep(DURACION_SALIDA_MS / 1000)

        try:
            await page.window.destroy()
        except Exception:
            pass

        os._exit(0)

    # ══════════════════════════════════════════
    # COMMAND LISTENER
    # ══════════════════════════════════════════

    async def escuchar_comandos() -> None:
        nonlocal ultimo_comando_id

        while not cerrando:
            try:
                if ARCHIVO_CONTROL.exists():
                    datos = json.loads(
                        ARCHIVO_CONTROL.read_text(encoding="utf-8")
                    )
                    comando_id = int(datos.get("id", 0))
                    comando = str(
                        datos.get("command", "")
                    ).lower()

                    if comando_id != ultimo_comando_id:
                        ultimo_comando_id = comando_id

                        if comando == "activate":
                            await activar_popup()
                        elif comando == "quit":
                            await cerrar_totalmente()
                            return

            except (
                OSError,
                ValueError,
                json.JSONDecodeError,
            ):
                pass

            await asyncio.sleep(0.10)

    # ══════════════════════════════════════════
    # LAYOUT
    # ══════════════════════════════════════════

    encabezado = ft.Row(
        controls=[
            ft.Text(
                "Nova Lens",
                color=COLOR_TEXTO,
                size=max(18, TAMANO_FUENTE + 2),
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                "Powered by Google Gemini",
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
        scroll_interval=50,
        on_scroll=registrar_interaccion,
    )

    campo_pregunta = ft.TextField(
        hint_text="Escribí otra pregunta…",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=3,
        shift_enter=True,
        border_radius=max(8, min(18, RADIO_BORDES - 4)),
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_TEXTO,
        bgcolor=COLOR_CAMPO,
        text_style=ft.TextStyle(
            color=COLOR_TEXTO,
            size=max(12, TAMANO_FUENTE - 2),
        ),
        hint_style=ft.TextStyle(
            color=COLOR_SECUNDARIO,
            size=max(12, TAMANO_FUENTE - 2),
        ),
        cursor_color=COLOR_TEXTO,
        content_padding=ft.Padding(
            left=14,
            right=14,
            top=9,
            bottom=9,
        ),
        on_change=registrar_interaccion,
        on_click=registrar_interaccion,
        on_focus=registrar_interaccion,
        on_selection_change=registrar_interaccion,
        on_submit=enviar_pregunta,
        always_call_on_tap=True,
    )

    boton_enviar = ft.TextButton(
        content=ft.Text(
            "Enviar",
            color=COLOR_TEXTO,
            weight=ft.FontWeight.BOLD,
        ),
        on_click=enviar_pregunta,
    )

    boton_copiar = ft.TextButton(
        content=texto_boton_copiar,
        on_click=copiar_respuesta,
    )

    boton_error = ft.TextButton(
        content=ft.Text(
            "Informar error",
            color=COLOR_SECUNDARIO,
        ),
        on_click=informar_error,
    )

    boton_listo = ft.TextButton(
        content=ft.Text(
            "Listo",
            color=COLOR_TEXTO,
            weight=ft.FontWeight.BOLD,
        ),
        on_click=boton_ocultar,
    )

    barra_inferior = ft.Row(
        controls=[
            campo_pregunta,
            boton_enviar,
            boton_copiar,
            boton_error,
            boton_listo,
        ],
        spacing=5,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    contenido = ft.Column(
        controls=[
            encabezado,
            zona_respuesta,
            barra_inferior,
        ],
        expand=True,
        spacing=7,
    )

    popup = ft.Container(
        expand=True,
        bgcolor=COLOR_FONDO,
        border=ft.Border.all(width=1, color=COLOR_BORDE),
        border_radius=ft.BorderRadius.all(RADIO_BORDES),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        padding=ft.Padding(
            left=24,
            right=24,
            top=12,
            bottom=8,
        ),
        content=contenido,
        opacity=0,
        offset=ft.Offset(0, DESPLAZAMIENTO_INICIAL),
        animate_opacity=ft.Animation(
            duration=DURACION_SALIDA_MS,
            curve=ft.AnimationCurve.EASE_OUT,
        ),
        animate_offset=ft.Animation(
            duration=DURACION_ENTRADA_MS,
            curve=ft.AnimationCurve.EASE_OUT_CUBIC,
        ),
    )

    detector_interacciones = ft.GestureDetector(
        content=popup,
        on_tap_down=registrar_interaccion,
    )

    page.add(detector_interacciones)
    page.update()

    asyncio.create_task(escuchar_comandos())


if __name__ == "__main__":
    ft.run(
        main,
        view=ft.AppView.FLET_APP_HIDDEN,
    )
