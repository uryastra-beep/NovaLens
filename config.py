from __future__ import annotations

import asyncio
from typing import Any

import flet as ft

from config_manager import (
    CONFIGURACION_PREDETERMINADA,
    cargar_api_key,
    cargar_configuracion,
    color_con_opacidad,
    color_con_transparencia,
    configurar_inicio_windows,
    es_color_hex,
    guardar_api_key,
    guardar_configuracion,
    restaurar_configuracion,
)

FONDO = "#17110E"
PANEL = "#241914"
PANEL_SECUNDARIO = "#2E211B"
TEXTO = "#FFF4E8"
TEXTO_SECUNDARIO = "#CDB7A8"
ACENTO = "#A86F4B"
BORDE = "#513A2E"
ERROR = "#FF8A80"
EXITO = "#9BE59B"


def tarjeta(titulo: str, subtitulo: str, contenido: list[ft.Control]) -> ft.Container:
    return ft.Container(
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDE),
        border_radius=18,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text(
                    titulo,
                    size=18,
                    weight=ft.FontWeight.BOLD,
                    color=TEXTO,
                ),
                ft.Text(
                    subtitulo,
                    size=12,
                    color=TEXTO_SECUNDARIO,
                ),
                ft.Divider(color=BORDE, height=18),
                *contenido,
            ],
            spacing=12,
        ),
    )


async def main(page: ft.Page) -> None:
    config = cargar_configuracion()
    api_key_actual = cargar_api_key()

    page.title = "Configuración de NovaLens"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FONDO
    page.padding = 24
    page.spacing = 0

    page.window.width = 860
    page.window.height = 780
    page.window.min_width = 720
    page.window.min_height = 620
    page.window.resizable = True

    apariencia = config["appearance"]
    comportamiento = config["behavior"]
    atajos = config["hotkeys"]
    sistema = config["system"]

    estado = ft.Text(
        "Los cambios se guardan localmente en este dispositivo.",
        size=12,
        color=TEXTO_SECUNDARIO,
    )

    vista_transparencia = ft.Text(
        f'{apariencia["transparency"]} %',
        color=TEXTO,
        weight=ft.FontWeight.BOLD,
    )
    vista_fuente = ft.Text(
        f'{apariencia["font_size"]} px',
        color=TEXTO,
        weight=ft.FontWeight.BOLD,
    )
    vista_radio = ft.Text(
        f'{apariencia["border_radius"]} px',
        color=TEXTO,
        weight=ft.FontWeight.BOLD,
    )
    vista_margen = ft.Text(
        f'{apariencia["margin"]} px',
        color=TEXTO,
        weight=ft.FontWeight.BOLD,
    )
    vista_tiempo = ft.Text(
        f'{comportamiento["visible_seconds"]} s',
        color=TEXTO,
        weight=ft.FontWeight.BOLD,
    )

    color_principal = ft.TextField(
        label="Color principal",
        value=apariencia["primary_color"],
        hint_text="#522E18",
        width=210,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    color_texto = ft.TextField(
        label="Color del texto",
        value=apariencia["text_color"],
        hint_text="#FFF4E8",
        width=210,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    color_secundario = ft.TextField(
        label="Texto secundario",
        value=apariencia["secondary_color"],
        hint_text="#E8C9B2",
        width=210,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    color_borde = ft.TextField(
        label="Color del borde",
        value=apariencia["border_color"],
        hint_text="#8A5738",
        width=210,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )

    transparencia = ft.Slider(
        min=0,
        max=90,
        divisions=18,
        value=apariencia["transparency"],
        active_color=ACENTO,
        expand=True,
    )
    fuente = ft.Slider(
        min=12,
        max=24,
        divisions=12,
        value=apariencia["font_size"],
        active_color=ACENTO,
        expand=True,
    )
    radio = ft.Slider(
        min=0,
        max=36,
        divisions=18,
        value=apariencia["border_radius"],
        active_color=ACENTO,
        expand=True,
    )
    margen = ft.Slider(
        min=0,
        max=32,
        divisions=16,
        value=apariencia["margin"],
        active_color=ACENTO,
        expand=True,
    )
    tiempo = ft.Slider(
        min=3,
        max=60,
        divisions=57,
        value=comportamiento["visible_seconds"],
        active_color=ACENTO,
        expand=True,
    )

    posicion = ft.Dropdown(
        label="Posición del popup",
        value=apariencia["position"],
        width=260,
        filled=True,
        fill_color=PANEL_SECUNDARIO,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
        options=[
            ft.DropdownOption(key="top", text="Arriba"),
            ft.DropdownOption(key="bottom", text="Abajo"),
        ],
    )

    click_through = ft.Switch(
        label="Permitir click-through cuando pierde el foco",
        value=comportamiento["click_through_on_blur"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )

    atajo_abrir = ft.TextField(
        label="Abrir o reactivar",
        value=atajos["open"],
        hint_text="p+enter",
        width=310,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    atajo_config = ft.TextField(
        label="Abrir configuración",
        value=atajos["settings"],
        hint_text="p+shift+enter",
        width=310,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    atajo_cerrar = ft.TextField(
        label="Cerrar NovaLens",
        value=atajos["close"],
        hint_text="p+backspace",
        width=310,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )
    atajo_cerrar_alt = ft.TextField(
        label="Atajo alternativo para cerrar",
        value=atajos["close_alt"],
        hint_text="p+delete",
        width=310,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )

    campo_api_key = ft.TextField(
        label="Google Gemini API Key",
        value=api_key_actual,
        hint_text="Pegá aquí tu propia API key de Gemini",
        password=True,
        can_reveal_password=True,
        expand=True,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
    )

    estado_api_key = ft.Text(
        (
            "API key configurada en este dispositivo."
            if api_key_actual
            else "Todavía no hay una API key configurada."
        ),
        size=12,
        color=EXITO if api_key_actual else TEXTO_SECUNDARIO,
    )

    inicio_windows = ft.Switch(
        label="Iniciar NovaLens automáticamente con Windows",
        value=sistema["start_with_windows"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )

    texto_vista_previa = ft.Text(
        "NovaLens está listo. Esta es una vista previa.",
        color=apariencia["text_color"],
        size=apariencia["font_size"],
    )

    vista_previa = ft.Container(
        height=132,
        bgcolor=color_con_transparencia(
            apariencia["primary_color"],
            apariencia["transparency"],
        ),
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=apariencia["border_radius"],
        padding=18,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "NovaLens",
                            color=apariencia["text_color"],
                            size=max(18, apariencia["font_size"] + 2),
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Powered by Google Gemini",
                            color=apariencia["secondary_color"],
                            size=12,
                        ),
                    ]
                ),
                texto_vista_previa,
            ],
            spacing=10,
        ),
    )

    def actualizar_vista_previa(e: Any = None) -> None:
        vista_transparencia.value = f"{round(transparencia.value or 0)} %"
        vista_fuente.value = f"{round(fuente.value or 16)} px"
        vista_radio.value = f"{round(radio.value or 0)} px"
        vista_margen.value = f"{round(margen.value or 0)} px"
        vista_tiempo.value = f"{round(tiempo.value or 10)} s"

        principal = (
            color_principal.value.strip()
            if es_color_hex(color_principal.value)
            else "#522E18"
        )
        texto = (
            color_texto.value.strip()
            if es_color_hex(color_texto.value)
            else "#FFF4E8"
        )
        secundario = (
            color_secundario.value.strip()
            if es_color_hex(color_secundario.value)
            else "#E8C9B2"
        )
        borde = (
            color_borde.value.strip()
            if es_color_hex(color_borde.value)
            else "#8A5738"
        )

        vista_previa.bgcolor = color_con_transparencia(
            principal,
            transparencia.value or 0,
        )
        vista_previa.border = ft.Border.all(1, borde)
        vista_previa.border_radius = round(radio.value or 0)
        texto_vista_previa.color = texto
        texto_vista_previa.size = round(fuente.value or 16)

        encabezado = vista_previa.content.controls[0]
        encabezado.controls[0].color = texto
        encabezado.controls[0].size = max(18, round(fuente.value or 16) + 2)
        encabezado.controls[1].color = secundario

        page.update()

    for campo in (
        color_principal,
        color_texto,
        color_secundario,
        color_borde,
    ):
        campo.on_change = actualizar_vista_previa

    for control in (
        transparencia,
        fuente,
        radio,
        margen,
        tiempo,
    ):
        control.on_change = actualizar_vista_previa

    def mostrar_estado(mensaje: str, correcto: bool) -> None:
        estado.value = mensaje
        estado.color = EXITO if correcto else ERROR
        page.update()

    def leer_formulario() -> dict[str, Any] | None:
        colores = {
            "Color principal": color_principal.value,
            "Color del texto": color_texto.value,
            "Texto secundario": color_secundario.value,
            "Color del borde": color_borde.value,
        }

        invalidos = [
            nombre
            for nombre, valor in colores.items()
            if not es_color_hex(valor)
        ]

        if invalidos:
            mostrar_estado(
                "Formato inválido en: "
                + ", ".join(invalidos)
                + ". Usá colores como #522E18.",
                False,
            )
            return None

        campos_atajos = {
            "Abrir": atajo_abrir.value,
            "Configuración": atajo_config.value,
            "Cerrar": atajo_cerrar.value,
            "Cerrar alternativo": atajo_cerrar_alt.value,
        }

        vacios = [
            nombre
            for nombre, valor in campos_atajos.items()
            if not (valor or "").strip()
        ]

        if vacios:
            mostrar_estado(
                "No podés dejar atajos vacíos: " + ", ".join(vacios),
                False,
            )
            return None

        return {
            "appearance": {
                "primary_color": color_principal.value.strip(),
                "text_color": color_texto.value.strip(),
                "secondary_color": color_secundario.value.strip(),
                "border_color": color_borde.value.strip(),
                "transparency": round(transparencia.value or 0),
                "font_size": round(fuente.value or 16),
                "border_radius": round(radio.value or 0),
                "margin": round(margen.value or 0),
                "position": posicion.value or "top",
            },
            "behavior": {
                "visible_seconds": round(tiempo.value or 10),
                "click_through_on_blur": bool(click_through.value),
            },
            "hotkeys": {
                "open": atajo_abrir.value.strip(),
                "settings": atajo_config.value.strip(),
                "close": atajo_cerrar.value.strip(),
                "close_alt": atajo_cerrar_alt.value.strip(),
            },
            "system": {
                "start_with_windows": bool(inicio_windows.value),
            },
        }

    def guardar(e: Any = None) -> None:
        nueva_config = leer_formulario()
        if nueva_config is None:
            return

        clave_api = (campo_api_key.value or "").strip()
        if not clave_api:
            mostrar_estado(
                "Pegá tu propia Google Gemini API key antes de guardar.",
                False,
            )
            return

        try:
            guardar_api_key(clave_api)
            guardada = guardar_configuracion(nueva_config)
            configurar_inicio_windows(
                guardada["system"]["start_with_windows"]
            )
        except Exception as error:
            mostrar_estado(f"No pude guardar la configuración: {error}", False)
            return

        estado_api_key.value = "API key guardada localmente en este dispositivo."
        estado_api_key.color = EXITO
        mostrar_estado(
            "Configuración y API key guardadas. NovaLens aplicará los cambios automáticamente.",
            True,
        )

    def cargar_en_formulario(nueva: dict[str, Any]) -> None:
        apariencia_nueva = nueva["appearance"]
        comportamiento_nuevo = nueva["behavior"]
        atajos_nuevos = nueva["hotkeys"]
        sistema_nuevo = nueva["system"]

        color_principal.value = apariencia_nueva["primary_color"]
        color_texto.value = apariencia_nueva["text_color"]
        color_secundario.value = apariencia_nueva["secondary_color"]
        color_borde.value = apariencia_nueva["border_color"]

        transparencia.value = apariencia_nueva["transparency"]
        fuente.value = apariencia_nueva["font_size"]
        radio.value = apariencia_nueva["border_radius"]
        margen.value = apariencia_nueva["margin"]
        posicion.value = apariencia_nueva["position"]

        tiempo.value = comportamiento_nuevo["visible_seconds"]
        click_through.value = comportamiento_nuevo["click_through_on_blur"]

        atajo_abrir.value = atajos_nuevos["open"]
        atajo_config.value = atajos_nuevos["settings"]
        atajo_cerrar.value = atajos_nuevos["close"]
        atajo_cerrar_alt.value = atajos_nuevos["close_alt"]

        inicio_windows.value = sistema_nuevo["start_with_windows"]

        actualizar_vista_previa()

    def restaurar(e: Any = None) -> None:
        try:
            predeterminada = restaurar_configuracion()
            configurar_inicio_windows(False)
            cargar_en_formulario(predeterminada)
        except Exception as error:
            mostrar_estado(f"No pude restaurar la configuración: {error}", False)
            return

        mostrar_estado(
            "Valores predeterminados restaurados. La API key no fue eliminada.",
            True,
        )

    boton_guardar = ft.Button(
        content="Guardar cambios",
        icon=ft.Icons.SAVE,
        bgcolor=ACENTO,
        color=TEXTO,
        on_click=guardar,
    )
    boton_restaurar = ft.OutlinedButton(
        content="Restaurar valores",
        icon=ft.Icons.RESTART_ALT,
        on_click=restaurar,
    )

    contenido = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(
                                "Configuración de NovaLens",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=TEXTO,
                            ),
                            ft.Text(
                                "Personalizá el popup y conectá tu propia cuenta de Gemini.",
                                color=TEXTO_SECUNDARIO,
                            ),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(
                        "1.0.1",
                        color=TEXTO,
                        bgcolor=ACENTO,
                        weight=ft.FontWeight.BOLD,
                    ),
                ]
            ),
            estado,
            tarjeta(
                "Google Gemini",
                "Usá tu propia API key para conectar NovaLens con Gemini.",
                [
                    campo_api_key,
                    estado_api_key,
                    ft.Text(
                        "La clave se guarda solamente en este dispositivo, dentro del archivo local .env. No se almacena en config.json ni se sube a GitHub.",
                        size=12,
                        color=TEXTO_SECUNDARIO,
                    ),
                ],
            ),
            tarjeta(
                "Vista previa",
                "Los cambios visuales se muestran aquí antes de guardarlos.",
                [vista_previa],
            ),
            tarjeta(
                "Apariencia",
                "Colores, transparencia, tamaño y posición del popup.",
                [
                    ft.Row(
                        controls=[
                            color_principal,
                            color_texto,
                            color_secundario,
                        ],
                        wrap=True,
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[color_borde, posicion],
                        wrap=True,
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[
                            ft.Text("Transparencia", color=TEXTO, width=135),
                            transparencia,
                            vista_transparencia,
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.Text("Tamaño de fuente", color=TEXTO, width=135),
                            fuente,
                            vista_fuente,
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.Text("Bordes redondeados", color=TEXTO, width=135),
                            radio,
                            vista_radio,
                        ]
                    ),
                    ft.Row(
                        controls=[
                            ft.Text("Margen de pantalla", color=TEXTO, width=135),
                            margen,
                            vista_margen,
                        ]
                    ),
                ],
            ),
            tarjeta(
                "Comportamiento",
                "Tiempo visible y comportamiento al perder el foco.",
                [
                    ft.Row(
                        controls=[
                            ft.Text("Tiempo visible", color=TEXTO, width=135),
                            tiempo,
                            vista_tiempo,
                        ]
                    ),
                    click_through,
                ],
            ),
            tarjeta(
                "Atajos de teclado",
                "Usá el formato tecla+tecla. Los cambios se aplican al guardar.",
                [
                    ft.Row(
                        controls=[atajo_abrir, atajo_config],
                        wrap=True,
                        spacing=12,
                    ),
                    ft.Row(
                        controls=[atajo_cerrar, atajo_cerrar_alt],
                        wrap=True,
                        spacing=12,
                    ),
                    ft.Text(
                        "Los atajos de pantalla (P + Shift + S) y audio (P + Shift + A) todavía son fijos.",
                        size=12,
                        color=TEXTO_SECUNDARIO,
                    ),
                ],
            ),
            tarjeta(
                "Sistema",
                "Controlá cómo se inicia NovaLens en Windows.",
                [inicio_windows],
            ),
            ft.Row(
                controls=[boton_guardar, boton_restaurar],
                alignment=ft.MainAxisAlignment.END,
            ),
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    page.add(contenido)
    page.update()


if __name__ == "__main__":
    ft.run(main)
