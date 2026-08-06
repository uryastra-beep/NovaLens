from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config_manager import cargar_api_key


CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"

# Source-mode fallback. In the packaged build, launcher.py loads the user's
# AppData environment before this module is imported.
load_dotenv(ARCHIVO_ENV, override=False)

# The packaged popup remains alive at zero opacity to avoid Flet's collapsed
# viewport bug. A small Win32 watcher guarantees that this invisible window
# cannot intercept mouse clicks.
if os.name == "nt" and "popup_exe" in Path(sys.argv[0]).stem.lower():
    try:
        from native_clickthrough import start_native_clickthrough_watch

        start_native_clickthrough_watch()
    except Exception:
        pass

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


def _crear_cliente(clave: str | None = None) -> genai.Client:
    return genai.Client(api_key=clave or _obtener_api_key())


def _extraer_texto(respuesta: object) -> str:
    texto = getattr(respuesta, "output_text", None)
    if not texto:
        texto = getattr(respuesta, "text", None)
    return str(texto or "").strip()


def _mensaje_error(error: Exception) -> str:
    detalle = str(error)

    if "ACCESS_TOKEN_TYPE_UNSUPPORTED" in detalle:
        detalle = (
            "Google rechazó el tipo de autenticación de esta key. "
            "Creá o copiá una Gemini API key desde Google AI Studio y volvé "
            "a guardarla en Settings.\n\n"
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


def _parece_auth_key(clave: str) -> bool:
    """New Google AI Studio authorization keys currently start with AQ."""

    return clave.lstrip().startswith("AQ.")


def _entrada_interactions_texto(texto: str) -> str:
    return _texto_con_instrucciones(texto)


def _entrada_interactions_multimodal(
    prompt: str,
    datos: bytes,
    mime_type: str,
    tipo: str,
) -> list[dict[str, str]]:
    return [
        {
            "type": "text",
            "text": _texto_con_instrucciones(prompt),
        },
        {
            "type": tipo,
            "data": base64.b64encode(datos).decode("ascii"),
            "mime_type": mime_type,
        },
    ]


def _generar_con_interactions(
    cliente: genai.Client,
    entrada: Any,
) -> str:
    respuesta = cliente.interactions.create(
        model=MODELO,
        input=entrada,
        store=False,
    )
    return _extraer_texto(respuesta)


def _generar_con_generate_content(
    cliente: genai.Client,
    contenido: Any,
) -> str:
    respuesta = cliente.models.generate_content(
        model=MODELO,
        contents=contenido,
        config=types.GenerateContentConfig(
            system_instruction=INSTRUCCIONES_NOVA_LENS,
        ),
    )
    return _extraer_texto(respuesta)


def _generar_texto(texto: str) -> str:
    """Automatically use the endpoint matching the user's key type."""

    clave = _obtener_api_key()
    cliente = _crear_cliente(clave)

    if _parece_auth_key(clave):
        primario = lambda: _generar_con_interactions(
            cliente,
            _entrada_interactions_texto(texto),
        )
        secundario = lambda: _generar_con_generate_content(cliente, texto)
    else:
        primario = lambda: _generar_con_generate_content(cliente, texto)
        secundario = lambda: _generar_con_interactions(
            cliente,
            _entrada_interactions_texto(texto),
        )

    try:
        return primario()
    except Exception as error:
        # Google is migrating between standard and authorization keys. If the
        # selected endpoint rejects only the credential type, try the other
        # official endpoint once before returning the error.
        if "ACCESS_TOKEN_TYPE_UNSUPPORTED" not in str(error):
            raise
        return secundario()


def _generar_multimodal(
    prompt: str,
    datos: bytes,
    mime_type: str,
    tipo_interactions: str,
) -> str:
    clave = _obtener_api_key()
    cliente = _crear_cliente(clave)

    contenido_generate = [
        prompt,
        types.Part.from_bytes(data=datos, mime_type=mime_type),
    ]
    contenido_interactions = _entrada_interactions_multimodal(
        prompt,
        datos,
        mime_type,
        tipo_interactions,
    )

    if _parece_auth_key(clave):
        primario = lambda: _generar_con_interactions(
            cliente,
            contenido_interactions,
        )
        secundario = lambda: _generar_con_generate_content(
            cliente,
            contenido_generate,
        )
    else:
        primario = lambda: _generar_con_generate_content(
            cliente,
            contenido_generate,
        )
        secundario = lambda: _generar_con_interactions(
            cliente,
            contenido_interactions,
        )

    try:
        return primario()
    except Exception as error:
        if "ACCESS_TOKEN_TYPE_UNSUPPORTED" not in str(error):
            raise
        return secundario()


def preguntar_a_novalens(pregunta: str) -> str:
    """Send a text question to Gemini and return only its answer."""

    pregunta = pregunta.strip()
    if not pregunta:
        return "No detecté ninguna pregunta."

    try:
        respuesta = _generar_texto(pregunta)
        return respuesta or "Gemini respondió, pero no devolvió texto."
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
        texto = _generar_multimodal(
            prompt,
            imagen_jpeg,
            "image/jpeg",
            "image",
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
        texto = _generar_multimodal(
            prompt,
            audio_wav,
            "audio/wav",
            "audio",
        )
        return texto or "Gemini procesó el audio, pero no devolvió texto."
    except Exception as error:
        return _mensaje_error(error)
