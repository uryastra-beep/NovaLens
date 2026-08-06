from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"

# Load the .env file located next to the source code.
load_dotenv(ARCHIVO_ENV)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "No encontré GEMINI_API_KEY dentro del archivo .env."
    )


MODELO = "gemini-3.5-flash"

INSTRUCCIONES_NOVA_LENS = (
    "Sos Nova Lens, un asistente que responde preguntas escritas, "
    "detectadas en capturas de pantalla o habladas en audio. "
    "Respondé en el mismo idioma de la pregunta. "
    "Da respuestas claras, directas y relativamente breves. "
    "Cuando sea un ejercicio, explicá solamente los pasos necesarios. "
    "Si falta información, indicá qué falta y no inventés datos."
)


client = genai.Client(api_key=API_KEY)
CONFIGURACION_GENERACION = types.GenerateContentConfig(
    system_instruction=INSTRUCCIONES_NOVA_LENS,
)


def _extraer_texto(respuesta: object) -> str:
    texto = getattr(respuesta, "text", None)

    if not texto:
        texto = getattr(respuesta, "output_text", None)

    return str(texto or "").strip()


def _mensaje_error(error: Exception) -> str:
    return (
        "No pude obtener una respuesta de Gemini.\n\n"
        f"Tipo de error: {type(error).__name__}\n"
        f"Detalle: {error}"
    )


def _generar_contenido(contenido: Any) -> str:
    respuesta = client.models.generate_content(
        model=MODELO,
        contents=contenido,
        config=CONFIGURACION_GENERACION,
    )
    return _extraer_texto(respuesta)


def preguntar_a_novalens(pregunta: str) -> str:
    """Send a text question to Gemini and return only its answer."""

    pregunta = pregunta.strip()

    if not pregunta:
        return "No detecté ninguna pregunta."

    try:
        respuesta = _generar_contenido(pregunta)

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
        texto = _generar_contenido(
            [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(
                    data=imagen_jpeg,
                    mime_type="image/jpeg",
                ),
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
        texto = _generar_contenido(
            [
                types.Part.from_text(text=prompt),
                types.Part.from_bytes(
                    data=audio_wav,
                    mime_type="audio/wav",
                ),
            ]
        )
        return texto or "Gemini procesó el audio, pero no devolvió texto."

    except Exception as error:
        return _mensaje_error(error)
