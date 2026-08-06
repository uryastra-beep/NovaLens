from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv


APP_NAME = "NovaLens"
CHILD_MODULES = {
    "popup.py": "popup_exe",
    "config.py": "config",
    "multimodal.py": "multimodal",
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

    # The packaged popup keeps its native window alive at zero opacity to
    # avoid the old collapsed-window bug. Start the Win32 watcher inside the
    # popup child process so that the invisible window becomes click-through.
    if requested_file == "popup.py":
        try:
            from native_clickthrough import start_native_clickthrough_watch

            start_native_clickthrough_watch()
        except Exception:
            # Flet's own ignore_mouse_events remains as a fallback.
            pass

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
    load_user_environment()
    configure_runtime_paths()

    if run_child_module():
        return

    run_background()


if __name__ == "__main__":
    main()
