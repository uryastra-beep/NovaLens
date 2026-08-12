from __future__ import annotations

import json
import os
import time
from pathlib import Path


ACTION_OPEN_POPUP = "open_popup"
ACTION_CLOSE_POPUP = "close_popup"
ACTION_RESTART_APP = "restart_app"

BRIDGE_ACTIONS = {"open", "ask", "screen", "audio"}
BRIDGE_REQUEST_NAME = "harvis_bridge_request.json"
BRIDGE_RESPONSE_NAME = "harvis_bridge_response.json"
BRIDGE_MAX_TEXT_CHARACTERS = 20_000

RESTART_HELPER_FLAG = "--novalens-restart-after-pid"
RESTARTED_FLAG = "--novalens-restarted"


def bridge_directory() -> Path:
    base = os.getenv("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    directory = root / "NovaLens"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def bridge_request_path() -> Path:
    return bridge_directory() / BRIDGE_REQUEST_NAME


def bridge_response_path() -> Path:
    return bridge_directory() / BRIDGE_RESPONSE_NAME


def write_bridge_response(
    request_id: str,
    status: str,
    text: str = "",
) -> bool:
    identifier = str(request_id).strip()[:80]
    if not identifier:
        return False

    path = bridge_response_path()
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    payload = {
        "version": 1,
        "id": identifier,
        "status": str(status).strip()[:80] or "completed",
        "text": str(text)[:BRIDGE_MAX_TEXT_CHARACTERS],
        "created_at": time.time(),
    }
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporary, path)
        return True
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def escribir_accion_runtime(
    ruta: Path | None,
    accion: str,
) -> bool:
    """Atomically send one command to the resident Nova Lens process."""
    if ruta is None or not accion:
        return False

    temporal = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")
    datos = {
        "id": time.time_ns(),
        "action": accion,
    }

    try:
        temporal.write_text(
            json.dumps(datos, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(temporal, ruta)
        return True
    except OSError:
        try:
            temporal.unlink(missing_ok=True)
        except OSError:
            pass
        return False
