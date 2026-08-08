from __future__ import annotations

import asyncio
import ctypes
import json
import math
import os
import re
import sys
import time
import webbrowser
from pathlib import Path

import flet as ft

from backend import preguntar_a_novalens
from config_manager import (
    cargar_configuracion,
    color_con_opacidad,
    color_con_transparencia,
)
from localization import tr
from popup_layout import (
    apply_popup_window_geometry,
    calculate_popup_horizontal_geometry,
    popup_viewport_matches,
)
from reporting import build_bug_report_url


if len(sys.argv) < 2:
    raise SystemExit("popup_exe.py requires the control-file path.")

ARCHIVO_CONTROL = Path(sys.argv[1])

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
MODO_VISUALIZACION = APARIENCIA["display_mode"]
MODO_COMPACTO = MODO_VISUALIZACION == "compact"

TIEMPO_VISIBLE = COMPORTAMIENTO["visible_seconds"]
OCULTAR_AL_PERDER_FOCO = COMPORTAMIENTO["click_through_on_blur"]

ALTURA_MINIMA = 165
ALTURA_MAXIMA = 378
ALTURA_CONTROLES_FIJOS = 112
ALTURA_RESPUESTA_MINIMA = 32
DURACION_ENTRADA_MS = 280
DURACION_SALIDA_MS = 220
RETRASO_OCULTAR_POR_BLUR = 0.18
PROTECCION_BLUR_AL_ABRIR = 0.70
DESPLAZAMIENTO_INICIAL = (
    0.18 if POSICION_POPUP == "bottom" else -0.18
)

RESPUESTA_INICIAL = tr("popup_ready")


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def limpiar_markdown_basico(texto: str) -> str:
    texto = re.sub(
        r"```(?:\w+)?\n?(.*?)```",
        r"\1",
        texto,
        flags=re.DOTALL,
    )
    texto = re.sub(r"\*\*(.*?)\*\*", r"\1", texto, flags=re.DOTALL)
    texto = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", texto)
    texto = re.sub(r"`([^`]*)`", r"\1", texto)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^\s*[-*]\s+", "• ", texto, flags=re.MULTILINE)
    return texto.strip()


def obtener_escala_dpi() -> float:
    if os.name != "nt":
        return 1.0

    try:
        dpi = int(ctypes.windll.user32.GetDpiForSystem())
    except Exception:
        dpi = 96

    return max(dpi / 96.0, 1.0)


def obtener_area_trabajo() -> tuple[int, int, int, int]:
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
            escala = obtener_escala_dpi()
            return (
                round(rect.left / escala),
                round(rect.top / escala),
                round((rect.right - rect.left) / escala),
                round((rect.bottom - rect.top) / escala),
            )
    except Exception:
        pass

    escala = obtener_escala_dpi()
    return (
        0,
        0,
        round(ctypes.windll.user32.GetSystemMetrics(0) / escala),
        round(ctypes.windll.user32.GetSystemMetrics(1) / escala),
    )


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
        lineas += max(1, math.ceil(len(parrafo) / caracteres_por_linea))

    return limitar_altura(128 + lineas * (TAMANO_FUENTE + 7))


def calcular_altura_respuesta(altura_popup: int | float) -> int:
    return max(
        ALTURA_RESPUESTA_MINIMA,
        limitar_altura(altura_popup) - ALTURA_CONTROLES_FIJOS,
    )


async def main(page: ft.Page) -> None:
    izquierda_area, _, ancho_area, _ = obtener_area_trabajo()
    _, ancho_popup = calculate_popup_horizontal_geometry(
        izquierda_area,
        ancho_area,
        MARGEN_PANTALLA,
        MODO_VISUALIZACION,
    )

    altura_actual = calcular_altura(RESPUESTA_INICIAL, ancho_popup)
    respuesta_actual = RESPUESTA_INICIAL
    ultimo_error = ""
    historial: list[tuple[str, str]] = []

    popup_visible = False
    procesando = False
    cerrando = False
    ocultando = False
    ventana_enfocada = False
    proteger_blur_hasta = 0.0
    ultimo_comando_id = -1
    numero_transicion = 0

    temporizador: asyncio.Task | None = None
    tarea_ocultar_blur: asyncio.Task | None = None

    campo_pregunta: ft.TextField
    boton_enviar: ft.TextButton
    boton_listo: ft.TextButton
    popup: ft.Container
    zona_respuesta: ft.ListView | None = None

    def aplicar_geometria(altura: int | float) -> tuple[int, int]:
        altura_segura = limitar_altura(altura)
        izquierda, arriba, ancho, alto = obtener_area_trabajo()
        izquierda_segura, ancho_seguro = calculate_popup_horizontal_geometry(
            izquierda,
            ancho,
            MARGEN_PANTALLA,
            MODO_VISUALIZACION,
        )

        if POSICION_POPUP == "bottom":
            arriba_seguro = max(
                arriba + MARGEN_PANTALLA,
                arriba + alto - altura_segura - MARGEN_PANTALLA,
            )
        else:
            arriba_seguro = arriba + MARGEN_PANTALLA

        apply_popup_window_geometry(
            page.window,
            izquierda_segura,
            arriba_seguro,
            ancho_seguro,
            altura_segura,
            ALTURA_MINIMA,
            ALTURA_MAXIMA,
        )

        if zona_respuesta is not None:
            zona_respuesta.height = calcular_altura_respuesta(altura_segura)

        return ancho_seguro, altura_segura

    async def sincronizar_geometria(
        altura: int | float,
        intentos: int = 6,
    ) -> tuple[int, int, bool]:
        """Wait until Flutter has adopted the requested native window bounds."""
        ancho_esperado, altura_esperada = aplicar_geometria(altura)
        page.update()

        for _ in range(max(1, int(intentos))):
            await asyncio.sleep(0.05)
            if popup_viewport_matches(
                page.width,
                page.height,
                ancho_esperado,
                altura_esperada,
            ):
                return ancho_esperado, altura_esperada, True

            ancho_esperado, altura_esperada = aplicar_geometria(altura)
            page.update()

        geometria_valida = popup_viewport_matches(
            page.width,
            page.height,
            ancho_esperado,
            altura_esperada,
        )
        return ancho_esperado, altura_esperada, geometria_valida

    def cancelar_tarea(tarea: asyncio.Task | None) -> None:
        if tarea is None or tarea.done():
            return
        # Auto-hide and blur tasks call hide themselves. Cancelling the current
        # task here aborts the hide halfway through and leaves a ghost window.
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

    async def ocultar_popup() -> None:
        nonlocal popup_visible
        nonlocal ventana_enfocada
        nonlocal ocultando
        nonlocal numero_transicion

        if not popup_visible or procesando or cerrando or ocultando:
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        ocultando = True
        numero_transicion += 1
        transicion_actual = numero_transicion

        popup.opacity = 0
        popup.offset = ft.Offset(0, DESPLAZAMIENTO_INICIAL)
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
        ventana_enfocada = False
        page.window.opacity = 0.0
        page.window.ignore_mouse_events = True
        page.update()

    async def ocultar_inmediatamente() -> None:
        nonlocal popup_visible
        nonlocal ventana_enfocada
        nonlocal ocultando
        nonlocal numero_transicion

        if cerrando:
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()
        numero_transicion += 1
        ocultando = False
        popup_visible = False
        ventana_enfocada = False
        popup.opacity = 0
        popup.offset = ft.Offset(0, DESPLAZAMIENTO_INICIAL)
        page.window.opacity = 0.0
        page.window.ignore_mouse_events = True
        page.update()

    async def cierre_automatico() -> None:
        try:
            await asyncio.sleep(TIEMPO_VISIBLE)
            if popup_visible and not procesando and not ocultando:
                await ocultar_popup()
        except asyncio.CancelledError:
            return

    def reiniciar_temporizador() -> None:
        nonlocal temporizador

        if cerrando or procesando or ocultando or not popup_visible:
            return

        cancelar_temporizador()
        temporizador = asyncio.create_task(cierre_automatico())

    async def activar_popup() -> None:
        nonlocal popup_visible
        nonlocal ventana_enfocada
        nonlocal proteger_blur_hasta
        nonlocal ocultando
        nonlocal numero_transicion

        if cerrando:
            return

        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        numero_transicion += 1
        activacion_actual = numero_transicion
        estaba_oculto = not popup_visible

        ocultando = False
        popup_visible = True
        ventana_enfocada = True
        proteger_blur_hasta = time.monotonic() + PROTECCION_BLUR_AL_ABRIR

        if estaba_oculto:
            popup.opacity = 0
            popup.offset = ft.Offset(0, DESPLAZAMIENTO_INICIAL)
        else:
            popup.opacity = 1
            popup.offset = ft.Offset(0, 0)

        # Keep the native window transparent and non-interactive until Flutter
        # confirms that its viewport matches the requested compact/normal size.
        page.window.ignore_mouse_events = True
        page.update()

        _, _, geometria_valida = await sincronizar_geometria(
            altura_actual,
            intentos=12,
        )

        if activacion_actual != numero_transicion:
            return

        if not geometria_valida:
            popup_visible = False
            ventana_enfocada = False
            page.window.opacity = 0.0
            page.window.ignore_mouse_events = True
            popup.opacity = 0
            page.update()
            return

        page.window.opacity = 1.0
        page.window.ignore_mouse_events = False
        page.window.focused = True
        popup.opacity = 1
        popup.offset = ft.Offset(0, 0)
        page.update()

        try:
            await page.window.to_front()
        except Exception:
            pass

        reiniciar_temporizador()

        try:
            await campo_pregunta.focus()
        except Exception:
            pass

    async def ocultar_despues_de_blur() -> None:
        try:
            await asyncio.sleep(RETRASO_OCULTAR_POR_BLUR)

            if time.monotonic() < proteger_blur_hasta:
                return

            if (
                OCULTAR_AL_PERDER_FOCO
                and popup_visible
                and not ventana_enfocada
                and not procesando
                and not cerrando
                and not ocultando
            ):
                await ocultar_popup()
        except asyncio.CancelledError:
            return

    async def evento_ventana(e: ft.WindowEvent) -> None:
        nonlocal ventana_enfocada
        nonlocal tarea_ocultar_blur

        if e.type == ft.WindowEventType.BLUR:
            ventana_enfocada = False

            if time.monotonic() < proteger_blur_hasta:
                return

            if (
                OCULTAR_AL_PERDER_FOCO
                and popup_visible
                and not procesando
                and not ocultando
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
                await sincronizar_geometria(altura_actual, intentos=2)
                reiniciar_temporizador()
                page.update()

    def registrar_interaccion(e=None) -> None:
        reiniciar_temporizador()

    def construir_pregunta_con_contexto(nueva_pregunta: str) -> str:
        partes = [
            "The user is asking from the Nova Lens popup."
        ]

        for numero, (pregunta, respuesta) in enumerate(historial[-4:], start=1):
            partes.append(f"Previous question {numero}:\n{pregunta}")
            partes.append(f"Previous answer {numero}:\n{respuesta}")

        partes.append(f"New question:\n{nueva_pregunta}")
        partes.append(
            "Answer only the new question. Use previous context only when needed."
        )
        return "\n\n".join(partes)

    async def enviar_pregunta(e=None) -> None:
        nonlocal procesando
        nonlocal respuesta_actual
        nonlocal altura_actual
        nonlocal ultimo_error

        if procesando or cerrando:
            return

        nueva_pregunta = (campo_pregunta.value or "").strip()

        if not nueva_pregunta:
            mensaje_estado.value = tr("write_first")
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
        mensaje_estado.value = tr("analyzing")
        page.update()

        consulta = construir_pregunta_con_contexto(nueva_pregunta)

        try:
            nueva_respuesta = await asyncio.to_thread(
                preguntar_a_novalens,
                consulta,
            )
            nueva_respuesta = (nueva_respuesta or "").strip() or tr("no_text")

            respuesta_actual = nueva_respuesta
            ultimo_error = ""
            historial.append((nueva_pregunta, nueva_respuesta))

            if len(historial) > 8:
                del historial[:-8]

            respuesta_limpia = limpiar_markdown_basico(nueva_respuesta)
            texto_respuesta.value = respuesta_limpia
            campo_pregunta.value = ""
            mensaje_estado.value = tr("response_ready")

            altura_actual = calcular_altura(
                respuesta_limpia,
                int(page.window.width or ancho_popup),
            )
            await sincronizar_geometria(altura_actual)

        except Exception as error:
            # Backend failures are displayed but never stored as conversation
            # history, so auth/debug text cannot contaminate later prompts.
            respuesta_actual = str(error)
            ultimo_error = respuesta_actual
            texto_respuesta.value = limpiar_markdown_basico(respuesta_actual)
            mensaje_estado.value = tr("error_occurred")

        finally:
            procesando = False
            campo_pregunta.disabled = False
            boton_enviar.disabled = False
            boton_listo.disabled = False
            indicador.visible = False

            if popup_visible:
                page.window.opacity = 1.0
                page.window.ignore_mouse_events = False
                popup.opacity = 1
                popup.offset = ft.Offset(0, 0)

            page.update()
            reiniciar_temporizador()

            try:
                await zona_respuesta.scroll_to(offset=0, duration=1)
            except Exception:
                pass

            try:
                await campo_pregunta.focus()
            except Exception:
                pass

    async def copiar_respuesta(e=None) -> None:
        registrar_interaccion()

        try:
            await ft.Clipboard().set(respuesta_actual)
            texto_boton_copiar.value = tr("copied")
            mensaje_estado.value = tr("copy_done")
        except Exception:
            mensaje_estado.value = tr("copy_failed")

        page.update()

    async def informar_error(e=None) -> None:
        registrar_interaccion()
        url = build_bug_report_url("text popup", ultimo_error)
        try:
            abierto = await asyncio.to_thread(webbrowser.open, url, 2)
        except Exception:
            abierto = False
        mensaje_estado.value = (
            tr("report_opened") if abierto else tr("report_open_failed")
        )
        page.update()

    async def boton_ocultar(e=None) -> None:
        if procesando:
            mensaje_estado.value = tr("wait_response")
            page.update()
            return

        await ocultar_popup()

    async def cerrar_totalmente() -> None:
        nonlocal cerrando

        if cerrando:
            return

        cerrando = True
        cancelar_temporizador()
        cancelar_ocultado_por_blur()

        try:
            await page.window.destroy()
        except Exception:
            pass

        os._exit(0)

    async def escuchar_comandos() -> None:
        nonlocal ultimo_comando_id

        while not cerrando:
            try:
                if ARCHIVO_CONTROL.exists():
                    datos = json.loads(
                        ARCHIVO_CONTROL.read_text(encoding="utf-8")
                    )
                    comando_id = int(datos.get("id", 0))
                    comando = str(datos.get("command", "")).lower()

                    if comando_id != ultimo_comando_id:
                        ultimo_comando_id = comando_id

                        if comando == "activate":
                            await activar_popup()
                        elif comando == "hide_now":
                            await ocultar_inmediatamente()
                        elif comando == "quit":
                            await cerrar_totalmente()
                            return

            except (OSError, ValueError, json.JSONDecodeError):
                pass

            await asyncio.sleep(0.10)

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
    page.window.opacity = 0.0
    page.window.ignore_mouse_events = True
    page.window.on_event = evento_ventana

    # Configure the compact viewport before Flet lays out the first frame.
    # Applying it only after page.add() lets Windows briefly keep Flet's
    # default full-screen width and compress the compact popup vertically.
    aplicar_geometria(altura_actual)

    texto_respuesta = ft.Text(
        limpiar_markdown_basico(RESPUESTA_INICIAL),
        color=COLOR_TEXTO,
        size=TAMANO_FUENTE,
        selectable=True,
    )

    texto_boton_copiar = ft.Text(
        tr("copy"),
        color=COLOR_TEXTO,
        weight=ft.FontWeight.W_600,
    )

    mensaje_estado = ft.Text("", size=12, color=COLOR_SECUNDARIO)

    indicador = ft.ProgressRing(
        width=15,
        height=15,
        stroke_width=2,
        color=COLOR_TEXTO,
        visible=False,
    )

    encabezado = ft.Row(
        controls=[
            ft.Text(
                "Nova Lens",
                color=COLOR_TEXTO,
                size=max(18, TAMANO_FUENTE + 2),
                weight=ft.FontWeight.BOLD,
            ),
            ft.Text(
                tr("powered_by"),
                color=COLOR_SECUNDARIO,
                size=12,
                visible=not MODO_COMPACTO,
            ),
            ft.Container(expand=True),
            indicador,
            mensaje_estado,
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # A scrollable control needs an explicit viewport in this frameless window.
    zona_respuesta = ft.ListView(
        controls=[texto_respuesta],
        height=calcular_altura_respuesta(altura_actual),
        build_controls_on_demand=False,
        scroll=ft.ScrollMode.ALWAYS,
        scroll_interval=50,
        on_scroll=registrar_interaccion,
    )

    campo_pregunta = ft.TextField(
        hint_text=tr("popup_hint"),
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
            "Send" if CONFIGURACION["system"].get("language") == "english" else "Enviar",
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
        content=ft.Text(tr("report_error"), color=COLOR_SECUNDARIO),
        on_click=informar_error,
    )

    boton_listo = ft.TextButton(
        content=ft.Text(
            tr("done"),
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
        controls=[encabezado, zona_respuesta, barra_inferior],
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
            left=16 if MODO_COMPACTO else 24,
            right=16 if MODO_COMPACTO else 24,
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
        expand=True,
        content=popup,
        on_tap_down=registrar_interaccion,
    )

    page.add(detector_interacciones)
    aplicar_geometria(altura_actual)
    page.update()

    try:
        await page.window.wait_until_ready_to_show()
    except Exception:
        pass

    # Create the native window invisibly, then let Flutter confirm the real
    # viewport before commands are allowed to expose the popup.
    page.window.visible = True
    page.window.opacity = 0.0
    page.window.ignore_mouse_events = True
    page.update()
    await sincronizar_geometria(altura_actual)

    asyncio.create_task(escuchar_comandos())


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP_HIDDEN)
