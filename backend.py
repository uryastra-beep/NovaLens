from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai

from config_manager import cargar_api_key


CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"

# Source-mode fallback. In the packaged build, launcher.py loads the user's
# AppData environment before this module is imported.
load_dotenv(ARCHIVO_ENV, override=False)

MODELO = "gemini-3.6-flash"

INSTRUCCIONES_NOVA_LENS = (
    "Sos Nova Lens, un asistente que responde preguntas escritas, "
    "detectadas en capturas de pantalla o habladas en audio. "
    "Respondé en el mismo idioma de la pregunta. "
    "Da respuestas claras, directas y relativamente breves. "
    "Cuando sea un ejercicio, explicá solamente los pasos necesarios. "
    "Si falta información, indicá qué falta y no inventés datos."
)


def _obtener_api_key() -> str:
    """Read the latest BYOK key instead of caching it at import time."""

    clave = cargar_api_key().strip()
    if not clave:
        clave = os.getenv("GEMINI_API_KEY", "").strip()

    if not clave:
        raise RuntimeError(
            "No encontré una API key de Gemini. Abrí Settings y guardá una."
        )

    return clave


def _crear_cliente() -> genai.Client:
    return genai.Client(api_key=_obtener_api_key())


def _extraer_texto(respuesta: object) -> str:
    texto = getattr(respuesta, "output_text", None)

    if not texto:
        texto = getattr(respuesta, "text", None)

    return str(texto or "").strip()


def _mensaje_error(error: Exception) -> str:
    detalle = str(error)

    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in detalle:
        detalle = (
            "Google rechazó la autenticación de la API key. "
            "Verificá que la key siga activa en Google AI Studio y que esté "
            "vinculada a un proyecto con Gemini API habilitada.\n\n"
            f"Detalle original: {error}"
        )

    return (
        "No pude obtener una respuesta de Gemini.\n\n"
        f"Tipo de error: {type(error).__name__}\n"
        f"Detalle: {detalle}"
    )


def _texto_con_instrucciones(texto: str) -> str:
    return (
        f"Instrucciones de Nova Lens:\n{INSTRUCCIONES_NOVA_LENS}\n\n"
        f"Solicitud del usuario:\n{texto}"
    )


def _generar_interaccion(entrada: Any) -> str:
    """Call the current Gemini Interactions API used by auth (AQ.) keys."""

    cliente = _crear_cliente()
    respuesta = cliente.interactions.create(
        model=MODELO,
        input=entrada,
        store=False,
    )
    return _extraer_texto(respuesta)


def preguntar_a_novalens(pregunta: str) -> str:
    """Send a text question to Gemini and return only its answer."""

    pregunta = pregunta.strip()

    if not pregunta:
        return "No detecté ninguna pregunta."

    try:
        respuesta = _generar_interaccion(
            _texto_con_instrucciones(pregunta)
        )

        if not respuesta:
            return "Gemini respondió, pero no devolvió texto."

        return respuesta

    except Exception as error:
        return _mensaje_error(error)


def analizar_captura_pantalla(imagen_jpeg: bytes) -> str:
    """Detect visible questions in a JPEG screenshot and answer them."""

    if not imagen_jpeg:
        return "No pude capturar la pantalla."

    prompt = (
        "Analizá esta captura de pantalla completa. Detectá la pregunta, "
        "problema o ejercicio principal que esté visible y respondelo. "
        "Si hay varias preguntas claramente visibles, respondelas en orden. "
        "No describás toda la pantalla ni mencionés que recibiste una captura. "
        "Si no hay ninguna pregunta legible, decí exactamente: "
        "No detecté una pregunta legible en la pantalla."
    )

    try:
        texto = _generar_interaccion(
            [
                {
                    "type": "text",
                    "text": _texto_con_instrucciones(prompt),
                },
                {
                    "type": "image",
                    "data": base64.b64encode(imagen_jpeg).decode("ascii"),
                    "mime_type": "image/jpeg",
                },
            ]
        )
        return texto or "Gemini analizó la pantalla, pero no devolvió texto."

    except Exception as error:
        return _mensaje_error(error)


def transcribir_y_responder_audio(audio_wav: bytes) -> str:
    """Transcribe a WAV recording and answer the spoken question."""

    if not audio_wav:
        return "No se grabó ningún audio."

    prompt = (
        "Escuchá este audio. Primero transcribí fielmente la pregunta hablada "
        "y después respondela. Conservá el idioma original. Usá exactamente "
        "este formato:\n\n"
        "Transcripción: <texto detectado>\n\n"
        "Respuesta: <respuesta clara y directa>\n\n"
        "Si el audio no contiene una pregunta inteligible, indicalo en ambos "
        "campos sin inventar palabras."
    )

    try:
        texto = _generar_interaccion(
            [
                {
                    "type": "text",
                    "text": _texto_con_instrucciones(prompt),
                },
                {
                    "type": "audio",
                    "data": base64.b64encode(audio_wav).decode("ascii"),
                    "mime_type": "audio/wav",
                },
            ]
        )
        return texto or "Gemini procesó el audio, pero no devolvió texto."

    except Exception as error:
        return _mensaje_error(error)
