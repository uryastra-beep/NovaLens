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
    cargar_api_key,
    cargar_configuracion,
)
from localization import tr
from rolling_audio import RollingAudioBuffer


# ══════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════

CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_POPUP = CARPETA_PROYECTO / "popup.py"
ARCHIVO_CONFIG_APP = CARPETA_PROYECTO / "config.py"
ARCHIVO_MULTIMODAL = CARPETA_PROYECTO / "multimodal.py"
ARCHIVO_INDICADOR_AUDIO = CARPETA_PROYECTO / "audio_indicator.py"
ARCHIVO_BURBUJA_CONTROL = CARPETA_PROYECTO / "control_bubble.py"

ARCHIVO_CONTROL = (
    Path(tempfile.gettempdir())
    / f"novalens_control_{os.getpid()}.json"
)
ARCHIVO_CONTROL_TEMPORAL = ARCHIVO_CONTROL.with_suffix(".tmp")
ARCHIVO_ACCIONES_BURBUJA = (
    Path(tempfile.gettempdir())
    / f"novalens_bubble_{os.getpid()}.json"
)

ATAJO_PANTALLA = "p+shift+s"
ATAJO_AUDIO = "p+shift+a"

FRECUENCIA_AUDIO = 16_000


# ══════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════

proceso_popup: subprocess.Popen | None = None
proceso_configuracion: subprocess.Popen | None = None
proceso_indicador_audio: subprocess.Popen | None = None
proceso_burbuja_control: subprocess.Popen | None = None
procesos_multimodales: dict[str, subprocess.Popen] = {}

bloqueo_estado = threading.Lock()
bloqueo_control = threading.Lock()
bloqueo_atajos = threading.Lock()
bloqueo_audio = threading.Lock()

novalens_cerrando = threading.Event()

ultimo_atajo_abrir = 0.0
mutex_instancia = None

identificadores_atajos: list[object] = []
archivos_audio_temporales: set[Path] = set()

buffer_audio = RollingAudioBuffer(
    duration_seconds=10,
    sample_rate=FRECUENCIA_AUDIO,
    channels=1,
)
error_buffer_audio = ""
audio_habilitado = True
duracion_buffer_audio = 10
mostrar_indicador_audio = True
mostrar_burbuja_control = True


# ══════════════════════════════════════════════
# CHILD PROCESS SHUTDOWN
# ══════════════════════════════════════════════

def terminar_arbol_proceso(
    proceso: subprocess.Popen | None,
    timeout: float = 1.0,
) -> None:
    """Stop one Nova Lens child and its Flet descendants on Windows."""
    if proceso is None:
        return

    try:
        if proceso.poll() is not None:
            return
    except Exception:
        return

    if os.name == "nt":
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            resultado = subprocess.run(
                [
                    "taskkill.exe",
                    "/PID",
                    str(proceso.pid),
                    "/T",
                    "/F",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=max(2.0, timeout + 1.0),
                creationflags=creation_flags,
                check=False,
            )

            if resultado.returncode == 0:
                try:
                    proceso.wait(timeout=timeout)
                except Exception:
                    pass
                return
        except (OSError, subprocess.TimeoutExpired):
            pass

    try:
        proceso.terminate()
        proceso.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            proceso.kill()
            proceso.wait(timeout=timeout)
        except Exception:
            pass
    except Exception:
        pass


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

    try:
        ARCHIVO_ACCIONES_BURBUJA.unlink(missing_ok=True)
    except OSError:
        pass

    for ruta in ARCHIVO_ACCIONES_BURBUJA.parent.glob(
        f"{ARCHIVO_ACCIONES_BURBUJA.name}.*.tmp"
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


def iniciar_popup() -> bool:
    global proceso_popup

    if not ARCHIVO_POPUP.exists():
        return False

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
        return False

    proceso_popup = proceso
    enviar_comando("activate")

    threading.Thread(
        target=vigilar_popup,
        args=(proceso,),
        daemon=True,
    ).start()

    return True


def activar_popup() -> None:
    global ultimo_atajo_abrir

    if novalens_cerrando.is_set():
        return

    if not cargar_api_key():
        abrir_configuracion()
        return

    ahora = time.monotonic()

    if ahora - ultimo_atajo_abrir < 0.30:
        return

    with bloqueo_estado:
        if popup_esta_ejecutandose():
            enviar_comando("activate")
            ultimo_atajo_abrir = ahora
            return

        if iniciar_popup():
            ultimo_atajo_abrir = ahora


def ocultar_popup_para_captura() -> None:
    with bloqueo_estado:
        activo = popup_esta_ejecutandose()

    if activo:
        enviar_comando("hide_now")


def detener_popup_residente() -> None:
    global proceso_popup

    with bloqueo_estado:
        proceso = proceso_popup

    if proceso is None:
        return

    terminar_arbol_proceso(proceso, timeout=1.5)

    with bloqueo_estado:
        if proceso_popup is proceso:
            proceso_popup = None


# ══════════════════════════════════════════════
# OPEN / CLOSE CONTROL BUBBLE
# ══════════════════════════════════════════════

def ejecutar_accion_burbuja(accion: str) -> None:
    if novalens_cerrando.is_set():
        return

    if accion == "open_popup":
        activar_popup()
    elif accion == "close_popup":
        ocultar_popup_para_captura()


def vigilar_acciones_burbuja() -> None:
    ultimo_id: object = None

    while not novalens_cerrando.wait(0.10):
        try:
            datos = json.loads(
                ARCHIVO_ACCIONES_BURBUJA.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            continue

        identificador = datos.get("id")
        if identificador is None or identificador == ultimo_id:
            continue

        ultimo_id = identificador
        accion = datos.get("action")
        if isinstance(accion, str):
            ejecutar_accion_burbuja(accion)


def vigilar_burbuja_control(proceso: subprocess.Popen) -> None:
    global proceso_burbuja_control

    proceso.wait()

    with bloqueo_estado:
        if proceso_burbuja_control is proceso:
            proceso_burbuja_control = None


def iniciar_burbuja_control() -> bool:
    global proceso_burbuja_control

    if (
        novalens_cerrando.is_set()
        or not mostrar_burbuja_control
        or not ARCHIVO_BURBUJA_CONTROL.exists()
    ):
        return False

    with bloqueo_estado:
        proceso_actual = proceso_burbuja_control
        if proceso_actual is not None and proceso_actual.poll() is None:
            return True

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_BURBUJA_CONTROL),
                    str(ARCHIVO_ACCIONES_BURBUJA),
                ],
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            return False

        proceso_burbuja_control = proceso

    threading.Thread(
        target=vigilar_burbuja_control,
        args=(proceso,),
        daemon=True,
    ).start()
    return True


def detener_burbuja_control() -> None:
    global proceso_burbuja_control

    with bloqueo_estado:
        proceso = proceso_burbuja_control
        proceso_burbuja_control = None

    terminar_arbol_proceso(proceso, timeout=1.5)


def aplicar_configuracion_burbuja(
    config: dict | None = None,
) -> None:
    global mostrar_burbuja_control

    configuracion = config or cargar_configuracion()
    nueva_visibilidad = bool(
        configuracion["behavior"]["show_control_bubble"]
    )

    # Recreate it after every saved setting so language, colors, margin, and
    # transparency are refreshed together with the rest of the interface.
    detener_burbuja_control()
    mostrar_burbuja_control = nueva_visibilidad

    if mostrar_burbuja_control:
        iniciar_burbuja_control()


# ══════════════════════════════════════════════
# MICROPHONE ACTIVITY INDICATOR
# ══════════════════════════════════════════════

def vigilar_indicador_audio(proceso: subprocess.Popen) -> None:
    global proceso_indicador_audio

    proceso.wait()

    with bloqueo_estado:
        if proceso_indicador_audio is proceso:
            proceso_indicador_audio = None


def iniciar_indicador_audio() -> bool:
    global proceso_indicador_audio

    if (
        novalens_cerrando.is_set()
        or not ARCHIVO_INDICADOR_AUDIO.exists()
    ):
        return False

    with bloqueo_estado:
        proceso_actual = proceso_indicador_audio
        pantalla = procesos_multimodales.get("screen")

        if proceso_actual is not None and proceso_actual.poll() is None:
            return True

        if pantalla is not None and pantalla.poll() is None:
            return False

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_INDICADOR_AUDIO),
                    str(duracion_buffer_audio),
                ],
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            return False

        proceso_indicador_audio = proceso

    threading.Thread(
        target=vigilar_indicador_audio,
        args=(proceso,),
        daemon=True,
    ).start()
    return True


def detener_indicador_audio() -> None:
    global proceso_indicador_audio

    with bloqueo_estado:
        proceso = proceso_indicador_audio
        proceso_indicador_audio = None

    terminar_arbol_proceso(proceso)


def sincronizar_indicador_audio() -> None:
    with bloqueo_estado:
        pantalla = procesos_multimodales.get("screen")
        seleccionando_pantalla = (
            pantalla is not None and pantalla.poll() is None
        )

    debe_mostrarse = (
        audio_habilitado
        and mostrar_indicador_audio
        and buffer_audio.is_running
        and not seleccionando_pantalla
        and not novalens_cerrando.is_set()
    )

    if debe_mostrarse:
        iniciar_indicador_audio()
    else:
        detener_indicador_audio()


# ══════════════════════════════════════════════
# ROLLING MICROPHONE BUFFER
# ══════════════════════════════════════════════

def iniciar_buffer_audio() -> bool:
    global error_buffer_audio

    if novalens_cerrando.is_set():
        return False

    if not audio_habilitado:
        error_buffer_audio = tr("audio_disabled")
        sincronizar_indicador_audio()
        return False

    with bloqueo_audio:
        if buffer_audio.is_running:
            sincronizar_indicador_audio()
            return True

        try:
            buffer_audio.start()
            error_buffer_audio = ""
            sincronizar_indicador_audio()
            return True
        except Exception as error:
            error_buffer_audio = (
                f"{tr('mic_start_error')} "
                f"{type(error).__name__}: {error}"
            )
            sincronizar_indicador_audio()
            return False


def detener_buffer_audio() -> None:
    with bloqueo_audio:
        buffer_audio.stop()
    sincronizar_indicador_audio()


def aplicar_configuracion_audio(
    config: dict | None = None,
) -> None:
    global audio_habilitado
    global duracion_buffer_audio
    global mostrar_indicador_audio
    global error_buffer_audio

    configuracion = config or cargar_configuracion()
    audio = configuracion["audio"]
    nueva_habilitacion = bool(audio["enabled"])
    nueva_duracion = int(audio["duration_seconds"])
    nuevo_indicador = bool(audio["show_indicator"])

    # The indicator also uses appearance and popup-position settings, so any
    # saved configuration change must recreate it with the latest values.
    detener_indicador_audio()
    audio_habilitado = nueva_habilitacion
    duracion_buffer_audio = nueva_duracion
    mostrar_indicador_audio = nuevo_indicador

    with bloqueo_audio:
        buffer_audio.set_duration(duracion_buffer_audio)

        if not audio_habilitado:
            buffer_audio.stop()
            error_buffer_audio = tr("audio_disabled")
        elif not buffer_audio.is_running:
            try:
                buffer_audio.start()
                error_buffer_audio = ""
            except Exception as error:
                error_buffer_audio = (
                    f"{tr('mic_start_error')} "
                    f"{type(error).__name__}: {error}"
                )

    sincronizar_indicador_audio()


def crear_archivo_audio_temporal(audio_wav: bytes) -> Path:
    ruta = (
        Path(tempfile.gettempdir())
        / f"novalens_audio_{os.getpid()}_{time.time_ns()}.wav"
    )
    ruta.write_bytes(audio_wav)

    with bloqueo_audio:
        archivos_audio_temporales.add(ruta)

    return ruta


def eliminar_archivo_audio_temporal(ruta: Path | None) -> None:
    if ruta is None:
        return

    try:
        ruta.unlink(missing_ok=True)
    except OSError:
        pass

    with bloqueo_audio:
        archivos_audio_temporales.discard(ruta)


def eliminar_todos_los_audios_temporales() -> None:
    with bloqueo_audio:
        rutas = list(archivos_audio_temporales)
        archivos_audio_temporales.clear()

    for ruta in rutas:
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass


def eliminar_audios_huerfanos() -> None:
    """Remove Nova Lens WAV files left behind by a previous crash."""
    carpeta_temp = Path(tempfile.gettempdir())
    for ruta in carpeta_temp.glob("novalens_audio_*.wav"):
        try:
            ruta.unlink(missing_ok=True)
        except OSError:
            pass


# ══════════════════════════════════════════════
# SCREEN AND AUDIO PROCESSES
# ══════════════════════════════════════════════

def vigilar_multimodal(
    modo: str,
    proceso: subprocess.Popen,
    archivo_audio: Path | None = None,
) -> None:
    proceso.wait()

    eliminar_archivo_audio_temporal(archivo_audio)

    with bloqueo_estado:
        if procesos_multimodales.get(modo) is proceso:
            procesos_multimodales.pop(modo, None)

    if modo == "screen":
        sincronizar_indicador_audio()


def abrir_multimodal(
    modo: str,
    archivo_audio: Path | None = None,
    error_audio: str = "",
) -> bool:
    if (
        novalens_cerrando.is_set()
        or modo not in {"screen", "audio"}
        or not ARCHIVO_MULTIMODAL.exists()
    ):
        eliminar_archivo_audio_temporal(archivo_audio)
        return False

    with bloqueo_estado:
        proceso_actual = procesos_multimodales.get(modo)

        if proceso_actual is not None and proceso_actual.poll() is None:
            eliminar_archivo_audio_temporal(archivo_audio)
            return False

        argumentos = [
            sys.executable,
            str(ARCHIVO_MULTIMODAL),
            modo,
        ]

        if modo == "audio":
            if error_audio:
                argumentos.extend(["--error", error_audio])
            elif archivo_audio is not None:
                argumentos.append(str(archivo_audio))
            argumentos.extend(
                ["--duration", str(duracion_buffer_audio)]
            )

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        try:
            proceso = subprocess.Popen(
                argumentos,
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            eliminar_archivo_audio_temporal(archivo_audio)
            return False

        procesos_multimodales[modo] = proceso

    threading.Thread(
        target=vigilar_multimodal,
        args=(modo, proceso, archivo_audio),
        daemon=True,
    ).start()
    return True


def abrir_selector_pantalla() -> None:
    if not abrir_multimodal("screen"):
        sincronizar_indicador_audio()


def analizar_pantalla() -> None:
    if not cargar_api_key():
        abrir_configuracion()
        return

    # Remove Nova Lens' own text popup from the screenshot before starting the
    # capture process. The popup child handles hide_now without an animation.
    ocultar_popup_para_captura()
    detener_indicador_audio()
    threading.Timer(0.15, abrir_selector_pantalla).start()


def responder_audio_anterior() -> None:
    if novalens_cerrando.is_set():
        return

    if not cargar_api_key():
        abrir_configuracion()
        return

    with bloqueo_estado:
        proceso_actual = procesos_multimodales.get("audio")
        if proceso_actual is not None and proceso_actual.poll() is None:
            return

    if not iniciar_buffer_audio():
        abrir_multimodal(
            "audio",
            error_audio=error_buffer_audio,
        )
        return

    segundos_disponibles = buffer_audio.available_seconds()

    if segundos_disponibles < 0.75:
        abrir_multimodal(
            "audio",
            error_audio=tr("audio_not_ready"),
        )
        return

    try:
        audio_wav = buffer_audio.snapshot_wav()
    except Exception as error:
        abrir_multimodal(
            "audio",
            error_audio=(
                f"{tr('audio_prepare_error')} "
                f"{type(error).__name__}: {error}"
            ),
        )
        return

    if not audio_wav:
        abrir_multimodal(
            "audio",
            error_audio=tr("audio_missing"),
        )
        return

    try:
        archivo_audio = crear_archivo_audio_temporal(audio_wav)
    except OSError as error:
        abrir_multimodal(
            "audio",
            error_audio=(
                f"{tr('audio_temp_error')} "
                f"{type(error).__name__}: {error}"
            ),
        )
        return

    abrir_multimodal("audio", archivo_audio=archivo_audio)


def detener_procesos_multimodales() -> None:
    with bloqueo_estado:
        procesos = list(procesos_multimodales.values())
        procesos_multimodales.clear()

    for proceso in procesos:
        terminar_arbol_proceso(proceso)

    eliminar_todos_los_audios_temporales()


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
                trigger_on_release=False,
            )
        except Exception:
            continue

        identificadores_atajos.append(identificador)
        usados.add(candidato)
        return


def registrar_atajos(config: dict | None = None) -> None:
    config = config or cargar_configuracion()
    atajos = config["hotkeys"]
    predeterminados = CONFIGURACION_PREDETERMINADA["hotkeys"]

    with bloqueo_atajos:
        quitar_atajos_registrados()

        usados: set[str] = set()

        # Fixed multimodal shortcuts always win. A custom shortcut that tries
        # to reuse one of these falls back to its own default instead.
        agregar_atajo_seguro(
            ATAJO_PANTALLA,
            ATAJO_PANTALLA,
            analizar_pantalla,
            usados,
        )
        agregar_atajo_seguro(
            ATAJO_AUDIO,
            ATAJO_AUDIO,
            responder_audio_anterior,
            usados,
        )

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
        config = cargar_configuracion()
        registrar_atajos(config)
        aplicar_configuracion_audio(config)
        aplicar_configuracion_burbuja(config)

        # popup.py reads the configuration when it starts. Closing it here
        # makes the next launch use the new settings and language.
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
    detener_burbuja_control()
    detener_procesos_multimodales()
    detener_indicador_audio()
    detener_buffer_audio()

    with bloqueo_estado:
        proceso_config = proceso_configuracion

    terminar_arbol_proceso(proceso_config)

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
    eliminar_audios_huerfanos()
    eliminar_todos_los_audios_temporales()

    config = cargar_configuracion()
    aplicar_configuracion_audio(config)
    aplicar_configuracion_burbuja(config)
    registrar_atajos(config)

    threading.Thread(
        target=vigilar_acciones_burbuja,
        daemon=True,
    ).start()

    threading.Thread(
        target=vigilar_cambios_configuracion,
        daemon=True,
    ).start()

    if not cargar_api_key():
        threading.Timer(0.35, abrir_configuracion).start()

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        cerrar_novalens()


if __name__ == "__main__":
    main()
