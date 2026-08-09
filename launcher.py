from __future__ import annotations

import ctypes
import os
import runpy
import subprocess
import sys
import time
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv

from runtime_control import RESTARTED_FLAG, RESTART_HELPER_FLAG


APP_NAME = "NovaLens"
CHILD_MODULES = {
    "popup.py": "popup_exe",
    "config.py": "config",
    "multimodal.py": "multimodal",
    "audio_indicator.py": "audio_indicator",
    "control_bubble.py": "control_bubble",
    "restart_prompt.py": "restart_prompt",
}


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def executable_directory() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def data_directory() -> Path:
    if not is_frozen():
        return Path(__file__).resolve().parent

    base = os.getenv("APPDATA")
    root = Path(base) if base else Path.home()
    folder = root / APP_NAME
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def load_user_environment() -> None:
    base = executable_directory()
    data = data_directory()

    candidates = [
        data / ".env",
        base / ".env",
    ]

    for path in candidates:
        if path.exists():
            load_dotenv(path, override=True)
            return


def own_command(*arguments: str) -> list[str]:
    if is_frozen():
        return [sys.executable, *arguments]

    return [
        sys.executable,
        str(Path(__file__).resolve()),
        *arguments,
    ]


def wait_for_process_exit(pid: int, timeout_seconds: float = 20.0) -> bool:
    if pid <= 0:
        return False

    if os.name == "nt":
        synchronize = 0x00100000
        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.WaitForSingleObject.restype = ctypes.c_ulong

        handle = kernel32.OpenProcess(
            synchronize,
            False,
            pid,
        )
        if not handle:
            return True

        try:
            result = kernel32.WaitForSingleObject(
                handle,
                max(0, int(timeout_seconds * 1000)),
            )
            return result == 0
        finally:
            kernel32.CloseHandle(handle)

    deadline = time.monotonic() + max(0.0, timeout_seconds)
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            pass
        time.sleep(0.10)

    return False


def launch_restarted_process() -> bool:
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
            own_command(RESTARTED_FLAG),
            cwd=str(executable_directory()),
            creationflags=creation_flags,
            start_new_session=start_new_session,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True
    except Exception:
        return False


def run_restart_helper() -> bool:
    if len(sys.argv) < 3 or sys.argv[1] != RESTART_HELPER_FLAG:
        return False

    try:
        previous_pid = int(sys.argv[2])
    except (TypeError, ValueError):
        return True

    if wait_for_process_exit(previous_pid):
        launch_restarted_process()

    return True


def configure_runtime_paths() -> None:
    if not is_frozen():
        return

    import config_manager

    folder = data_directory()
    config_manager.CARPETA_PROYECTO = folder
    config_manager.ARCHIVO_CONFIG = folder / "config.json"
    config_manager.ARCHIVO_CONFIG_TEMPORAL = (
        folder / "config.tmp.json"
    )
    config_manager.ARCHIVO_ENV = folder / ".env"
    config_manager.ARCHIVO_ENV_TEMPORAL = folder / ".env.tmp"

    def configure_windows_startup(enable: bool) -> None:
        if os.name != "nt":
            return

        import winreg

        registry_path = (
            r"Software\Microsoft\Windows\CurrentVersion\Run"
        )

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            registry_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enable:
                command = f'"{Path(sys.executable).resolve()}"'
                winreg.SetValueEx(
                    key,
                    config_manager.NOMBRE_INICIO_WINDOWS,
                    0,
                    winreg.REG_SZ,
                    command,
                )
            else:
                try:
                    winreg.DeleteValue(
                        key,
                        config_manager.NOMBRE_INICIO_WINDOWS,
                    )
                except FileNotFoundError:
                    pass

    config_manager.configurar_inicio_windows = (
        configure_windows_startup
    )


def run_child_module() -> bool:
    if not is_frozen() or len(sys.argv) < 2:
        return False

    requested_file = Path(sys.argv[1]).name.lower()
    module_name = CHILD_MODULES.get(requested_file)

    if module_name is None:
        return False

    original_arguments = sys.argv[1:]
    sys.argv = original_arguments
    runpy.run_module(
        module_name,
        run_name="__main__",
    )
    return True


def run_background() -> NoReturn:
    import main as background

    background.main()
    raise SystemExit(0)


def main() -> None:
    if run_restart_helper():
        return

    load_user_environment()
    configure_runtime_paths()

    if run_child_module():
        return

    run_background()


if __name__ == "__main__":
    main()
