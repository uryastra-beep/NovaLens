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


# ══════════════════════════════════════════════
# APARIENCIA
# ══════════════════════════════════════════════

COLOR_PRINCIPAL = "#522E18"

# 40 % de opacidad = 60 % de transparencia.
COLOR_FONDO = "#66522E18"

COLOR_CAMPO = "#88402012"

COLOR_TEXTO = "#FFF4E8"
COLOR_SECUNDARIO = "#E8C9B2"
COLOR_BORDE = "#8A5738"

TAMANO_FUENTE = 16
RADIO_BORDES = 20

MARGEN_PANTALLA = 8

ALTURA_MINIMA = 145

# Aproximadamente 10 cm a 96 DPI.
ALTURA_MAXIMA = 378


# ══════════════════════════════════════════════
# TIEMPOS Y ANIMACIONES
# ══════════════════════════════════════════════

TIEMPO_VISIBLE = 10

DURACION_ENTRADA_MS = 550
DURACION_SALIDA_MS = 650

DESPLAZAMIENTO_INICIAL = -1.10


# ══════════════════════════════════════════════
# ARCHIVO DE CONTROL
# ══════════════════════════════════════════════

if len(sys.argv) < 2:
    raise SystemExit(
        "popup.py necesita la ruta del archivo de control."
    )

ARCHIVO_CONTROL = Path(sys.argv[1])


# ══════════════════════════════════════════════
# TEXTO
# ══════════════════════════════════════════════

RESPUESTA_INICIAL = (
    "NovaLens está listo. "
    "Escribí una pregunta en el campo inferior."
)


def limpiar_markdown_basico(texto: str) -> str:
    """
    Quita Markdown básico del texto generado.
    """

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

    texto = re.sub(
        r"`([^`]*)`",
        r"\1",
        texto,
    )

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
# PANTALLA
# ══════════════════════════════════════════════

def preparar_dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def obtener_ancho_pantalla() -> int:
    preparar_dpi()

    return int(
        ctypes.windll.user32.GetSystemMetrics(0)
    )


def calcular_altura(
    texto: str,
    ancho: int,
) -> int:
    """
    Hace crecer el popup hasta un máximo de 10 cm.
    """

    espacio_texto = max(
        ancho - 120,
        300,
    )

    caracteres_por_linea = max(
        30,
        int(
            espacio_texto
            / (TAMANO_FUENTE * 0.55)
        ),
    )

    lineas = 0

    for parrafo in texto.splitlines() or [""]:
        lineas += max(
            1,
            math.ceil(
                len(parrafo)
                / caracteres_por_linea
            ),
        )

    altura = (
        120
        + lineas
        * (TAMANO_FUENTE + 7)
    )

    return max(
        ALTURA_MINIMA,
        min(
            altura,
            ALTURA_MAXIMA,
        ),
    )


# ══════════════════════════════════════════════
# INTERFAZ
# ══════════════════════════════════════════════

async def main(page: ft.Page) -> None:
    ancho_pantalla = obtener_ancho_pantalla()

    ancho_popup = (
        ancho_pantalla
        - MARGEN_PANTALLA * 2
    )

    respuesta_actual = RESPUESTA_INICIAL
    historial: list[tuple[str, str]] = []

    popup_visible = False
    procesando = False
    cerrando = False

    ultimo_comando_id = -1
    numero_transicion = 0

    temporizador: asyncio.Task | None = None
    tarea_control: asyncio.Task | None = None

    # ══════════════════════════════════════════
    # VENTANA
    # ══════════════════════════════════════════

    page.title = "NovaLens"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = ft.Colors.TRANSPARENT

    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.window.frameless = True
    page.window.always_on_top = True
    page.window.skip_task_bar = True
    page.window.resizable = False
    page.window.shadow = False

    page.window.left = MARGEN_PANTALLA
    page.window.top = MARGEN_PANTALLA
    page.window.width = ancho_popup
    page.window.height = calcular_altura(
        RESPUESTA_INICIAL,
        ancho_popup,
    )

    page.window.min_height = ALTURA_MINIMA
    page.window.max_height = ALTURA_MAXIMA

    # Inicia oculto y con click-through.
    page.window.visible = False
    page.window.ignore_mouse_events = True

    # ══════════════════════════════════════════
    # CONTROLES DINÁMICOS
    # ══════════════════════════════════════════

    texto_respuesta = ft.Text(
        limpiar_markdown_basico(
            RESPUESTA_INICIAL
        ),
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

    campo_pregunta: ft.TextField
    boton_enviar: ft.TextButton
    boton_listo: ft.TextButton
    popup: ft.Container

    # ══════════════════════════════════════════
    # TEMPORIZADOR
    # ══════════════════════════════════════════

    def cancelar_temporizador() -> None:
        nonlocal temporizador

        if (
            temporizador is not None
            and not temporizador.done()
        ):
            temporizador.cancel()

        temporizador = None

    async def ocultar_con_fade() -> None:
        """
        Oculta el popup, pero deja popup.py vivo.
        """

        nonlocal popup_visible
        nonlocal numero_transicion

        if (
            not popup_visible
            or procesando
            or cerrando
        ):
            return

        cancelar_temporizador()

        numero_transicion += 1
        transicion_actual = numero_transicion

        popup.opacity = 0
        popup.update()

        await asyncio.sleep(
            DURACION_SALIDA_MS / 1000
        )

        # Si P + Enter se presionó durante el fade,
        # no ocultamos la ventana.
        if transicion_actual != numero_transicion:
            return

        page.window.ignore_mouse_events = True
        page.window.visible = False
        page.update()

        popup_visible = False

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
        ):
            return

        cancelar_temporizador()

        temporizador = asyncio.create_task(
            cierre_automatico()
        )

    def registrar_interaccion(e=None) -> None:
        reiniciar_temporizador()

    # ══════════════════════════════════════════
    # MOSTRAR Y REACTIVAR
    # ══════════════════════════════════════════

    async def activar_popup() -> None:
        """
        Desactiva click-through y devuelve el popup al frente.
        """

        nonlocal popup_visible
        nonlocal numero_transicion

        if cerrando:
            return

        cancelar_temporizador()

        numero_transicion += 1

        estaba_oculto = not popup_visible

        page.window.visible = True
        page.window.ignore_mouse_events = False
        page.window.focused = True

        page.update()

        try:
            await page.window.to_front()
        except Exception:
            pass

        if estaba_oculto:
            popup_visible = True

            popup.offset = ft.Offset(
                0,
                DESPLAZAMIENTO_INICIAL,
            )

            popup.opacity = 0
            popup.update()

            await asyncio.sleep(0.06)

            popup.offset = ft.Offset(0, 0)
            popup.opacity = 1
            popup.update()

            await asyncio.sleep(
                DURACION_ENTRADA_MS / 1000
            )

        else:
            popup.offset = ft.Offset(0, 0)
            popup.opacity = 1
            popup.update()

        if not procesando:
            reiniciar_temporizador()

            try:
                await campo_pregunta.focus()
            except Exception:
                pass

    # ══════════════════════════════════════════
    # CLICK-THROUGH AL PERDER FOCO
    # ══════════════════════════════════════════

    async def evento_ventana(
        e: ft.WindowEvent,
    ) -> None:
        if e.type == ft.WindowEventType.BLUR:
            # El popup sigue visible, pero los clics
            # atraviesan hacia VS Code, Zoom, etc.
            page.window.ignore_mouse_events = True
            page.update()

        elif e.type == ft.WindowEventType.FOCUS:
            page.window.ignore_mouse_events = False
            page.update()

            reiniciar_temporizador()

    page.window.on_event = evento_ventana

    # ══════════════════════════════════════════
    # CONTEXTO PARA SEGUIMIENTOS
    # ══════════════════════════════════════════

    def construir_pregunta_con_contexto(
        nueva_pregunta: str,
    ) -> str:
        partes = [
            (
                "El usuario está haciendo una pregunta "
                "desde el popup de NovaLens."
            )
        ]

        for numero, (
            pregunta,
            respuesta,
        ) in enumerate(
            historial[-4:],
            start=1,
        ):
            partes.append(
                f"Pregunta anterior {numero}:\n"
                f"{pregunta}"
            )

            partes.append(
                f"Respuesta anterior {numero}:\n"
                f"{respuesta}"
            )

        partes.append(
            "Nueva pregunta:\n"
            f"{nueva_pregunta}"
        )

        partes.append(
            "Respondé solamente la nueva pregunta. "
            "Usá el contexto anterior solo si es necesario."
        )

        return "\n\n".join(partes)

    # ══════════════════════════════════════════
    # PREGUNTAS
    # ══════════════════════════════════════════

    async def enviar_pregunta(e=None) -> None:
        nonlocal procesando
        nonlocal respuesta_actual

        if procesando or cerrando:
            return

        nueva_pregunta = (
            campo_pregunta.value or ""
        ).strip()

        if not nueva_pregunta:
            mensaje_estado.value = (
                "Escribí una pregunta primero."
            )

            page.update()
            reiniciar_temporizador()
            return

        cancelar_temporizador()

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

            nueva_respuesta = (
                nueva_respuesta or ""
            ).strip()

            if not nueva_respuesta:
                nueva_respuesta = (
                    "Gemini no devolvió ningún texto."
                )

            respuesta_actual = nueva_respuesta

            historial.append(
                (
                    nueva_pregunta,
                    nueva_respuesta,
                )
            )

            if len(historial) > 8:
                del historial[:-8]

            respuesta_limpia = limpiar_markdown_basico(
                nueva_respuesta
            )

            texto_respuesta.value = respuesta_limpia
            campo_pregunta.value = ""

            mensaje_estado.value = "Respuesta lista."

            page.window.height = calcular_altura(
                respuesta_limpia,
                ancho_popup,
            )

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

            page.update()

            # Comienza a contar únicamente después
            # de que Gemini terminó de responder.
            reiniciar_temporizador()

            try:
                await campo_pregunta.focus()
            except Exception:
                pass

    # ══════════════════════════════════════════
    # BOTONES
    # ══════════════════════════════════════════

    async def copiar_respuesta(e) -> None:
        registrar_interaccion()

        try:
            await ft.Clipboard().set(
                respuesta_actual
            )

            texto_boton_copiar.value = "Copiado"
            mensaje_estado.value = "Respuesta copiada."

        except Exception:
            mensaje_estado.value = (
                "No pude copiar la respuesta."
            )

        page.update()

    async def informar_error(e) -> None:
        registrar_interaccion()

        mensaje_estado.value = (
            "El sistema para informar errores "
            "se agregará después."
        )

        page.update()

    async def boton_ocultar(e) -> None:
        if procesando:
            mensaje_estado.value = (
                "Esperá a que termine la respuesta."
            )
            page.update()
            return

        await ocultar_con_fade()

    # ══════════════════════════════════════════
    # CERRAR PROCESO DEL POPUP
    # ══════════════════════════════════════════

    async def cerrar_totalmente() -> None:
        nonlocal cerrando

        if cerrando:
            return

        cerrando = True
        cancelar_temporizador()

        if popup_visible:
            popup.opacity = 0
            popup.update()

            await asyncio.sleep(
                DURACION_SALIDA_MS / 1000
            )

        try:
            await page.window.destroy()
        except Exception:
            pass

        os._exit(0)

    # ══════════════════════════════════════════
    # ESCUCHAR ÓRDENES DE main.py
    # ══════════════════════════════════════════

    async def escuchar_comandos() -> None:
        nonlocal ultimo_comando_id

        while not cerrando:
            try:
                if ARCHIVO_CONTROL.exists():
                    datos = json.loads(
                        ARCHIVO_CONTROL.read_text(
                            encoding="utf-8"
                        )
                    )

                    comando_id = int(
                        datos.get("id", 0)
                    )

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
    # DISEÑO
    # ══════════════════════════════════════════

    encabezado = ft.Row(
        controls=[
            ft.Text(
                "NovaLens",
                color=COLOR_TEXTO,
                size=18,
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
        controls=[
            texto_respuesta,
        ],
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

        # Enter envía; Shift + Enter crea otra línea.
        shift_enter=True,

        border_radius=14,
        border_color=COLOR_BORDE,
        focused_border_color=COLOR_TEXTO,
        bgcolor=COLOR_CAMPO,

        text_style=ft.TextStyle(
            color=COLOR_TEXTO,
            size=14,
        ),

        hint_style=ft.TextStyle(
            color=COLOR_SECUNDARIO,
            size=14,
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

        border=ft.Border.all(
            width=1,
            color=COLOR_BORDE,
        ),

        border_radius=ft.BorderRadius.all(
            RADIO_BORDES
        ),

        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,

        padding=ft.Padding(
            left=24,
            right=24,
            top=12,
            bottom=8,
        ),

        content=contenido,

        opacity=0,

        offset=ft.Offset(
            0,
            DESPLAZAMIENTO_INICIAL,
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

    detector_interacciones = ft.GestureDetector(
        content=popup,
        on_tap_down=registrar_interaccion,
    )

    page.add(detector_interacciones)
    page.update()

    # Escucha permanentemente las órdenes de main.py.
    tarea_control = asyncio.create_task(
        escuchar_comandos()
    )


if __name__ == "__main__":
    # Inicia sin enseñar una ventana vacía.
    ft.run(
        main,
        view=ft.AppView.FLET_APP_HIDDEN,
    )