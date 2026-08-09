from __future__ import annotations

import copy
import sys
from pathlib import Path
from typing import Any

import flet as ft
import keyboard

from app_info import APP_VERSION
from bubble_layout import (
    eliminar_archivo_sesion,
    escribir_estado_desbloqueo,
    leer_posicion,
)
from config_manager import (
    CONFIGURACION_PREDETERMINADA,
    cargar_api_key,
    cargar_configuracion,
    color_con_transparencia,
    configurar_inicio_windows,
    es_color_hex,
    guardar_api_key,
    guardar_configuracion,
    restaurar_configuracion,
)
from runtime_control import ACTION_RESTART_APP, escribir_accion_runtime

FONDO = "#17110E"
PANEL = "#241914"
PANEL_SECUNDARIO = "#2E211B"
TEXTO = "#FFF4E8"
TEXTO_SECUNDARIO = "#CDB7A8"
ACENTO = "#A86F4B"
BORDE = "#513A2E"
ERROR = "#FF8A80"
EXITO = "#9BE59B"

SETTINGS_SECTION_KEYS = (
    "general",
    "interface",
    "visual",
    "controls",
    "multimedia",
    "accessibility",
)


def ruta_recurso(ruta_relativa: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / ruta_relativa)


RUTA_LOGO = ruta_recurso("assets/NovaLens.png")

TRADUCCIONES = {
    "english": {
        "window_title": "Nova Lens Settings",
        "title": "Nova Lens Settings",
        "subtitle": "Customize the popup and connect your own Gemini account.",
        "welcome_title": "Welcome to Nova Lens",
        "welcome_subtitle": "Let's prepare your desktop assistant. Complete the steps below, review the remaining settings, and save your changes.",
        "welcome_card_title": "First-time setup",
        "welcome_card_sub": "Everything Nova Lens needs is available in this Settings window.",
        "welcome_required": "Required",
        "welcome_optional": "Customize",
        "welcome_step_key": "Connect Google Gemini",
        "welcome_step_key_sub": "Paste your personal Gemini API key. Nova Lens stores it only on this device.",
        "welcome_step_interface": "Choose your interface",
        "welcome_step_interface_sub": "Select the language, colors, popup position, and normal or compact mode.",
        "welcome_step_controls": "Set your controls",
        "welcome_step_controls_sub": "Review text, screen, audio, Settings, and close shortcuts.",
        "welcome_step_save": "Save and start",
        "welcome_step_save_sub": "Press Save changes at the bottom. Nova Lens will remember this setup.",
        "setup_complete": "Welcome setup complete. Nova Lens is ready to use.",
        "local": "Changes are stored locally on this device.",
        "language": "Language",
        "english": "English",
        "spanish": "Spanish",
        "language_note": "The selected language is applied after saving and reopening Nova Lens.",
        "sections": "Settings sections",
        "sections_sub": "Choose what you want to configure.",
        "nav_general": "General",
        "nav_interface": "Interface",
        "nav_visual": "Visual",
        "nav_controls": "Controls",
        "nav_multimedia": "Audio & screen",
        "nav_accessibility": "Accessibility",
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
        "display_mode": "Display mode",
        "normal_mode": "Normal",
        "compact_mode": "Compact",
        "transparency": "Transparency",
        "font_size": "Font size",
        "radius": "Rounded corners",
        "margin": "Screen margin",
        "interface": "Interface",
        "interface_sub": "Popup mode, placement, and floating controls.",
        "accessibility": "Accessibility",
        "accessibility_sub": "Text readability, response time, and pointer behavior.",
        "behavior": "Behavior",
        "behavior_sub": "Visible time and behavior when focus is lost.",
        "visible_time": "Visible time",
        "click_through": "Allow click-through when focus is lost",
        "control_bubble": "Show the Open / Close / Reset control bubble",
        "unlock_bubbles": "Unlock floating bubbles to move them",
        "unlock_bubbles_help": "Turn this on, drag the microphone bubble and the Open / Close / Reset bubble, then press Save changes to keep their new positions.",
        "audio": "Recent audio",
        "audio_sub": "Control the rolling microphone buffer used by Nova Lens.",
        "audio_enabled": "Keep recent microphone audio available",
        "audio_duration": "Audio duration",
        "audio_indicator": "Show the microphone activity indicator",
        "audio_privacy": "Audio stays only in memory until you use {shortcut}. Disabling this option stops the microphone immediately.",
        "screen_capture": "Screen region",
        "screen_capture_sub": "Choose exactly which part of the screen Gemini receives.",
        "screen_region_help": "Press {shortcut}, drag a rectangle, and release to analyze only that region. Press Esc or right-click to cancel.",
        "hotkeys": "Keyboard shortcuts",
        "hotkeys_sub": "Use key+key format. Changes apply after saving.",
        "open": "Open or reactivate",
        "settings": "Open Settings",
        "screen_hotkey": "Analyze screen region",
        "audio_hotkey": "Analyze recent audio",
        "close": "Close Nova Lens",
        "close_alt": "Alternative close shortcut",
        "system": "System",
        "system_sub": "Control how Nova Lens starts in Windows.",
        "startup": "Start Nova Lens automatically with Windows",
        "reset_app": "Reset Nova Lens",
        "reset_help": "Completely close and reopen Nova Lens if a floating bubble or background component stops responding.",
        "restarting": "Nova Lens is restarting…",
        "reset_error": "I could not request the restart. Close Settings and try again.",
        "save": "Save changes",
        "restore": "Restore defaults",
        "saved": "Settings and API key saved. Restart Nova Lens to apply the language everywhere.",
        "restored": "Default settings restored. The API key was not deleted.",
        "need_key": "Paste your Google Gemini API key before saving.",
        "invalid_color": "Invalid color format in: {fields}. Use values such as #522E18.",
        "empty_hotkey": "Shortcuts cannot be empty: {fields}",
        "invalid_hotkey": "Invalid shortcut format in: {fields}",
        "duplicate_hotkey": "Each shortcut must be unique. Duplicated: {fields}",
        "save_error": "Could not save settings: {error}",
        "restore_error": "Could not restore settings: {error}",
    },
    "spanish": {
        "window_title": "Configuración de Nova Lens",
        "title": "Configuración de Nova Lens",
        "subtitle": "Personalizá el popup y conectá tu propia cuenta de Gemini.",
        "welcome_title": "Bienvenido a Nova Lens",
        "welcome_subtitle": "Preparemos tu asistente de escritorio. Completá los pasos, revisá las demás opciones y guardá los cambios.",
        "welcome_card_title": "Configuración inicial",
        "welcome_card_sub": "Todo lo que Nova Lens necesita está disponible en esta ventana de configuración.",
        "welcome_required": "Obligatorio",
        "welcome_optional": "Personalizar",
        "welcome_step_key": "Conectá Google Gemini",
        "welcome_step_key_sub": "Pegá tu API key personal de Gemini. Nova Lens la guarda únicamente en este dispositivo.",
        "welcome_step_interface": "Elegí tu interfaz",
        "welcome_step_interface_sub": "Seleccioná idioma, colores, posición y modo normal o compacto.",
        "welcome_step_controls": "Configurá los controles",
        "welcome_step_controls_sub": "Revisá los atajos de texto, pantalla, audio, configuración y cierre.",
        "welcome_step_save": "Guardá y comenzá",
        "welcome_step_save_sub": "Presioná Guardar cambios al final. Nova Lens recordará esta configuración.",
        "setup_complete": "Configuración inicial completada. Nova Lens está listo para usarse.",
        "local": "Los cambios se guardan localmente en este dispositivo.",
        "language": "Idioma",
        "english": "Inglés",
        "spanish": "Español",
        "language_note": "El idioma seleccionado se aplica después de guardar y volver a abrir Nova Lens.",
        "sections": "Secciones de configuración",
        "sections_sub": "Elegí qué querés configurar.",
        "nav_general": "General",
        "nav_interface": "Interfaz",
        "nav_visual": "Visual",
        "nav_controls": "Controles",
        "nav_multimedia": "Audio y pantalla",
        "nav_accessibility": "Accesibilidad",
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
        "display_mode": "Modo de visualización",
        "normal_mode": "Normal",
        "compact_mode": "Compacto",
        "transparency": "Transparencia",
        "font_size": "Tamaño de fuente",
        "radius": "Bordes redondeados",
        "margin": "Margen de pantalla",
        "interface": "Interfaz",
        "interface_sub": "Modo, posición y controles flotantes del popup.",
        "accessibility": "Accesibilidad",
        "accessibility_sub": "Legibilidad del texto, tiempo de respuesta y comportamiento del puntero.",
        "behavior": "Comportamiento",
        "behavior_sub": "Tiempo visible y comportamiento al perder el foco.",
        "visible_time": "Tiempo visible",
        "click_through": "Permitir click-through cuando pierde el foco",
        "control_bubble": "Mostrar la burbuja de Abrir / Cerrar / Reiniciar",
        "unlock_bubbles": "Desbloquear las burbujas para moverlas",
        "unlock_bubbles_help": "Activá esta opción, arrastrá la burbuja del micrófono y la de Abrir / Cerrar / Reiniciar, y luego presioná Guardar cambios para conservar sus posiciones.",
        "audio": "Audio reciente",
        "audio_sub": "Controlá el búfer continuo del micrófono que usa Nova Lens.",
        "audio_enabled": "Mantener disponible el audio reciente del micrófono",
        "audio_duration": "Duración del audio",
        "audio_indicator": "Mostrar el indicador de actividad del micrófono",
        "audio_privacy": "El audio permanece solo en memoria hasta que usás {shortcut}. Desactivar esta opción detiene el micrófono inmediatamente.",
        "screen_capture": "Región de pantalla",
        "screen_capture_sub": "Elegí exactamente qué parte de la pantalla recibe Gemini.",
        "screen_region_help": "Presioná {shortcut}, arrastrá un rectángulo y soltá para analizar solo esa región. Presioná Esc o hacé clic derecho para cancelar.",
        "hotkeys": "Atajos de teclado",
        "hotkeys_sub": "Usá el formato tecla+tecla. Los cambios se aplican al guardar.",
        "open": "Abrir o reactivar",
        "settings": "Abrir configuración",
        "screen_hotkey": "Analizar región de pantalla",
        "audio_hotkey": "Analizar audio reciente",
        "close": "Cerrar Nova Lens",
        "close_alt": "Atajo alternativo para cerrar",
        "system": "Sistema",
        "system_sub": "Controlá cómo se inicia Nova Lens en Windows.",
        "startup": "Iniciar Nova Lens automáticamente con Windows",
        "reset_app": "Reiniciar Nova Lens",
        "reset_help": "Cerrá y volvé a abrir Nova Lens por completo si una burbuja o componente en segundo plano deja de responder.",
        "restarting": "Nova Lens se está reiniciando…",
        "reset_error": "No pude solicitar el reinicio. Cerrá Configuración e intentá nuevamente.",
        "save": "Guardar cambios",
        "restore": "Restaurar valores",
        "saved": "Configuración y API key guardadas. Reiniciá Nova Lens para aplicar el idioma en toda la app.",
        "restored": "Valores predeterminados restaurados. La API key no fue eliminada.",
        "need_key": "Pegá tu Google Gemini API key antes de guardar.",
        "invalid_color": "Formato inválido en: {fields}. Usá valores como #522E18.",
        "empty_hotkey": "No podés dejar atajos vacíos: {fields}",
        "invalid_hotkey": "Formato de atajo inválido en: {fields}",
        "duplicate_hotkey": "Cada atajo debe ser único. Repetidos: {fields}",
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


def paso_bienvenida(
    icono: str,
    titulo: str,
    descripcion: str,
    etiqueta: str,
    obligatorio: bool = False,
) -> ft.Container:
    return ft.Container(
        width=370,
        bgcolor=PANEL_SECUNDARIO,
        border=ft.Border.all(1, ACENTO if obligatorio else BORDE),
        border_radius=14,
        padding=14,
        content=ft.Row(
            controls=[
                ft.Container(
                    width=42,
                    height=42,
                    bgcolor=ACENTO if obligatorio else PANEL,
                    border_radius=12,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icono, color=TEXTO, size=22),
                ),
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    titulo,
                                    color=TEXTO,
                                    weight=ft.FontWeight.BOLD,
                                    expand=True,
                                ),
                                ft.Text(
                                    etiqueta,
                                    size=10,
                                    color=TEXTO,
                                    bgcolor=ACENTO if obligatorio else BORDE,
                                ),
                            ],
                        ),
                        ft.Text(
                            descripcion,
                            size=11,
                            color=TEXTO_SECUNDARIO,
                        ),
                    ],
                    spacing=5,
                    expand=True,
                ),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


async def main(page: ft.Page) -> None:
    archivo_desbloqueo = Path(sys.argv[1]) if len(sys.argv) >= 2 else None
    archivo_posicion_audio = Path(sys.argv[2]) if len(sys.argv) >= 3 else None
    archivo_posicion_control = Path(sys.argv[3]) if len(sys.argv) >= 4 else None
    archivo_acciones = Path(sys.argv[4]) if len(sys.argv) >= 5 else None
    escribir_estado_desbloqueo(archivo_desbloqueo, False)

    config = cargar_configuracion()
    api_key_actual = cargar_api_key()
    idioma_actual = config["system"].get("language", "english")
    t = TRADUCCIONES.get(idioma_actual, TRADUCCIONES["english"])

    page.title = t["window_title"]
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FONDO
    page.padding = 24
    page.window.width = 980
    page.window.height = 800
    page.window.min_width = 760
    page.window.min_height = 620
    page.window.resizable = True

    apariencia = config["appearance"]
    comportamiento = config["behavior"]
    audio = config["audio"]
    atajos = config["hotkeys"]
    sistema = config["system"]
    onboarding_activo = not bool(sistema.get("onboarding_completed", False))
    posiciones_guardadas = copy.deepcopy(config["bubble_positions"])

    estado = ft.Text(t["local"], size=12, color=TEXTO_SECUNDARIO)
    logo_novalens = ft.Container(
        width=58,
        height=58,
        border_radius=ft.BorderRadius.all(12),
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=ft.Image(
            src=RUTA_LOGO,
            width=58,
            height=58,
            fit=ft.BoxFit.COVER,
        ),
    )
    titulo_principal = ft.Text(
        t["welcome_title"] if onboarding_activo else t["title"],
        size=28,
        weight=ft.FontWeight.BOLD,
        color=TEXTO,
    )
    subtitulo_principal = ft.Text(
        t["welcome_subtitle"] if onboarding_activo else t["subtitle"],
        color=TEXTO_SECUNDARIO,
    )
    tarjeta_bienvenida = ft.Container(
        visible=onboarding_activo,
        bgcolor="#302018",
        border=ft.Border.all(1, ACENTO),
        border_radius=20,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.AUTO_AWESOME, color=ACENTO, size=30),
                        ft.Column(
                            controls=[
                                ft.Text(
                                    t["welcome_card_title"],
                                    size=20,
                                    weight=ft.FontWeight.BOLD,
                                    color=TEXTO,
                                ),
                                ft.Text(
                                    t["welcome_card_sub"],
                                    size=12,
                                    color=TEXTO_SECUNDARIO,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                    ],
                    spacing=12,
                ),
                ft.Row(
                    controls=[
                        paso_bienvenida(
                            ft.Icons.KEY,
                            t["welcome_step_key"],
                            t["welcome_step_key_sub"],
                            t["welcome_required"],
                            True,
                        ),
                        paso_bienvenida(
                            ft.Icons.PALETTE,
                            t["welcome_step_interface"],
                            t["welcome_step_interface_sub"],
                            t["welcome_optional"],
                        ),
                        paso_bienvenida(
                            ft.Icons.KEYBOARD,
                            t["welcome_step_controls"],
                            t["welcome_step_controls_sub"],
                            t["welcome_optional"],
                        ),
                        paso_bienvenida(
                            ft.Icons.CHECK_CIRCLE,
                            t["welcome_step_save"],
                            t["welcome_step_save_sub"],
                            t["welcome_required"],
                            True,
                        ),
                    ],
                    wrap=True,
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=16,
        ),
    )

    def actualizar_estado_onboarding(completado: bool) -> None:
        nonlocal onboarding_activo
        onboarding_activo = not bool(completado)
        tarjeta_bienvenida.visible = onboarding_activo
        titulo_principal.value = (
            t["welcome_title"] if onboarding_activo else t["title"]
        )
        subtitulo_principal.value = (
            t["welcome_subtitle"] if onboarding_activo else t["subtitle"]
        )

    def campo(
        label: str,
        value: str,
        hint: str,
        width: int = 210,
        password: bool = False,
    ) -> ft.TextField:
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
    duracion_audio = ft.Slider(min=3, max=30, divisions=27, value=audio["duration_seconds"], active_color=ACENTO, expand=True)
    etiquetas_sliders: dict[int, tuple[ft.Text, str]] = {}

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
    modo_visual = ft.Dropdown(
        label=t["display_mode"],
        value=apariencia["display_mode"],
        width=260,
        filled=True,
        fill_color=PANEL_SECUNDARIO,
        border_color=BORDE,
        focused_border_color=ACENTO,
        color=TEXTO,
        options=[
            ft.DropdownOption(key="normal", text=t["normal_mode"]),
            ft.DropdownOption(key="compact", text=t["compact_mode"]),
        ],
    )

    click_through = ft.Switch(
        label=t["click_through"],
        value=comportamiento["click_through_on_blur"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    burbuja_control = ft.Switch(
        label=t["control_bubble"],
        value=comportamiento["show_control_bubble"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    desbloquear_burbujas = ft.Switch(
        label=t["unlock_bubbles"],
        value=False,
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    audio_habilitado = ft.Switch(
        label=t["audio_enabled"],
        value=audio["enabled"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    indicador_audio = ft.Switch(
        label=t["audio_indicator"],
        value=audio["show_indicator"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )
    inicio_windows = ft.Switch(
        label=t["startup"],
        value=sistema["start_with_windows"],
        active_color=ACENTO,
        label_text_style=ft.TextStyle(color=TEXTO),
    )

    def cambiar_bloqueo_burbujas(e: Any = None) -> None:
        escribir_estado_desbloqueo(
            archivo_desbloqueo,
            bool(desbloquear_burbujas.value),
        )

    desbloquear_burbujas.on_change = cambiar_bloqueo_burbujas

    atajo_abrir = campo(t["open"], atajos["open"], "p+enter", 310)
    atajo_config = campo(t["settings"], atajos["settings"], "p+shift+enter", 310)
    atajo_pantalla = campo(t["screen_hotkey"], atajos["screen"], "p+shift+s", 310)
    atajo_audio = campo(t["audio_hotkey"], atajos["audio"], "p+shift+a", 310)
    atajo_cerrar = campo(t["close"], atajos["close"], "p+backspace", 310)
    atajo_cerrar_alt = campo(t["close_alt"], atajos["close_alt"], "p+delete", 310)

    preview_title = ft.Text(
        "Nova Lens",
        color=apariencia["text_color"],
        size=20,
        weight=ft.FontWeight.BOLD,
    )
    preview_body = ft.Text(
        t["preview_text"],
        color=apariencia["text_color"],
        size=apariencia["font_size"],
    )
    vista_previa = ft.Container(
        height=132,
        bgcolor=color_con_transparencia(apariencia["primary_color"], apariencia["transparency"]),
        border=ft.Border.all(1, apariencia["border_color"]),
        border_radius=apariencia["border_radius"],
        padding=18,
        content=ft.Column(controls=[preview_title, preview_body]),
    )

    def mostrar_estado(mensaje: str, correcto: bool) -> None:
        estado.value = mensaje
        estado.color = EXITO if correcto else ERROR
        page.update()

    def actualizar_preview(e: Any = None) -> None:
        primary = (
            (color_principal.value or "").strip()
            if es_color_hex(color_principal.value)
            else apariencia["primary_color"]
        )
        text = (
            (color_texto.value or "").strip()
            if es_color_hex(color_texto.value)
            else apariencia["text_color"]
        )
        border = (
            (color_borde.value or "").strip()
            if es_color_hex(color_borde.value)
            else apariencia["border_color"]
        )

        vista_previa.bgcolor = color_con_transparencia(
            primary,
            round(transparencia.value or 0),
        )
        vista_previa.border = ft.Border.all(1, border)
        vista_previa.border_radius = round(radio.value or 0)
        preview_title.color = text
        preview_body.color = text
        preview_body.size = round(fuente.value or 16)
        page.update()

    for control in (color_principal, color_texto, color_secundario, color_borde):
        control.on_change = actualizar_preview

    def normalizar_atajo(valor: str | None) -> str:
        return (valor or "").strip().lower()

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
            t["open"]: normalizar_atajo(atajo_abrir.value),
            t["settings"]: normalizar_atajo(atajo_config.value),
            t["screen_hotkey"]: normalizar_atajo(atajo_pantalla.value),
            t["audio_hotkey"]: normalizar_atajo(atajo_audio.value),
            t["close"]: normalizar_atajo(atajo_cerrar.value),
            t["close_alt"]: normalizar_atajo(atajo_cerrar_alt.value),
        }

        vacios = [nombre for nombre, valor in campos_atajos.items() if not valor]
        if vacios:
            mostrar_estado(t["empty_hotkey"].format(fields=", ".join(vacios)), False)
            return None

        invalidos_atajo: list[str] = []
        for nombre, valor in campos_atajos.items():
            try:
                keyboard.parse_hotkey(valor)
            except Exception:
                invalidos_atajo.append(nombre)
        if invalidos_atajo:
            mostrar_estado(t["invalid_hotkey"].format(fields=", ".join(invalidos_atajo)), False)
            return None

        vistos: dict[str, list[str]] = {}
        for nombre, valor in campos_atajos.items():
            vistos.setdefault(valor, []).append(nombre)
        repetidos = [
            ", ".join(nombres)
            for nombres in vistos.values()
            if len(nombres) > 1
        ]
        if repetidos:
            mostrar_estado(t["duplicate_hotkey"].format(fields="; ".join(repetidos)), False)
            return None

        posiciones = copy.deepcopy(posiciones_guardadas)
        posicion_audio = leer_posicion(archivo_posicion_audio)
        posicion_control = leer_posicion(archivo_posicion_control)
        if posicion_audio is not None:
            posiciones["audio"] = posicion_audio
        if posicion_control is not None:
            posiciones["control"] = posicion_control

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
                "display_mode": modo_visual.value or "normal",
            },
            "behavior": {
                "visible_seconds": round(tiempo.value or 10),
                "click_through_on_blur": bool(click_through.value),
                "show_control_bubble": bool(burbuja_control.value),
            },
            "audio": {
                "enabled": bool(audio_habilitado.value),
                "duration_seconds": round(duracion_audio.value or 10),
                "show_indicator": bool(indicador_audio.value),
            },
            "bubble_positions": posiciones,
            "hotkeys": {
                "open": campos_atajos[t["open"]],
                "settings": campos_atajos[t["settings"]],
                "screen": campos_atajos[t["screen_hotkey"]],
                "audio": campos_atajos[t["audio_hotkey"]],
                "close": campos_atajos[t["close"]],
                "close_alt": campos_atajos[t["close_alt"]],
            },
            "system": {
                "start_with_windows": bool(inicio_windows.value),
                "language": idioma.value or "english",
                "onboarding_completed": True,
            },
        }

    def aplicar_config_a_controles(datos: dict[str, Any]) -> None:
        ap = datos["appearance"]
        beh = datos["behavior"]
        audiocfg = datos["audio"]
        hk = datos["hotkeys"]
        syscfg = datos["system"]
        posiciones_guardadas.clear()
        posiciones_guardadas.update(
            copy.deepcopy(datos["bubble_positions"])
        )

        color_principal.value = ap["primary_color"]
        color_texto.value = ap["text_color"]
        color_secundario.value = ap["secondary_color"]
        color_borde.value = ap["border_color"]
        transparencia.value = ap["transparency"]
        fuente.value = ap["font_size"]
        radio.value = ap["border_radius"]
        margen.value = ap["margin"]
        posicion.value = ap["position"]
        modo_visual.value = ap["display_mode"]
        tiempo.value = beh["visible_seconds"]
        click_through.value = beh["click_through_on_blur"]
        burbuja_control.value = beh["show_control_bubble"]
        audio_habilitado.value = audiocfg["enabled"]
        duracion_audio.value = audiocfg["duration_seconds"]
        indicador_audio.value = audiocfg["show_indicator"]
        desbloquear_burbujas.value = False
        escribir_estado_desbloqueo(archivo_desbloqueo, False)
        atajo_abrir.value = hk["open"]
        atajo_config.value = hk["settings"]
        atajo_pantalla.value = hk["screen"]
        atajo_audio.value = hk["audio"]
        atajo_cerrar.value = hk["close"]
        atajo_cerrar_alt.value = hk["close_alt"]
        inicio_windows.value = syscfg["start_with_windows"]
        idioma.value = syscfg["language"]
        actualizar_estado_onboarding(syscfg["onboarding_completed"])
        for control in (
            transparencia,
            fuente,
            radio,
            margen,
            tiempo,
            duracion_audio,
        ):
            datos_valor = etiquetas_sliders.get(id(control))
            if datos_valor is not None:
                etiqueta_valor, sufijo = datos_valor
                etiqueta_valor.value = (
                    f"{round(control.value or 0)} {sufijo}"
                )
        actualizar_preview()

    def guardar(e: Any = None) -> None:
        era_onboarding = onboarding_activo
        nueva = leer_formulario()
        if nueva is None:
            return
        clave = (campo_api_key.value or "").strip()
        if not clave:
            mostrar_estado(t["need_key"], False)
            return
        desbloquear_burbujas.value = False
        escribir_estado_desbloqueo(archivo_desbloqueo, False)
        try:
            guardar_api_key(clave)
            guardada = guardar_configuracion(nueva)
            configurar_inicio_windows(guardada["system"]["start_with_windows"])
        except Exception as error:
            mostrar_estado(t["save_error"].format(error=error), False)
            return
        posiciones_guardadas.clear()
        posiciones_guardadas.update(
            copy.deepcopy(guardada["bubble_positions"])
        )
        eliminar_archivo_sesion(archivo_posicion_audio)
        eliminar_archivo_sesion(archivo_posicion_control)
        actualizar_estado_onboarding(True)
        mostrar_estado(
            t["setup_complete"] if era_onboarding else t["saved"],
            True,
        )

    def restaurar(e: Any = None) -> None:
        desbloquear_burbujas.value = False
        escribir_estado_desbloqueo(archivo_desbloqueo, False)
        eliminar_archivo_sesion(archivo_posicion_audio)
        eliminar_archivo_sesion(archivo_posicion_control)
        try:
            restaurada = restaurar_configuracion()
            configurar_inicio_windows(False)
            aplicar_config_a_controles(restaurada)
        except Exception as error:
            mostrar_estado(t["restore_error"].format(error=error), False)
            return
        mostrar_estado(t["restored"], True)

    def reiniciar_app(e: Any = None) -> None:
        if escribir_accion_runtime(
            archivo_acciones,
            ACTION_RESTART_APP,
        ):
            mostrar_estado(t["restarting"], True)
            return

        mostrar_estado(t["reset_error"], False)

    def fila_slider(etiqueta: str, control: ft.Slider, sufijo: str) -> ft.Row:
        valor = ft.Text(
            f"{round(control.value or 0)} {sufijo}",
            color=TEXTO,
            weight=ft.FontWeight.BOLD,
        )

        def actualizar(e: Any = None) -> None:
            valor.value = f"{round(control.value or 0)} {sufijo}"
            actualizar_preview()

        control.on_change = actualizar
        etiquetas_sliders[id(control)] = (valor, sufijo)
        return ft.Row(
            controls=[ft.Text(etiqueta, color=TEXTO, width=150), control, valor]
        )

    tarjeta_idioma = tarjeta(t["language"], t["language_note"], [idioma])
    tarjeta_gemini = tarjeta(
        t["gemini"],
        t["gemini_sub"],
        [
            campo_api_key,
            ft.Text(
                t["api_ready"] if api_key_actual else t["api_missing"],
                size=12,
                color=EXITO if api_key_actual else TEXTO_SECUNDARIO,
            ),
            ft.Text(t["api_privacy"], size=12, color=TEXTO_SECUNDARIO),
        ],
    )
    tarjeta_sistema = tarjeta(
        t["system"],
        t["system_sub"],
        [
            inicio_windows,
            ft.Divider(color=BORDE),
            ft.Text(
                t["reset_help"],
                size=12,
                color=TEXTO_SECUNDARIO,
            ),
            ft.OutlinedButton(
                content=t["reset_app"],
                icon=ft.Icons.RESTART_ALT_ROUNDED,
                on_click=reiniciar_app,
            ),
        ],
    )
    tarjeta_interfaz = tarjeta(
        t["interface"],
        t["interface_sub"],
        [
            ft.Row(
                controls=[posicion, modo_visual],
                wrap=True,
                spacing=12,
            ),
            burbuja_control,
            desbloquear_burbujas,
            ft.Text(
                t["unlock_bubbles_help"],
                size=12,
                color=TEXTO_SECUNDARIO,
            ),
        ],
    )
    tarjeta_visual = tarjeta(
        t["appearance"],
        t["appearance_sub"],
        [
            ft.Row(
                controls=[color_principal, color_texto, color_secundario],
                wrap=True,
                spacing=12,
            ),
            color_borde,
            fila_slider(t["transparency"], transparencia, "%"),
            fila_slider(t["radius"], radio, "px"),
            fila_slider(t["margin"], margen, "px"),
        ],
    )
    tarjeta_accesibilidad = tarjeta(
        t["accessibility"],
        t["accessibility_sub"],
        [
            fila_slider(t["font_size"], fuente, "px"),
            fila_slider(t["visible_time"], tiempo, "s"),
            click_through,
        ],
    )
    tarjeta_audio = tarjeta(
        t["audio"],
        t["audio_sub"],
        [
            audio_habilitado,
            fila_slider(t["audio_duration"], duracion_audio, "s"),
            indicador_audio,
            ft.Text(
                t["audio_privacy"].format(shortcut=atajos["audio"]),
                size=12,
                color=TEXTO_SECUNDARIO,
            ),
        ],
    )
    tarjeta_pantalla = tarjeta(
        t["screen_capture"],
        t["screen_capture_sub"],
        [
            ft.Text(
                t["screen_region_help"].format(shortcut=atajos["screen"]),
                size=12,
                color=TEXTO_SECUNDARIO,
            )
        ],
    )
    tarjeta_atajos = tarjeta(
        t["hotkeys"],
        t["hotkeys_sub"],
        [
            ft.Row(
                controls=[atajo_abrir, atajo_config],
                wrap=True,
                spacing=12,
            ),
            ft.Row(
                controls=[atajo_pantalla, atajo_audio],
                wrap=True,
                spacing=12,
            ),
            ft.Row(
                controls=[atajo_cerrar, atajo_cerrar_alt],
                wrap=True,
                spacing=12,
            ),
        ],
    )

    vistas_seccion = {
        "general": ft.Column(
            controls=[
                tarjeta_bienvenida,
                tarjeta_idioma,
                tarjeta_gemini,
                tarjeta_sistema,
            ],
            spacing=16,
            visible=True,
        ),
        "interface": ft.Column(
            controls=[tarjeta_interfaz],
            spacing=16,
            visible=False,
        ),
        "visual": ft.Column(
            controls=[
                tarjeta(t["preview"], t["preview_sub"], [vista_previa]),
                tarjeta_visual,
            ],
            spacing=16,
            visible=False,
        ),
        "controls": ft.Column(
            controls=[tarjeta_atajos],
            spacing=16,
            visible=False,
        ),
        "multimedia": ft.Column(
            controls=[tarjeta_audio, tarjeta_pantalla],
            spacing=16,
            visible=False,
        ),
        "accessibility": ft.Column(
            controls=[tarjeta_accesibilidad],
            spacing=16,
            visible=False,
        ),
    }

    botones_seccion: dict[str, ft.Button] = {}

    def cambiar_seccion(e: Any) -> None:
        clave = str(e.control.data)
        if clave not in vistas_seccion:
            return
        for nombre, vista in vistas_seccion.items():
            seleccionada = nombre == clave
            vista.visible = seleccionada
            botones_seccion[nombre].bgcolor = (
                ACENTO if seleccionada else PANEL_SECUNDARIO
            )
        page.update()

    iconos_seccion = {
        "general": ft.Icons.AUTO_AWESOME,
        "interface": ft.Icons.SETTINGS,
        "visual": ft.Icons.PALETTE,
        "controls": ft.Icons.KEYBOARD,
        "multimedia": ft.Icons.MIC,
        "accessibility": ft.Icons.VISIBILITY,
    }
    for clave in SETTINGS_SECTION_KEYS:
        boton = ft.Button(
            content=t[f"nav_{clave}"],
            icon=iconos_seccion[clave],
            data=clave,
            width=176,
            height=46,
            bgcolor=ACENTO if clave == "general" else PANEL_SECUNDARIO,
            color=TEXTO,
            on_click=cambiar_seccion,
        )
        botones_seccion[clave] = boton

    barra_secciones = ft.Container(
        width=204,
        bgcolor=PANEL,
        border=ft.Border.all(1, BORDE),
        border_radius=18,
        padding=14,
        content=ft.Column(
            controls=[
                ft.Text(
                    t["sections"],
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=TEXTO,
                ),
                ft.Text(t["sections_sub"], size=11, color=TEXTO_SECUNDARIO),
                ft.Divider(color=BORDE),
                *[botones_seccion[clave] for clave in SETTINGS_SECTION_KEYS],
            ],
            spacing=9,
        ),
    )

    area_seccion = ft.Column(
        controls=[vistas_seccion[clave] for clave in SETTINGS_SECTION_KEYS],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    acciones = ft.Row(
        controls=[
            ft.Button(
                content=t["save"],
                icon=ft.Icons.SAVE,
                bgcolor=ACENTO,
                color=TEXTO,
                on_click=guardar,
            ),
            ft.OutlinedButton(
                content=t["restore"],
                icon=ft.Icons.RESTART_ALT,
                on_click=restaurar,
            ),
        ],
        alignment=ft.MainAxisAlignment.END,
    )

    contenido = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    logo_novalens,
                    ft.Column(
                        controls=[titulo_principal, subtitulo_principal],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Text(
                        APP_VERSION,
                        color=TEXTO,
                        bgcolor=ACENTO,
                        weight=ft.FontWeight.BOLD,
                    ),
                ],
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            estado,
            ft.Row(
                controls=[
                    barra_secciones,
                    ft.Container(content=area_seccion, expand=True),
                ],
                spacing=16,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                expand=True,
            ),
            acciones,
        ],
        spacing=16,
        expand=True,
    )

    page.add(contenido)
    page.update()


if __name__ == "__main__":
    ft.run(main)
