from __future__ import annotations

import copy
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_CONFIG = CARPETA_PROYECTO / "config.json"
ARCHIVO_CONFIG_TEMPORAL = CARPETA_PROYECTO / "config.tmp.json"
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"
ARCHIVO_ENV_TEMPORAL = CARPETA_PROYECTO / ".env.tmp"

NOMBRE_INICIO_WINDOWS = "NovaLens"

CONFIGURACION_PREDETERMINADA: dict[str, Any] = {
    "appearance": {
        "primary_color": "#522E18",
        "text_color": "#FFF4E8",
        "secondary_color": "#E8C9B2",
        "border_color": "#8A5738",
        "transparency": 60,
        "font_size": 16,
        "border_radius": 20,
        "margin": 8,
        "position": "top",
    },
    "behavior": {
        "visible_seconds": 10,
        "click_through_on_blur": True,
    },
    "hotkeys": {
        "open": "p+enter",
        "settings": "p+shift+enter",
        "close": "p+backspace",
        "close_alt": "p+delete",
    },
    "system": {
        "start_with_windows": False,
    },
}

PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def limitar(valor: Any, minimo: int, maximo: int, predeterminado: int) -> int:
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        return predeterminado

    return max(minimo, min(numero, maximo))


def es_color_hex(valor: Any) -> bool:
    return isinstance(valor, str) and bool(PATRON_COLOR.fullmatch(valor.strip()))


def normalizar_color(valor: Any, predeterminado: str) -> str:
    if not es_color_hex(valor):
        return predeterminado

    return valor.strip().upper()


def mezclar_diccionarios(base: dict[str, Any], nuevos: dict[str, Any]) -> dict[str, Any]:
    resultado = copy.deepcopy(base)

    for clave, valor in nuevos.items():
        if (
            clave in resultado
            and isinstance(resultado[clave], dict)
            and isinstance(valor, dict)
        ):
            resultado[clave] = mezclar_diccionarios(resultado[clave], valor)
        else:
            resultado[clave] = valor

    return resultado


def validar_configuracion(datos: Any) -> dict[str, Any]:
    if not isinstance(datos, dict):
        datos = {}

    config = mezclar_diccionarios(CONFIGURACION_PREDETERMINADA, datos)

    apariencia = config["appearance"]
    apariencia_predeterminada = CONFIGURACION_PREDETERMINADA["appearance"]

    apariencia["primary_color"] = normalizar_color(
        apariencia.get("primary_color"),
        apariencia_predeterminada["primary_color"],
    )
    apariencia["text_color"] = normalizar_color(
        apariencia.get("text_color"),
        apariencia_predeterminada["text_color"],
    )
    apariencia["secondary_color"] = normalizar_color(
        apariencia.get("secondary_color"),
        apariencia_predeterminada["secondary_color"],
    )
    apariencia["border_color"] = normalizar_color(
        apariencia.get("border_color"),
        apariencia_predeterminada["border_color"],
    )
    apariencia["transparency"] = limitar(
        apariencia.get("transparency"),
        0,
        90,
        apariencia_predeterminada["transparency"],
    )
    apariencia["font_size"] = limitar(
        apariencia.get("font_size"),
        12,
        24,
        apariencia_predeterminada["font_size"],
    )
    apariencia["border_radius"] = limitar(
        apariencia.get("border_radius"),
        0,
        36,
        apariencia_predeterminada["border_radius"],
    )
    apariencia["margin"] = limitar(
        apariencia.get("margin"),
        0,
        32,
        apariencia_predeterminada["margin"],
    )
    apariencia["position"] = (
        apariencia.get("position")
        if apariencia.get("position") in {"top", "bottom"}
        else apariencia_predeterminada["position"]
    )

    comportamiento = config["behavior"]
    comportamiento_predeterminado = CONFIGURACION_PREDETERMINADA["behavior"]

    comportamiento["visible_seconds"] = limitar(
        comportamiento.get("visible_seconds"),
        3,
        60,
        comportamiento_predeterminado["visible_seconds"],
    )
    comportamiento["click_through_on_blur"] = bool(
        comportamiento.get(
            "click_through_on_blur",
            comportamiento_predeterminado["click_through_on_blur"],
        )
    )

    atajos = config["hotkeys"]
    atajos_predeterminados = CONFIGURACION_PREDETERMINADA["hotkeys"]

    for clave in ("open", "settings", "close", "close_alt"):
        valor = atajos.get(clave)
        if not isinstance(valor, str) or not valor.strip():
            valor = atajos_predeterminados[clave]

        atajos[clave] = valor.strip().lower()

    sistema = config["system"]
    sistema["start_with_windows"] = bool(
        sistema.get("start_with_windows", False)
    )

    return config


def cargar_configuracion() -> dict[str, Any]:
    if not ARCHIVO_CONFIG.exists():
        configuracion = validar_configuracion(CONFIGURACION_PREDETERMINADA)
        guardar_configuracion(configuracion)
        return configuracion

    try:
        datos = json.loads(ARCHIVO_CONFIG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        datos = {}

    return validar_configuracion(datos)


def guardar_configuracion(datos: dict[str, Any]) -> dict[str, Any]:
    configuracion = validar_configuracion(datos)
    ARCHIVO_CONFIG.parent.mkdir(parents=True, exist_ok=True)

    ARCHIVO_CONFIG_TEMPORAL.write_text(
        json.dumps(configuracion, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(ARCHIVO_CONFIG_TEMPORAL, ARCHIVO_CONFIG)

    return configuracion


def restaurar_configuracion() -> dict[str, Any]:
    return guardar_configuracion(CONFIGURACION_PREDETERMINADA)


def cargar_api_key() -> str:
    try:
        lineas = ARCHIVO_ENV.read_text(encoding="utf-8").splitlines()
    except OSError:
        return os.getenv("GEMINI_API_KEY", "").strip()

    for linea in lineas:
        contenido = linea.strip()
        if not contenido or contenido.startswith("#"):
            continue

        nombre, separador, valor = contenido.partition("=")
        if separador and nombre.strip() == "GEMINI_API_KEY":
            clave = valor.strip()
            if len(clave) >= 2 and clave[0] == clave[-1] and clave[0] in {'"', "'"}:
                clave = clave[1:-1]
            return clave.strip()

    return ""


def guardar_api_key(valor: str) -> str:
    clave = (valor or "").strip()

    if not clave:
        raise ValueError("La API key de Google Gemini no puede estar vacía.")

    if "\n" in clave or "\r" in clave:
        raise ValueError("La API key contiene caracteres no válidos.")

    ARCHIVO_ENV.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ENV_TEMPORAL.write_text(
        f"GEMINI_API_KEY={clave}\n",
        encoding="utf-8",
    )
    os.replace(ARCHIVO_ENV_TEMPORAL, ARCHIVO_ENV)
    os.environ["GEMINI_API_KEY"] = clave
    return clave


def color_con_opacidad(color_hex: str, opacidad_porcentaje: int | float) -> str:
    color = normalizar_color(color_hex, "#000000")
    opacidad = max(0, min(float(opacidad_porcentaje), 100))
    alfa = round(255 * (opacidad / 100))
    return f"#{alfa:02X}{color[1:]}"


def color_con_transparencia(
    color_hex: str,
    transparencia_porcentaje: int | float,
) -> str:
    transparencia = max(0, min(float(transparencia_porcentaje), 100))
    return color_con_opacidad(color_hex, 100 - transparencia)


def obtener_pythonw() -> Path:
    pythonw_venv = CARPETA_PROYECTO / ".venv" / "Scripts" / "pythonw.exe"
    if pythonw_venv.exists():
        return pythonw_venv

    ejecutable = Path(sys.executable)
    candidato = ejecutable.with_name("pythonw.exe")

    if candidato.exists():
        return candidato

    return ejecutable


def configurar_inicio_windows(activar: bool) -> None:
    if os.name != "nt":
        return

    import winreg

    ruta_registro = r"Software\Microsoft\Windows\CurrentVersion\Run"

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        ruta_registro,
        0,
        winreg.KEY_SET_VALUE,
    ) as clave:
        if activar:
            pythonw = obtener_pythonw()
            main_py = CARPETA_PROYECTO / "main.py"
            comando = f'"{pythonw}" "{main_py}"'

            winreg.SetValueEx(
                clave,
                NOMBRE_INICIO_WINDOWS,
                0,
                winreg.REG_SZ,
                comando,
            )
        else:
            try:
                winreg.DeleteValue(clave, NOMBRE_INICIO_WINDOWS)
            except FileNotFoundError:
                pass
