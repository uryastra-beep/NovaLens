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

from bubble_layout import (
    eliminar_archivo_sesion,
    escribir_estado_desbloqueo,
)
from config_manager import (
    ARCHIVO_CONFIG,
    CONFIGURACION_PREDETERMINADA,
    cargar_api_key,
    cargar_configuracion,
)
from localization import tr
from rolling_audio import RollingAudioBuffer
from runtime_control import (
    ACTION_CLOSE_POPUP,
    ACTION_OPEN_POPUP,
    ACTION_RESTART_APP,
    RESTARTED_FLAG,
    RESTART_HELPER_FLAG,
)


# ══════════════════════════════════════════════
# PATHS
# ══════════════════════════════════════════════

CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_POPUP = CARPETA_PROYECTO / "popup.py"
ARCHIVO_CONFIG_APP = CARPETA_PROYECTO / "config.py"
ARCHIVO_MULTIMODAL = CARPETA_PROYECTO / "multimodal.py"
ARCHIVO_INDICADOR_AUDIO = CARPETA_PROYECTO / "audio_indicator.py"
ARCHIVO_BURBUJA_CONTROL = CARPETA_PROYECTO / "control_bubble.py"
ARCHIVO_AVISO_REINICIO = CARPETA_PROYECTO / "restart_prompt.py"
ARCHIVO_LANZADOR = CARPETA_PROYECTO / "launcher.py"

ARCHIVO_CONTROL = (
    Path(tempfile.gettempdir())
    / f"novalens_control_{os.getpid()}.json"
)
ARCHIVO_CONTROL_TEMPORAL = ARCHIVO_CONTROL.with_suffix(".tmp")
ARCHIVO_ACCIONES_BURBUJA = (
    Path(tempfile.gettempdir())
    / f"novalens_bubble_{os.getpid()}.json"
)
ARCHIVO_ESTADO_BURBUJAS = (
    Path(tempfile.gettempdir())
    / f"novalens_bubble_unlock_{os.getpid()}.json"
)
ARCHIVO_POSICION_AUDIO_BORRADOR = (
    Path(tempfile.gettempdir())
    / f"novalens_audio_position_{os.getpid()}.json"
)
ARCHIVO_POSICION_CONTROL_BORRADOR = (
    Path(tempfile.gettempdir())
    / f"novalens_control_position_{os.getpid()}.json"
)
ARCHIVO_SALUD_BURBUJA = (
    Path(tempfile.gettempdir())
    / f"novalens_control_bubble_health_{os.getpid()}.tmp"
)

FRECUENCIA_AUDIO = 16_000
GRACIA_INICIO_BURBUJA_SEGUNDOS = 8.0
MAX_EDAD_LATIDO_BURBUJA_SEGUNDOS = 4.0


# ══════════════════════════════════════════════
# STATE
# ══════════════════════════════════════════════

proceso_popup: subprocess.Popen | None = None
proceso_configuracion: subprocess.Popen | None = None
proceso_indicador_audio: subprocess.Popen | None = None
proceso_burbuja_control: subprocess.Popen | None = None
proceso_aviso_reinicio: subprocess.Popen | None = None
procesos_multimodales: dict[str, subprocess.Popen] = {}

bloqueo_estado = threading.Lock()
bloqueo_control = threading.Lock()
bloqueo_atajos = threading.Lock()
bloqueo_audio = threading.Lock()
bloqueo_ciclo_burbuja = threading.RLock()

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
inicio_burbuja_control = 0.0


# ══════════════════════════════════════════════
# CHILD PROCESS SHUTDOWN
# ══════════════════════════════════════════════

def archivo_hijo_disponible(ruta: Path) -> bool:
    # PyInstaller bundles hidden modules inside NovaLens.exe. The launcher
    # routes child modes by the requested basename, so a frozen build does not
    # require the original .py data file to exist beside the executable.
    return bool(getattr(sys, "frozen", False)) or ruta.exists()


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

def enviar_comando(comando: str, **extras: object) -> None:
    datos = {
        "id": time.time_ns(),
        "command": comando,
        **extras,
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

    for ruta in (
        ARCHIVO_ESTADO_BURBUJAS,
        ARCHIVO_POSICION_AUDIO_BORRADOR,
        ARCHIVO_POSICION_CONTROL_BORRADOR,
        ARCHIVO_SALUD_BURBUJA,
    ):
        eliminar_archivo_sesion(ruta)


def reiniciar_sesion_posiciones_burbujas() -> None:
    escribir_estado_desbloqueo(ARCHIVO_ESTADO_BURBUJAS, False)
    eliminar_archivo_sesion(ARCHIVO_POSICION_AUDIO_BORRADOR)
    eliminar_archivo_sesion(ARCHIVO_POSICION_CONTROL_BORRADOR)


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

    if accion == ACTION_OPEN_POPUP:
        activar_popup()
    elif accion == ACTION_CLOSE_POPUP:
        ocultar_popup_para_captura()
    elif accion == ACTION_RESTART_APP:
        reiniciar_novalens()


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
    global inicio_burbuja_control

    proceso.wait()

    with bloqueo_estado:
        if proceso_burbuja_control is proceso:
            proceso_burbuja_control = None
            inicio_burbuja_control = 0.0


def burbuja_control_saludable() -> bool:
    with bloqueo_estado:
        proceso = proceso_burbuja_control
        inicio = inicio_burbuja_control

    if proceso is None or proceso.poll() is not None:
        return False

    if time.monotonic() - inicio <= GRACIA_INICIO_BURBUJA_SEGUNDOS:
        return True

    try:
        edad = max(
            0.0,
            time.time() - ARCHIVO_SALUD_BURBUJA.stat().st_mtime,
        )
    except OSError:
        return False

    # The Flet HWND may be owned by a desktop child process. Its own event loop
    # publishes this heartbeat, so freshness plus a live supervised process is
    # the reliable health signal. Native visibility is repaired inside the
    # bubble process without destroying and recreating the entire process tree.
    return edad <= MAX_EDAD_LATIDO_BURBUJA_SEGUNDOS


def iniciar_burbuja_control() -> bool:
    global proceso_burbuja_control
    global inicio_burbuja_control

    with bloqueo_ciclo_burbuja:
        if (
            novalens_cerrando.is_set()
            or not mostrar_burbuja_control
            or not archivo_hijo_disponible(ARCHIVO_BURBUJA_CONTROL)
        ):
            return False

        with bloqueo_estado:
            proceso_actual = proceso_burbuja_control
            if proceso_actual is not None and proceso_actual.poll() is None:
                return True

            try:
                ARCHIVO_SALUD_BURBUJA.unlink(missing_ok=True)
            except OSError:
                pass

            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

            try:
                proceso = subprocess.Popen(
                    [
                        sys.executable,
                        str(ARCHIVO_BURBUJA_CONTROL),
                        str(ARCHIVO_ACCIONES_BURBUJA),
                        str(ARCHIVO_ESTADO_BURBUJAS),
                        str(ARCHIVO_POSICION_CONTROL_BORRADOR),
                        str(ARCHIVO_SALUD_BURBUJA),
                    ],
                    cwd=str(CARPETA_PROYECTO),
                    creationflags=creation_flags,
                )
            except Exception:
                return False

            proceso_burbuja_control = proceso
            inicio_burbuja_control = time.monotonic()

    threading.Thread(
        target=vigilar_burbuja_control,
        args=(proceso,),
        daemon=True,
    ).start()
    return True


def detener_burbuja_control() -> None:
    global proceso_burbuja_control
    global inicio_burbuja_control

    with bloqueo_ciclo_burbuja:
        with bloqueo_estado:
            proceso = proceso_burbuja_control
            proceso_burbuja_control = None
            inicio_burbuja_control = 0.0

        terminar_arbol_proceso(proceso, timeout=1.5)

        try:
            ARCHIVO_SALUD_BURBUJA.unlink(missing_ok=True)
        except OSError:
            pass


def aplicar_configuracion_burbuja(
    config: dict | None = None,
) -> None:
    global mostrar_burbuja_control

    configuracion = config or cargar_configuracion()
    nueva_visibilidad = bool(
        configuracion["behavior"]["show_control_bubble"]
    )

    with bloqueo_ciclo_burbuja:
        mostrar_burbuja_control = nueva_visibilidad

        # Recreate it after every saved setting so language, colors, margin,
        # and transparency are refreshed together with the interface.
        detener_burbuja_control()

        if mostrar_burbuja_control:
            iniciar_burbuja_control()


def asegurar_burbuja_control_activa() -> bool:
    if novalens_cerrando.is_set() or not mostrar_burbuja_control:
        return False

    if burbuja_control_saludable():
        return True

    with bloqueo_ciclo_burbuja:
        if burbuja_control_saludable():
            return True

        detener_burbuja_control()
        return iniciar_burbuja_control()


def vigilar_salud_burbuja_control() -> None:
    while not novalens_cerrando.wait(1.0):
        asegurar_burbuja_control_activa()


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
        or not archivo_hijo_disponible(ARCHIVO_INDICADOR_AUDIO)
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
                    str(ARCHIVO_ESTADO_BURBUJAS),
                    str(ARCHIVO_POSICION_AUDIO_BORRADOR),
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
# RECOVERY AND FULL RESTART
# ══════════════════════════════════════════════

def comando_lanzador(*argumentos: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, *argumentos]

    return [
        sys.executable,
        str(ARCHIVO_LANZADOR),
        *argumentos,
    ]


def vigilar_aviso_reinicio(proceso: subprocess.Popen) -> None:
    global proceso_aviso_reinicio

    proceso.wait()

    with bloqueo_estado:
        if proceso_aviso_reinicio is proceso:
            proceso_aviso_reinicio = None


def iniciar_aviso_reinicio() -> bool:
    global proceso_aviso_reinicio

    if (
        novalens_cerrando.is_set()
        or not archivo_hijo_disponible(ARCHIVO_AVISO_REINICIO)
    ):
        return False

    with bloqueo_estado:
        proceso_actual = proceso_aviso_reinicio
        if proceso_actual is not None and proceso_actual.poll() is None:
            return True

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_AVISO_REINICIO),
                ],
                cwd=str(CARPETA_PROYECTO),
                creationflags=creation_flags,
            )
        except Exception:
            return False

        proceso_aviso_reinicio = proceso

    threading.Thread(
        target=vigilar_aviso_reinicio,
        args=(proceso,),
        daemon=True,
    ).start()
    return True


def detener_aviso_reinicio() -> None:
    global proceso_aviso_reinicio

    with bloqueo_estado:
        proceso = proceso_aviso_reinicio
        proceso_aviso_reinicio = None

    terminar_arbol_proceso(proceso)


def reiniciar_novalens() -> bool:
    if novalens_cerrando.is_set():
        return False

    creation_flags = 0
    start_new_session = False
    if os.name == "nt":
        creation_flags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        start_new_session = True

    try:
        subprocess.Popen(
            comando_lanzador(
                RESTART_HELPER_FLAG,
                str(os.getpid()),
            ),
            cwd=str(CARPETA_PROYECTO),
            creationflags=creation_flags,
            start_new_session=start_new_session,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception:
        return False

    cerrar_novalens()
    return True


# ══════════════════════════════════════════════
# SETTINGS WINDOW
# ══════════════════════════════════════════════

def vigilar_config_app(proceso: subprocess.Popen) -> None:
    global proceso_configuracion

    proceso.wait()

    with bloqueo_estado:
        era_actual = proceso_configuracion is proceso
        if era_actual:
            proceso_configuracion = None

    if not era_actual:
        return

    reiniciar_sesion_posiciones_burbujas()

    if not novalens_cerrando.is_set():
        config = cargar_configuracion()
        aplicar_configuracion_audio(config)
        aplicar_configuracion_burbuja(config)


def abrir_configuracion() -> None:
    global proceso_configuracion

    if (
        novalens_cerrando.is_set()
        or not archivo_hijo_disponible(ARCHIVO_CONFIG_APP)
    ):
        return

    with bloqueo_estado:
        if (
            proceso_configuracion is not None
            and proceso_configuracion.poll() is None
        ):
            return

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        reiniciar_sesion_posiciones_burbujas()

        try:
            proceso = subprocess.Popen(
                [
                    sys.executable,
                    str(ARCHIVO_CONFIG_APP),
                    str(ARCHIVO_ESTADO_BURBUJAS),
                    str(ARCHIVO_POSICION_AUDIO_BORRADOR),
                    str(ARCHIVO_POSICION_CONTROL_BORRADOR),
                    str(ARCHIVO_ACCIONES_BURBUJA),
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

        agregar_atajo_seguro(
            atajos["screen"],
            predeterminados["screen"],
            analizar_pantalla,
            usados,
        )
        agregar_atajo_seguro(
            atajos["audio"],
            predeterminados["audio"],
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


def debe_abrir_configuracion_inicial(
    config: dict,
    api_key: str,
) -> bool:
    return (
        not bool((api_key or "").strip())
        or not bool(config["system"].get("onboarding_completed", False))
    )


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
    detener_aviso_reinicio()
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

    threading.Thread(
        target=vigilar_salud_burbuja_control,
        daemon=True,
    ).start()

    if debe_abrir_configuracion_inicial(config, cargar_api_key()):
        threading.Timer(0.35, abrir_configuracion).start()

    if RESTARTED_FLAG in sys.argv:
        threading.Timer(0.75, iniciar_aviso_reinicio).start()

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        cerrar_novalens()


if __name__ == "__main__":
    main()
