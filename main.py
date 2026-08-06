from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

import keyboard

from config_manager import (
    ARCHIVO_CONFIG,
    CONFIGURACION_PREDETERMINADA,
    cargar_configuracion,
)


# ══════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════

CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_POPUP = CARPETA_PROYECTO / "popup.py"
ARCHIVO_CONFIG_APP = CARPETA_PROYECTO / "config.py"
ARCHIVO_MULTIMODAL = CARPETA_PROYECTO / "multimodal.py"

ARCHIVO_CONTROL = (
    Path(tempfile.gettempdir())
    / f"novalens_control_{os.getpid()}.json"
)
ARCHIVO_CONTROL_TEMPORAL = ARCHIVO_CONTROL.with_suffix(".tmp")

ATAJO_PANTALLA = "p+shift+s"
ATAJO_AUDIO = "p+shift+a"


# ══════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════

proceso_popup: subprocess.Popen | None = None
proceso_configuracion: subprocess.Popen | None = None
procesos_multimodales: dict[str, subprocess.Popen] = {}

bloqueo_estado = threading.Lock()
bloqueo_control = threading.Lock()
bloqueo_atajos = threading.Lock()

novalens_cerrando = threading.Event()

ultimo_atajo_abrir = 0.0
mutex_instancia = None

identificadores_atajos: list[object] = []


# ══════════════════════════════════════════════
# SINGLE INSTANCE
# ══════════════════════════════════════════════

def asegurar_instancia_unica() -> None:
    global mutex_instancia

    if os.name != "nt":
        return

    mutex_instancia = ctypes.windll.kernel32.CreateMutexW(
        None,
        False,
        "NovaLens_Background_Instance",
    )

    ERROR_ALREADY_EXISTS = 183

    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        sys.exit(0)


# ══════════════════════════════════════════════
# COMMUNICATION WITH popup.py
# ══════════════════════════════════════════════

def enviar_comando(comando: str) -> None:
    datos = {
        "id": time.time_ns(),
        "command": comando,
    }

    with bloqueo_control:
        try:
            ARCHIVO_CONTROL_TEMPORAL.write_text(
                json.dumps(datos, ensure_ascii=False),
                encoding="utf-8",
            )
            os.replace(
                ARCHIVO_CONTROL_TEMPORAL,
                ARCHIVO_CONTROL,
            )
        except OSError:
            pass


def eliminar_archivos_control() -> None:
    for ruta in (
        ARCHIVO_CONTROL,
        ARCHIVO_CONTROL_TEMPORAL,
    ):
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass


# ══════════════════════════════════════════════
# TEXT POPUP PROCESS
# ══════════════════════════════════════════════

def popup_esta_ejecutandose() -> bool:
    return proceso_popup is not None and proceso_popup.poll() is None


def vigilar_popup(proceso: subprocess.Popen) -> None:
    global proceso_popup

    proceso.wait()

    with bloqueo_estado:
        if proceso_popup is proceso:
            proceso_popup = None


def iniciar_popup() -> None:
    global proceso_popup

    if not ARCHIVO_POPUP.exists():
        return

    enviar_comando("activate")

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proceso = subprocess.Popen(
            [
                sys.executable,
                str(ARCHIVO_POPUP),
                str(ARCHIVO_CONTROL),
            ],
            cwd=str(CARPETA_PROYECTO),
            creationflags=creation_flags,
        )
    except Exception:
        return

    proceso_popup = proceso

    threading.Thread(
        target=vigilar_popup,
        args=(proceso,),
        daemon=True,
    ).start()


def activar_popup() -> None:
    global ultimo_atajo_abrir

    if novalens_cerrando.is_set():
        return

    ahora = time.monotonic()

    if ahora - ultimo_atajo_abrir < 0.30:
        return

    ultimo_atajo_abrir = ahora

    with bloqueo_estado:
        if popup_esta_ejecutandose():
            enviar_comando("activate")
            return

        iniciar_popup()


def detener_popup_residente() -> None:
    global proceso_popup

    with bloqueo_estado:
        proceso = proceso_popup

    if proceso is None or proceso.poll() is not None:
        return

    enviar_comando("quit")

    try:
        proceso.wait(timeout=1.5)
    except subprocess.TimeoutExpired:
        try:
            proceso.terminate()
            proceso.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proceso.kill()
        except Exception:
            pass
    except Exception:
        pass

    with bloqueo_estado:
        if proceso_popup is proceso:
            proceso_popup = None


# ══════════════════════════════════════════════
# SCREEN AND AUDIO PROCESSES
# ══════════════════════════════════════════════

def vigilar_multimodal(modo: str, proceso: subprocess.Popen) -> None:
    proceso.wait()

    with bloqueo_estado:
        if procesos_multimodales.get(modo) is proceso:
            procesos_multimodales.pop(modo, None)


def abrir_multimodal(modo: str) -> None:
    if (
        novalens_cerrando.is_set()
        or modo not in {"screen", "audio"}
        or not ARCHIVO_MULTIMODAL.exists()
    ):
        return

    with bloqueo_estado:
        proceso_actual = procesos_multimodales.get(modo)

        if proceso_actual is not None and proceso_actual.poll() is None:
            return

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_MULTIMODAL),
                    modo,
                ],
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            return

        procesos_multimodales[modo] = proceso

    threading.Thread(
        target=vigilar_multimodal,
        args=(modo, proceso),
        daemon=True,
    ).start()


def analizar_pantalla() -> None:
    abrir_multimodal("screen")


def grabar_pregunta_audio() -> None:
    abrir_multimodal("audio")


def detener_procesos_multimodales() -> None:
    with bloqueo_estado:
        procesos = list(procesos_multimodales.values())
        procesos_multimodales.clear()

    for proceso in procesos:
        if proceso.poll() is not None:
            continue

        try:
            proceso.terminate()
            proceso.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proceso.kill()
        except Exception:
            pass


# ══════════════════════════════════════════════
# SETTINGS WINDOW
# ══════════════════════════════════════════════

def vigilar_config_app(proceso: subprocess.Popen) -> None:
    global proceso_configuracion

    proceso.wait()

    with bloqueo_estado:
        if proceso_configuracion is proceso:
            proceso_configuracion = None


def abrir_configuracion() -> None:
    global proceso_configuracion

    if novalens_cerrando.is_set() or not ARCHIVO_CONFIG_APP.exists():
        return

    with bloqueo_estado:
        if (
            proceso_configuracion is not None
            and proceso_configuracion.poll() is None
        ):
            return

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_CONFIG_APP),
                ],
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            return

        proceso_configuracion = proceso

    threading.Thread(
        target=vigilar_config_app,
        args=(proceso,),
        daemon=True,
    ).start()


# ══════════════════════════════════════════════
# DYNAMIC HOTKEYS
# ══════════════════════════════════════════════

def quitar_atajos_registrados() -> None:
    global identificadores_atajos

    for identificador in identificadores_atajos:
        try:
            keyboard.remove_hotkey(identificador)
        except Exception:
            pass

    identificadores_atajos = []


def agregar_atajo_seguro(
    atajo: str,
    predeterminado: str,
    accion: Callable[[], None],
    usados: set[str],
) -> None:
    candidatos = [atajo, predeterminado]

    for candidato in candidatos:
        candidato = candidato.strip().lower()

        if not candidato or candidato in usados:
            continue

        try:
            identificador = keyboard.add_hotkey(
                candidato,
                accion,
                suppress=True,
                trigger_on_release=True,
            )
        except Exception:
            continue

        identificadores_atajos.append(identificador)
        usados.add(candidato)
        return


def registrar_atajos() -> None:
    config = cargar_configuracion()
    atajos = config["hotkeys"]
    predeterminados = CONFIGURACION_PREDETERMINADA["hotkeys"]

    with bloqueo_atajos:
        quitar_atajos_registrados()

        usados: set[str] = set()

        agregar_atajo_seguro(
            atajos["open"],
            predeterminados["open"],
            activar_popup,
            usados,
        )
        agregar_atajo_seguro(
            atajos["settings"],
            predeterminados["settings"],
            abrir_configuracion,
            usados,
        )
        agregar_atajo_seguro(
            atajos["close"],
            predeterminados["close"],
            cerrar_novalens,
            usados,
        )
        agregar_atajo_seguro(
            atajos["close_alt"],
            predeterminados["close_alt"],
            cerrar_novalens,
            usados,
        )

        # Multimodal Beta hotkeys. They will become configurable later.
        agregar_atajo_seguro(
            ATAJO_PANTALLA,
            ATAJO_PANTALLA,
            analizar_pantalla,
            usados,
        )
        agregar_atajo_seguro(
            ATAJO_AUDIO,
            ATAJO_AUDIO,
            grabar_pregunta_audio,
            usados,
        )


def obtener_marca_config() -> int:
    try:
        return ARCHIVO_CONFIG.stat().st_mtime_ns
    except OSError:
        return 0


def vigilar_cambios_configuracion() -> None:
    ultima_marca = obtener_marca_config()

    while not novalens_cerrando.wait(0.50):
        marca_actual = obtener_marca_config()

        if marca_actual == 0 or marca_actual == ultima_marca:
            continue

        ultima_marca = marca_actual
        registrar_atajos()

        # popup.py reads the configuration when it starts.
        # Closing it here makes the next launch use the new settings.
        detener_popup_residente()


# ══════════════════════════════════════════════
# COMPLETELY CLOSE NOVA LENS
# ══════════════════════════════════════════════

def cerrar_novalens() -> None:
    global proceso_configuracion

    if novalens_cerrando.is_set():
        return

    novalens_cerrando.set()

    detener_popup_residente()
    detener_procesos_multimodales()

    with bloqueo_estado:
        proceso_config = proceso_configuracion

    if proceso_config is not None and proceso_config.poll() is None:
        try:
            proceso_config.terminate()
            proceso_config.wait(timeout=1)
        except subprocess.TimeoutExpired:
            proceso_config.kill()
        except Exception:
            pass

    try:
        keyboard.unhook_all_hotkeys()
    except Exception:
        pass

    eliminar_archivos_control()
    os._exit(0)


# ══════════════════════════════════════════════
# RESIDENT PROCESS
# ══════════════════════════════════════════════

def main() -> None:
    asegurar_instancia_unica()
    eliminar_archivos_control()

    # Create config.json automatically on the first run.
    cargar_configuracion()

    registrar_atajos()

    threading.Thread(
        target=vigilar_cambios_configuracion,
        daemon=True,
    ).start()

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        cerrar_novalens()


if __name__ == "__main__":
    main()
