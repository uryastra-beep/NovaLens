from __future__ import annotations

from config_manager import cargar_configuracion


TRANSLATIONS: dict[str, dict[str, str]] = {
    "english": {
        "popup_ready": "Nova Lens is ready. Type a question in the field below.",
        "popup_hint": "Type another question…",
        "copy": "Copy",
        "copied": "Copied",
        "copy_done": "Response copied.",
        "copy_failed": "I could not copy the response.",
        "report_error": "Report error",
        "report_opened": "Nova Lens Discord opened in your browser.",
        "report_open_failed": "I could not open the Nova Lens Discord invitation.",
        "done": "Done",
        "wait_response": "Wait for the response to finish.",
        "write_first": "Type a question first.",
        "analyzing": "Analyzing…",
        "response_ready": "Response ready.",
        "error_occurred": "An error occurred.",
        "no_text": "Gemini returned no text.",
        "powered_by": "Powered by Google Gemini",
        "mic_start_error": "I could not start the default Windows microphone.",
        "mic_indicator": "Mic · {seconds}s",
        "audio_disabled": "Recent-audio capture is disabled in Nova Lens Settings.",
        "audio_not_ready": "Nova Lens does not have enough recent audio yet. Wait a second and try the shortcut again.",
        "audio_prepare_error": "I could not prepare the recent audio.",
        "audio_missing": "I could not find recent microphone audio to analyze.",
        "audio_temp_error": "I could not prepare the temporary audio file.",
        "preparing": "Preparing…",
        "screen_audio": "Screen & Audio",
        "select_screen_region": "Drag to select the screen region Nova Lens should analyze",
        "select_screen_cancel": "Press Esc or right-click to cancel",
        "detecting_screen": "Detecting the question inside the selected region…",
        "analyzing_screen": "Analyzing selected region…",
        "analyzing_audio": "Analyzing the previous {seconds} seconds of microphone audio…",
        "processing_audio": "Processing recent audio…",
        "request_failed": "I could not complete the request.",
        "bubble_open": "Open",
        "bubble_close": "Close",
    },
    "spanish": {
        "popup_ready": "Nova Lens está listo. Escribí una pregunta en el campo inferior.",
        "popup_hint": "Escribí otra pregunta…",
        "copy": "Copiar",
        "copied": "Copiado",
        "copy_done": "Respuesta copiada.",
        "copy_failed": "No pude copiar la respuesta.",
        "report_error": "Informar error",
        "report_opened": "Abrí el Discord de Nova Lens en tu navegador.",
        "report_open_failed": "No pude abrir la invitación de Discord de Nova Lens.",
        "done": "Listo",
        "wait_response": "Esperá a que termine la respuesta.",
        "write_first": "Escribí una pregunta primero.",
        "analyzing": "Analizando…",
        "response_ready": "Respuesta lista.",
        "error_occurred": "Ocurrió un error.",
        "no_text": "Gemini no devolvió ningún texto.",
        "powered_by": "Impulsado por Google Gemini",
        "mic_start_error": "No pude iniciar el micrófono predeterminado de Windows.",
        "mic_indicator": "Mic · {seconds}s",
        "audio_disabled": "La captura de audio reciente está desactivada en la configuración de Nova Lens.",
        "audio_not_ready": "Nova Lens todavía no tiene suficiente audio reciente. Esperá un segundo y probá el atajo nuevamente.",
        "audio_prepare_error": "No pude preparar los últimos segundos de audio.",
        "audio_missing": "No encontré audio reciente del micrófono para analizar.",
        "audio_temp_error": "No pude preparar el archivo temporal de audio.",
        "preparing": "Preparando…",
        "screen_audio": "Pantalla y audio",
        "select_screen_region": "Arrastrá para seleccionar la región que Nova Lens debe analizar",
        "select_screen_cancel": "Presioná Esc o hacé clic derecho para cancelar",
        "detecting_screen": "Detectando la pregunta dentro de la región seleccionada…",
        "analyzing_screen": "Analizando la región seleccionada…",
        "analyzing_audio": "Analizando los últimos {seconds} segundos del micrófono…",
        "processing_audio": "Procesando audio reciente…",
        "request_failed": "No pude completar la solicitud.",
        "bubble_open": "Abrir",
        "bubble_close": "Cerrar",
    },
}


def get_language() -> str:
    try:
        language = (
            cargar_configuracion()
            .get("system", {})
            .get("language", "english")
        )
    except Exception:
        language = "english"

    return language if language in TRANSLATIONS else "english"


def tr(key: str, language: str | None = None) -> str:
    selected = language or get_language()
    if selected not in TRANSLATIONS:
        selected = "english"
    return TRANSLATIONS[selected].get(key, TRANSLATIONS["english"].get(key, key))
