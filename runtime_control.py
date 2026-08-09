from __future__ import annotations

import json
import os
import time
from pathlib import Path


ACTION_OPEN_POPUP = "open_popup"
ACTION_CLOSE_POPUP = "close_popup"
ACTION_RESTART_APP = "restart_app"

RESTART_HELPER_FLAG = "--novalens-restart-after-pid"
RESTARTED_FLAG = "--novalens-restarted"


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
