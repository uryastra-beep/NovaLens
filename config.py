from __future__ import annotations

from typing import Any

import flet as ft

from config_manager import (
    cargar_api_key,
    cargar_configuracion,
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

TRADUCCIONES = {
    "english": {
        "window_title": "Nova Lens Settings",
        "title": "Nova Lens Settings",
        "subtitle": "Customize the popup and connect your own Gemini account.",
        "local": "Changes are stored locally on this device.",
        "language": "Language",
        "english": "English",
        "spanish": "Spanish",
        "language_note": "The selected language is applied after saving and reopening Nova Lens.",
        "gemini": "Google Gemini",
        "gemini_sub": "Use your own API key to connect Nova Lens to Gemini.",
        "api_hint": "Paste your own Gemini API key here",
        "api_ready": "An API key is configured on this device.",
        "api_missing": "No API key is configured yet.",
        "api_privacy": "The key is stored only on this device in the local .env file. It is not stored in config.json or uploaded to GitHub.",
        "preview": "Preview",
        "preview_sub": "Visual changes are shown here before saving.",
        "preview_text": "Nova Lens is ready. This is a preview.",
        "appearance": "Appearance",
        "appearance_sub": "Popup colors, transparency, size, and position.",
        "primary": "Primary color",
        "text_color": "Text color",
        "secondary": "Secondary text",
        "border": "Border color",
        "position": "Popup position",
        "top": "Top",
        "bottom": "Bottom",
        "transparency": "Transparency",
        "font_size": "Font size",
        "radius": "Rounded corners",
        "margin": "Screen margin",
        "behavior": "Behavior",
        "behavior_sub": "Visible time and behavior when focus is lost.",
        "visible_time": "Visible time",
        "click_through": "Allow click-through when focus is lost",
        "hotkeys": "Keyboard shortcuts",
        "hotkeys_sub": "Use key+key format. Changes apply after saving.",
        "open": "Open or reactivate",
        "settings": "Open Settings",
        "close": "Close Nova Lens",
        "close_alt": "Alternative close shortcut",
        "fixed_hotkeys": "Screenshot (P + Shift + S) and audio (P + Shift + A) shortcuts are currently fixed.",
        "system": "System",
        "system_sub": "Control how Nova Lens starts in Windows.",
        "startup": "Start Nova Lens automatically with Windows",
        "save": "Save changes",
        "restore": "Restore defaults",
        "saved": "Settings and API key saved. Restart Nova Lens to apply the language everywhere.",
        "restored": "Default settings restored. The API key was not deleted.",
        "need_key": "Paste your Google Gemini API key before saving.",
        "invalid_color": "Invalid color format in: {fields}. Use values such as #522E18.",
        "empty_hotkey": "Shortcuts cannot be empty: {fields}",
        "save_error": "Could not save settings: {error}",
        "restore_error": "Could not restore settings: {error}",
    },
    "spanish": {
        "window_title": "Configuración de Nova Lens",
        "title": "Configuración de Nova Lens",
        "subtitle": "Personalizá el popup y conectá tu propia cuenta de Gemini.",
        "local": "Los cambios se guardan localmente en este dispositivo.",
        "language": "Idioma",
        "english": "Inglés",
        "spanish": "Español",
        "language_note": "El idioma seleccionado se aplica después de guardar y volver a abrir Nova Lens.",
        "gemini": "Google Gemini",
        "gemini_sub": "Usá tu propia API key para conectar Nova Lens con Gemini.",
        "api_hint": "Pegá aquí tu propia API key de Gemini",
        "api_ready": "Hay una API key configurada en este dispositivo.",
        "api_missing": "Todavía no hay una API key configurada.",
        "api_privacy": "La clave se guarda solo en este dispositivo, dentro del archivo local .env. No se almacena en config.json ni se sube a GitHub.",
        "preview": "Vista previa",
        "preview_sub": "Los cambios visuales se muestran aquí antes de guardarlos.",
        "preview_text": "Nova Lens está listo. Esta es una vista previa.",
        "appearance": "Apariencia",
        "appearance_sub": "Colores, transparencia, tamaño y posición del popup.",
        "primary": "Color principal",
        "text_color": "Color del texto",
        "secondary": "Texto secundario",
        "border": "Color del borde",
        "position": "Posición del popup",
        "top": "Arriba",
        "bottom": "Abajo",
        "transparency": "Transparencia",
        "font_size": "Tamaño de fuente",
        "radius": "Bordes redondeados",
        "margin": "Margen de pantalla",
        "behavior": "Comportamiento",
        "behavior_sub": "Tiempo visible y comportamiento al perder el foco.",
        "visible_time": "Tiempo visible",
        "click_through": "Permitir click-through cuando pierde el foco",
        "hotkeys": "Atajos de teclado",
        "hotkeys_sub": "Usá el formato tecla+tecla. Los cambios se aplican al guardar.",
        "open": "Abrir o reactivar",
        "settings": "Abrir configuración",
        "close": "Cerrar Nova Lens",
        "close_alt": "Atajo alternativo para cerrar",
        "fixed_hotkeys": "Los atajos de pantalla (P + Shift + S) y audio (P + Shift + A) todavía son fijos.",
        "system": "Sistema",
        "system_sub": "Controlá cómo se inicia Nova Lens en Windows.",
        "startup": "Iniciar Nova Lens automáticamente con Windows",
        "save": "Guardar cambios",
        "restore": "Restaurar valores",
        "saved": "Configuración y API key guardadas. Reiniciá Nova Lens para aplicar el idioma en toda la app.",
        "restored": "Valores predeterminados restaurados. La API key no fue eliminada.",
        "need_key": "Pegá tu Google Gemini API key antes de guardar.",
        "invalid_color": "Formato inválido en: {fields}. Usá valores como #522E18.",
        "empty_hotkey": "No podés dejar atajos vacíos: {fields}",
        "save_error": "No pude guardar la configuración: {error}",
        "restore_error": "No pude restaurar la configuración: {error}",
    },
}


def tarjeta(titulo: str, subtitulo: str, controles: list[ft.Control]) -> ft.Container:
    return ft.Container(
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDE),
        border_radius=18,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
                ft.Text(subtitulo, size=12, color=TEXTO_SECUNDARIO),
                ft.Divider(color=BORDE, height=18),
                *controles,
            ],
            spacing=12,
        ),
    )


async def main(page: ft.Page) -> None:
    config = cargar_configuracion()
    api_key_actual = cargar_api_key()
    idioma_actual = config["system"].get("language", "english")
    t = TRADUCCIONES.get(idioma_actual, TRADUCCIONES["english"])

    page.title = t["window_title"]
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FONDO
    page.padding = 24
    page.window.width = 860
    page.window.height = 800
    page.window.min_width = 720
    page.window.min_height = 620
    page.window.resizable = True

    apariencia = config["appearance"]
    comportamiento = config["behavior"]
    atajos = config["hotkeys"]
    sistema = config["system"]

    estado = ft.Text(t["local"], size=12, color=TEXTO_SECUNDARIO)

    def campo(label: str, value: str, hint: str, width: int = 210, password: bool = False) -> ft.TextField:
        return ft.TextField(
            label=label,
            value=value,
            hint_text=hint,
            width=width,
            password=password,
            can_reveal_password=password,
            border_color=BORDE,
            focused_border_color=ACENTO,
            color=TEXTO,
        )

    idioma = ft.Dropdown(
        label=t["language"],
        value=idioma_actual,
        width=260,
        filled=True,
        fill_color=PANEL_SECUNDARIO,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
        options=[
            ft.DropdownOption(key="english", text=t["english"]),
            ft.DropdownOption(key="spanish", text=t["spanish"]),
        ],
    )

    campo_api_key = campo("Google Gemini API Key", api_key_actual, t["api_hint"], 700, True)
    color_principal = campo(t["primary"], apariencia["primary_color"], "#522E18")
    color_texto = campo(t["text_color"], apariencia["text_color"], "#FFF4E8")
    color_secundario = campo(t["secondary"], apariencia["secondary_color"], "#E8C9B2")
    color_borde = campo(t["border"], apariencia["border_color"], "#8A5738")

    transparencia = ft.Slider(min=0, max=90, divisions=18, value=apariencia["transparency"], active_color=ACENTO, expand=True)
    fuente = ft.Slider(min=12, max=24, divisions=12, value=apariencia["font_size"], active_color=ACENTO, expand=True)
    radio = ft.Slider(min=0, max=36, divisions=18, value=apariencia["border_radius"], active_color=ACENTO, expand=True)
    margen = ft.Slider(min=0, max=32, divisions=16, value=apariencia["margin"], active_color=ACENTO, expand=True)
    tiempo = ft.Slider(min=3, max=60, divisions=57, value=comportamiento["visible_seconds"], active_color=ACENTO, expand=True)

    posicion = ft.Dropdown(
        label=t["position"],
        value=apariencia["position"],
        width=260,
        filled=True,
        fill_color=PANEL_SECUNDARIO,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
        options=[
            ft.DropdownOption(key="top", text=t["top"]),
            ft.DropdownOption(key="bottom", text=t["bottom"]),
        ],
    )

    click_through = ft.Switch(
        label=t["click_through"],
        value=comportamiento["click_through_on_blur"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    inicio_windows = ft.Switch(
        label=t["startup"],
        value=sistema["start_with_windows"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )

    atajo_abrir = campo(t["open"], atajos["open"], "p+enter", 310)
    atajo_config = campo(t["settings"], atajos["settings"], "p+shift+enter", 310)
    atajo_cerrar = campo(t["close"], atajos["close"], "p+backspace", 310)
    atajo_cerrar_alt = campo(t["close_alt"], atajos["close_alt"], "p+delete", 310)

    vista_previa = ft.Container(
        height=132,
        bgcolor=color_con_transparencia(apariencia["primary_color"], apariencia["transparency"]),
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=apariencia["border_radius"],
        padding=18,
        content=ft.Column(
            controls=[
                ft.Text("Nova Lens", color=apariencia["text_color"], size=20, weight=ft.FontWeight.BOLD),
                ft.Text(t["preview_text"], color=apariencia["text_color"], size=apariencia["font_size"]),
            ]
        ),
    )

    def mostrar_estado(mensaje: str, correcto: bool) -> None:
        estado.value = mensaje
        estado.color = EXITO if correcto else ERROR
        page.update()

    def leer_formulario() -> dict[str, Any] | None:
        colores = {
            t["primary"]: color_principal.value,
            t["text_color"]: color_texto.value,
            t["secondary"]: color_secundario.value,
            t["border"]: color_borde.value,
        }
        invalidos = [nombre for nombre, valor in colores.items() if not es_color_hex(valor)]
        if invalidos:
            mostrar_estado(t["invalid_color"].format(fields=", ".join(invalidos)), False)
            return None

        campos_atajos = {
            t["open"]: atajo_abrir.value,
            t["settings"]: atajo_config.value,
            t["close"]: atajo_cerrar.value,
            t["close_alt"]: atajo_cerrar_alt.value,
        }
        vacios = [nombre for nombre, valor in campos_atajos.items() if not (valor or "").strip()]
        if vacios:
            mostrar_estado(t["empty_hotkey"].format(fields=", ".join(vacios)), False)
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
                "language": idioma.value or "english",
            },
        }

    def guardar(e: Any = None) -> None:
        nueva = leer_formulario()
        if nueva is None:
            return
        clave = (campo_api_key.value or "").strip()
        if not clave:
            mostrar_estado(t["need_key"], False)
            return
        try:
            guardar_api_key(clave)
            guardada = guardar_configuracion(nueva)
            configurar_inicio_windows(guardada["system"]["start_with_windows"])
        except Exception as error:
            mostrar_estado(t["save_error"].format(error=error), False)
            return
        mostrar_estado(t["saved"], True)

    def restaurar(e: Any = None) -> None:
        try:
            restaurar_configuracion()
            configurar_inicio_windows(False)
        except Exception as error:
            mostrar_estado(t["restore_error"].format(error=error), False)
            return
        mostrar_estado(t["restored"], True)

    def fila_slider(etiqueta: str, control: ft.Slider, sufijo: str) -> ft.Row:
        valor = ft.Text(f"{round(control.value or 0)} {sufijo}", color=TEXTO, weight=ft.FontWeight.BOLD)
        def actualizar(e: Any = None) -> None:
            valor.value = f"{round(control.value or 0)} {sufijo}"
            page.update()
        control.on_change = actualizar
        return ft.Row(controls=[ft.Text(etiqueta, color=TEXTO, width=150), control, valor])

    contenido = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Text(t["title"], size=28, weight=ft.FontWeight.BOLD, color=TEXTO),
                            ft.Text(t["subtitle"], color=TEXTO_SECUNDARIO),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text("1.0.1", color=TEXTO, bgcolor=ACENTO, weight=ft.FontWeight.BOLD),
                ]
            ),
            estado,
            tarjeta(t["language"], t["language_note"], [idioma]),
            tarjeta(
                t["gemini"],
                t["gemini_sub"],
                [
                    campo_api_key,
                    ft.Text(t["api_ready"] if api_key_actual else t["api_missing"], size=12, color=EXITO if api_key_actual else TEXTO_SECUNDARIO),
                    ft.Text(t["api_privacy"], size=12, color=TEXTO_SECUNDARIO),
                ],
            ),
            tarjeta(t["preview"], t["preview_sub"], [vista_previa]),
            tarjeta(
                t["appearance"],
                t["appearance_sub"],
                [
                    ft.Row(controls=[color_principal, color_texto, color_secundario], wrap=True, spacing=12),
                    ft.Row(controls=[color_borde, posicion], wrap=True, spacing=12),
                    fila_slider(t["transparency"], transparencia, "%"),
                    fila_slider(t["font_size"], fuente, "px"),
                    fila_slider(t["radius"], radio, "px"),
                    fila_slider(t["margin"], margen, "px"),
                ],
            ),
            tarjeta(
                t["behavior"],
                t["behavior_sub"],
                [fila_slider(t["visible_time"], tiempo, "s"), click_through],
            ),
            tarjeta(
                t["hotkeys"],
                t["hotkeys_sub"],
                [
                    ft.Row(controls=[atajo_abrir, atajo_config], wrap=True, spacing=12),
                    ft.Row(controls=[atajo_cerrar, atajo_cerrar_alt], wrap=True, spacing=12),
                    ft.Text(t["fixed_hotkeys"], size=12, color=TEXTO_SECUNDARIO),
                ],
            ),
            tarjeta(t["system"], t["system_sub"], [inicio_windows]),
            ft.Row(
                controls=[
                    ft.Button(content=t["save"], icon=ft.Icons.SAVE, bgcolor=ACENTO, color=TEXTO, on_click=guardar),
                    ft.OutlinedButton(content=t["restore"], icon=ft.Icons.RESTART_ALT, on_click=restaurar),
                ],
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
