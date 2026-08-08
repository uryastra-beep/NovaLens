from __future__ import annotations

import ctypes
import json
import math
import os
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any


def _escribir_json_atomico(ruta: Path | None, datos: dict[str, Any]) -> None:
    if ruta is None:
        return

    temporal = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")

    try:
        temporal.write_text(
            json.dumps(datos, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporal, ruta)
    except OSError:
        try:
            temporal.unlink(missing_ok=True)
        except OSError:
            pass


def _leer_json(ruta: Path | None) -> dict[str, Any]:
    if ruta is None:
        return {}

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    return datos if isinstance(datos, dict) else {}


def escribir_estado_desbloqueo(
    ruta: Path | None,
    desbloqueado: bool,
) -> None:
    _escribir_json_atomico(
        ruta,
        {
            "id": time.time_ns(),
            "unlocked": bool(desbloqueado),
        },
    )


def leer_estado_desbloqueo(ruta: Path | None) -> bool:
    return _leer_json(ruta).get("unlocked") is True


def _coordenada(valor: Any) -> int | None:
    if valor is None or isinstance(valor, bool):
        return None

    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(numero):
        return None

    return max(-1_000_000, min(1_000_000, int(round(numero))))


def normalizar_posicion(datos: Any) -> dict[str, int | None]:
    if not isinstance(datos, dict):
        datos = {}

    return {
        "left": _coordenada(datos.get("left")),
        "top": _coordenada(datos.get("top")),
    }


def escribir_posicion(
    ruta: Path | None,
    left: Any,
    top: Any,
) -> None:
    posicion = normalizar_posicion({"left": left, "top": top})
    if posicion["left"] is None or posicion["top"] is None:
        return

    _escribir_json_atomico(
        ruta,
        {
            "id": time.time_ns(),
            **posicion,
        },
    )


def leer_posicion(ruta: Path | None) -> dict[str, int | None] | None:
    posicion = normalizar_posicion(_leer_json(ruta))
    if posicion["left"] is None or posicion["top"] is None:
        return None
    return posicion


def eliminar_archivo_sesion(ruta: Path | None) -> None:
    if ruta is None:
        return

    try:
        ruta.unlink(missing_ok=True)
    except OSError:
        pass

    for temporal in ruta.parent.glob(f"{ruta.name}.*.tmp"):
        try:
            temporal.unlink(missing_ok=True)
        except OSError:
            pass


def obtener_escritorio_virtual(
    area_alternativa: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if os.name != "nt":
        return area_alternativa

    try:
        user32 = ctypes.windll.user32
        izquierda = int(user32.GetSystemMetrics(76))
        arriba = int(user32.GetSystemMetrics(77))
        ancho = int(user32.GetSystemMetrics(78))
        alto = int(user32.GetSystemMetrics(79))
        if ancho > 0 and alto > 0:
            return izquierda, arriba, ancho, alto
    except Exception:
        pass

    return area_alternativa


def resolver_posicion(
    posicion: Any,
    predeterminada: tuple[int, int],
    escritorio: tuple[int, int, int, int],
    tamano_ventana: tuple[int, int],
) -> tuple[int, int]:
    normalizada = normalizar_posicion(posicion)
    left = normalizada["left"]
    top = normalizada["top"]

    if left is None or top is None:
        return predeterminada

    x, y, ancho, alto = escritorio
    ancho_ventana, alto_ventana = tamano_ventana
    max_left = max(x, x + ancho - ancho_ventana)
    max_top = max(y, y + alto - alto_ventana)

    return (
        max(x, min(left, max_left)),
        max(y, min(top, max_top)),
    )


def obtener_posicion_ventana_proceso(
    titulo: str | None = None,
) -> tuple[int, int] | None:
    if os.name != "nt":
        return None

    user32 = ctypes.windll.user32

    if titulo:
        try:
            hwnd_titulo = user32.FindWindowW(None, titulo)
            if hwnd_titulo:
                rect_titulo = wintypes.RECT()
                if user32.GetWindowRect(
                    hwnd_titulo,
                    ctypes.byref(rect_titulo),
                ):
                    return int(rect_titulo.left), int(rect_titulo.top)
        except Exception:
            pass

    current_pid = os.getpid()
    resultado: list[tuple[int, int]] = []
    enum_proc = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HWND,
        wintypes.LPARAM,
    )

    @enum_proc
    def callback(hwnd: int, _lparam: int) -> bool:
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        if pid.value != current_pid or user32.GetParent(hwnd):
            return True

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        if rect.right - rect.left < 60 or rect.bottom - rect.top < 20:
            return True

        resultado.append((int(rect.left), int(rect.top)))
        return False

    try:
        user32.EnumWindows(callback, 0)
    except Exception:
        return None

    return resultado[0] if resultado else None
