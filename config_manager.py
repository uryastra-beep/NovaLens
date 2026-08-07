from __future__ import annotations

import copy
import json
import math
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
        "language": "english",
    },
}

PATRON_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def limitar(valor: Any, minimo: int, maximo: int, predeterminado: int) -> int:
    try:
        numero_float = float(valor)
        if not math.isfinite(numero_float):
            return predeterminado
        numero = int(round(numero_float))
    except (TypeError, ValueError, OverflowError):
        return predeterminado
    return max(minimo, min(numero, maximo))


def normalizar_bool(valor: Any, predeterminado: bool) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return bool(valor)
    if isinstance(valor, str):
        texto = valor.strip().lower()
        if texto in {"true", "1", "yes", "on"}:
            return True
        if texto in {"false", "0", "no", "off"}:
            return False
    return predeterminado


def es_color_hex(valor: Any) -> bool:
    return isinstance(valor, str) and bool(PATRON_COLOR.fullmatch(valor.strip()))


def normalizar_color(valor: Any, predeterminado: str) -> str:
    if not es_color_hex(valor):
        return predeterminado
    return valor.strip().upper()


def mezclar_diccionarios(base: dict[str, Any], nuevos: dict[str, Any]) -> dict[str, Any]:
    resultado = copy.deepcopy(base)
    for clave, valor in nuevos.items():
        # Known object sections must remain dictionaries. A syntactically valid
        # but structurally corrupted config file should never crash startup.
        if clave in resultado and isinstance(resultado[clave], dict):
            if isinstance(valor, dict):
                resultado[clave] = mezclar_diccionarios(resultado[clave], valor)
            continue
        resultado[clave] = valor
    return resultado


def _seccion_dict(config: dict[str, Any], nombre: str) -> dict[str, Any]:
    seccion = config.get(nombre)
    if isinstance(seccion, dict):
        return seccion
    predeterminada = CONFIGURACION_PREDETERMINADA[nombre]
    reemplazo = copy.deepcopy(predeterminada)
    config[nombre] = reemplazo
    return reemplazo


def validar_configuracion(datos: Any) -> dict[str, Any]:
    if not isinstance(datos, dict):
        datos = {}

    config = mezclar_diccionarios(CONFIGURACION_PREDETERMINADA, datos)
    apariencia = _seccion_dict(config, "appearance")
    apariencia_predeterminada = CONFIGURACION_PREDETERMINADA["appearance"]

    for clave in ("primary_color", "text_color", "secondary_color", "border_color"):
        apariencia[clave] = normalizar_color(
            apariencia.get(clave),
            apariencia_predeterminada[clave],
        )

    apariencia["transparency"] = limitar(apariencia.get("transparency"), 0, 90, 60)
    apariencia["font_size"] = limitar(apariencia.get("font_size"), 12, 24, 16)
    apariencia["border_radius"] = limitar(apariencia.get("border_radius"), 0, 36, 20)
    apariencia["margin"] = limitar(apariencia.get("margin"), 0, 32, 8)
    apariencia["position"] = (
        apariencia.get("position")
        if apariencia.get("position") in {"top", "bottom"}
        else "top"
    )

    comportamiento = _seccion_dict(config, "behavior")
    comportamiento["visible_seconds"] = limitar(
        comportamiento.get("visible_seconds"), 3, 60, 10
    )
    comportamiento["click_through_on_blur"] = normalizar_bool(
        comportamiento.get("click_through_on_blur"), True
    )

    atajos = _seccion_dict(config, "hotkeys")
    for clave, predeterminado in CONFIGURACION_PREDETERMINADA["hotkeys"].items():
        valor = atajos.get(clave)
        if not isinstance(valor, str) or not valor.strip():
            valor = predeterminado
        atajos[clave] = valor.strip().lower()

    sistema = _seccion_dict(config, "system")
    sistema["start_with_windows"] = normalizar_bool(
        sistema.get("start_with_windows"), False
    )
    idioma = str(sistema.get("language", "english")).strip().lower()
    sistema["language"] = idioma if idioma in {"english", "spanish"} else "english"

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
        raise ValueError("Google Gemini API key cannot be empty.")
    if "\n" in clave or "\r" in clave:
        raise ValueError("The API key contains invalid characters.")

    ARCHIVO_ENV.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVO_ENV_TEMPORAL.write_text(f"GEMINI_API_KEY={clave}\n", encoding="utf-8")
    os.replace(ARCHIVO_ENV_TEMPORAL, ARCHIVO_ENV)
    os.environ["GEMINI_API_KEY"] = clave
    return clave


def color_con_opacidad(color_hex: str, opacidad_porcentaje: int | float) -> str:
    color = normalizar_color(color_hex, "#000000")
    try:
        opacidad = float(opacidad_porcentaje)
    except (TypeError, ValueError, OverflowError):
        opacidad = 100.0
    if not math.isfinite(opacidad):
        opacidad = 100.0
    opacidad = max(0.0, min(opacidad, 100.0))
    alfa = round(255 * (opacidad / 100))
    return f"#{alfa:02X}{color[1:]}"


def color_con_transparencia(color_hex: str, transparencia_porcentaje: int | float) -> str:
    try:
        transparencia = float(transparencia_porcentaje)
    except (TypeError, ValueError, OverflowError):
        transparencia = 0.0
    if not math.isfinite(transparencia):
        transparencia = 0.0
    transparencia = max(0.0, min(transparencia, 100.0))
    return color_con_opacidad(color_hex, 100 - transparencia)


def obtener_pythonw() -> Path:
    pythonw_venv = CARPETA_PROYECTO / ".venv" / "Scripts" / "pythonw.exe"
    if pythonw_venv.exists():
        return pythonw_venv
    ejecutable = Path(sys.executable)
    candidato = ejecutable.with_name("pythonw.exe")
    return candidato if candidato.exists() else ejecutable


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
            winreg.SetValueEx(clave, NOMBRE_INICIO_WINDOWS, 0, winreg.REG_SZ, comando)
        else:
            try:
                winreg.DeleteValue(clave, NOMBRE_INICIO_WINDOWS)
            except FileNotFoundError:
                pass
