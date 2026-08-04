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

import keyboard


# ══════════════════════════════════════════════
# RUTAS Y ATAJOS
# ══════════════════════════════════════════════

CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_POPUP = CARPETA_PROYECTO / "popup.py"

ATAJO_ABRIR = "p+enter"
ATAJO_CERRAR_BACKSPACE = "p+backspace"
ATAJO_CERRAR_DELETE = "p+delete"

# Archivo utilizado para enviar órdenes al popup residente.
ARCHIVO_CONTROL = (
    Path(tempfile.gettempdir())
    / f"novalens_control_{os.getpid()}.json"
)

ARCHIVO_CONTROL_TEMPORAL = ARCHIVO_CONTROL.with_suffix(".tmp")


# ══════════════════════════════════════════════
# ESTADO
# ══════════════════════════════════════════════

proceso_popup: subprocess.Popen | None = None

bloqueo_estado = threading.Lock()
bloqueo_control = threading.Lock()

novalens_cerrando = threading.Event()

ultimo_atajo_abrir = 0.0
mutex_instancia = None


# ══════════════════════════════════════════════
# EVITAR DOS INSTANCIAS
# ══════════════════════════════════════════════

def asegurar_instancia_unica() -> None:
    """
    Impide ejecutar NovaLens dos veces al mismo tiempo.
    """

    global mutex_instancia

    if os.name != "nt":
        return

    mutex_instancia = ctypes.windll.kernel32.CreateMutexW(
        None,
        False,
        "NovaLens_Background_Instance",
    )

    ERROR_ALREADY_EXISTS = 183

    if (
        ctypes.windll.kernel32.GetLastError()
        == ERROR_ALREADY_EXISTS
    ):
        sys.exit(0)


# ══════════════════════════════════════════════
# COMUNICACIÓN CON popup.py
# ══════════════════════════════════════════════

def enviar_comando(comando: str) -> None:
    """
    Escribe una orden para popup.py de forma atómica.

    Comandos válidos:
        activate
        quit
    """

    datos = {
        "id": time.time_ns(),
        "command": comando,
    }

    with bloqueo_control:
        try:
            ARCHIVO_CONTROL_TEMPORAL.write_text(
                json.dumps(
                    datos,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            os.replace(
                ARCHIVO_CONTROL_TEMPORAL,
                ARCHIVO_CONTROL,
            )

        except OSError:
            pass


def eliminar_archivos_control() -> None:
    """
    Elimina archivos temporales usados por NovaLens.
    """

    for ruta in (
        ARCHIVO_CONTROL,
        ARCHIVO_CONTROL_TEMPORAL,
    ):
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass


# ══════════════════════════════════════════════
# CONTROL DEL PROCESO DEL POPUP
# ══════════════════════════════════════════════

def popup_esta_ejecutandose() -> bool:
    return (
        proceso_popup is not None
        and proceso_popup.poll() is None
    )


def vigilar_popup(proceso: subprocess.Popen) -> None:
    """
    Detecta si popup.py terminó inesperadamente.
    """

    global proceso_popup

    proceso.wait()

    with bloqueo_estado:
        if proceso_popup is proceso:
            proceso_popup = None


def iniciar_popup() -> None:
    """
    Inicia popup.py una sola vez.

    Después se mantiene vivo y se oculta o muestra
    mediante órdenes.
    """

    global proceso_popup

    if not ARCHIVO_POPUP.exists():
        return

    # popup.py inicia oculto y lee esta orden al arrancar.
    enviar_comando("activate")

    creation_flags = getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0,
    )

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

    hilo = threading.Thread(
        target=vigilar_popup,
        args=(proceso,),
        daemon=True,
    )

    hilo.start()


def activar_popup() -> None:
    """
    P + Enter:

    - Inicia el popup si todavía no existe.
    - Si ya existe, lo reactiva.
    - Desactiva el click-through.
    - Lo devuelve al frente.
    """

    global ultimo_atajo_abrir

    if novalens_cerrando.is_set():
        return

    ahora = time.monotonic()

    # Evita varias activaciones por mantener las teclas presionadas.
    if ahora - ultimo_atajo_abrir < 0.30:
        return

    ultimo_atajo_abrir = ahora

    with bloqueo_estado:
        if popup_esta_ejecutandose():
            enviar_comando("activate")
            return

        iniciar_popup()


# ══════════════════════════════════════════════
# CERRAR NOVALENS COMPLETAMENTE
# ══════════════════════════════════════════════

def cerrar_novalens() -> None:
    """
    P + Backspace o P + Delete:

    1. Ordena cerrar el popup.
    2. Termina el proceso si no responde.
    3. Quita los atajos.
    4. Cierra NovaLens por completo.
    """

    global proceso_popup

    if novalens_cerrando.is_set():
        return

    novalens_cerrando.set()

    enviar_comando("quit")

    with bloqueo_estado:
        proceso = proceso_popup

    if proceso is not None and proceso.poll() is None:
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

    try:
        keyboard.unhook_all_hotkeys()
    except Exception:
        pass

    eliminar_archivos_control()

    os._exit(0)


# ══════════════════════════════════════════════
# NOVALENS RESIDENTE
# ══════════════════════════════════════════════

def main() -> None:
    asegurar_instancia_unica()
    eliminar_archivos_control()

    keyboard.add_hotkey(
        ATAJO_ABRIR,
        activar_popup,
        suppress=True,
        trigger_on_release=True,
    )

    keyboard.add_hotkey(
        ATAJO_CERRAR_BACKSPACE,
        cerrar_novalens,
        suppress=True,
        trigger_on_release=True,
    )

    keyboard.add_hotkey(
        ATAJO_CERRAR_DELETE,
        cerrar_novalens,
        suppress=True,
        trigger_on_release=True,
    )

    try:
        # NovaLens queda vivo sin consumir CPU constantemente.
        keyboard.wait()

    except KeyboardInterrupt:
        cerrar_novalens()


if __name__ == "__main__":
    main()