from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from google import genai

from config_manager import cargar_api_key, cargar_configuracion


CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"
load_dotenv(ARCHIVO_ENV, override=False)

MODELO = "gemini-3.6-flash"
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

TEXTOS = {
    "english": {
        "instructions": (
            "You are Nova Lens, an assistant that answers written questions, "
            "questions detected in screenshots, and spoken questions in audio. "
            "Reply in the same language as the user's request. Be clear, direct, "
            "and relatively brief. For exercises, explain only the necessary "
            "steps. If information is missing, say what is missing and do not invent it."
        ),
        "no_key": "No Gemini API key was found. Open Settings and save your key.",
        "no_question": "I did not detect a question.",
        "empty": "Gemini returned no text.",
        "auth_error": (
            "Google rejected this authorization key before Nova Lens could send "
            "the request. Open Google AI Studio, verify that the key is active and "
            "bound to a project with the Gemini API enabled, then save it again in Settings."
        ),
        "generic_error": "Nova Lens could not get a response from Gemini.",
    },
    "spanish": {
        "instructions": (
            "Sos Nova Lens, un asistente que responde preguntas escritas, "
            "detectadas en capturas de pantalla o habladas en audio. Respondé "
            "en el mismo idioma de la solicitud. Sé claro, directo y relativamente "
            "breve. En ejercicios, explicá solo los pasos necesarios. Si falta "
            "información, decí qué falta y no inventés datos."
        ),
        "no_key": "No encontré una API key de Gemini. Abrí Configuración y guardá tu key.",
        "no_question": "No detecté ninguna pregunta.",
        "empty": "Gemini no devolvió texto.",
        "auth_error": (
            "Google rechazó esta clave de autorización antes de que Nova Lens pudiera "
            "enviar la solicitud. Abrí Google AI Studio, verificá que la clave esté "
            "activa y vinculada a un proyecto con Gemini API habilitada, y guardala "
            "de nuevo en Configuración."
        ),
        "generic_error": "Nova Lens no pudo obtener una respuesta de Gemini.",
    },
}


def _idioma() -> str:
    idioma = cargar_configuracion().get("system", {}).get("language", "english")
    return idioma if idioma in TEXTOS else "english"


def _t(clave: str) -> str:
    return TEXTOS[_idioma()][clave]


def _obtener_api_key() -> str:
    clave = cargar_api_key().strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not clave:
        raise RuntimeError(_t("no_key"))
    return clave


def _extraer_texto(respuesta: object) -> str:
    texto = getattr(respuesta, "output_text", None) or getattr(respuesta, "text", None)
    return str(texto or "").strip()


def _texto_con_instrucciones(texto: str) -> str:
    return f"System instructions:\n{_t('instructions')}\n\nUser request:\n{texto}"


def _es_error_tipo_credencial(error: Exception | str) -> bool:
    detalle = str(error)
    return "ACCESS_TOKEN_TYPE_UNSUPPORTED" in detalle or "UNAUTHENTICATED" in detalle


def _mensaje_error(error: Exception) -> str:
    if _es_error_tipo_credencial(error):
        return f"{_t('auth_error')}\n\nTechnical detail: {error}"
    return f"{_t('generic_error')}\n\n{type(error).__name__}: {error}"


def _crear_interaccion_sdk(entrada: Any) -> str:
    cliente = genai.Client(api_key=_obtener_api_key())
    respuesta = cliente.interactions.create(
        model=MODELO,
        input=entrada,
        store=False,
    )
    return _extraer_texto(respuesta)


def _crear_interaccion_rest(entrada: Any) -> str:
    respuesta = httpx.post(
        INTERACTIONS_URL,
        headers={
            "x-goog-api-key": _obtener_api_key(),
            "Content-Type": "application/json",
        },
        json={"model": MODELO, "input": entrada, "store": False},
        timeout=60,
    )
    respuesta.raise_for_status()
    datos = respuesta.json()
    return str(datos.get("output_text") or "").strip()


def _generar_interaccion(entrada: Any) -> str:
    try:
        return _crear_interaccion_sdk(entrada)
    except Exception as error_sdk:
        try:
            return _crear_interaccion_rest(entrada)
        except Exception as error_rest:
            if _es_error_tipo_credencial(error_rest):
                raise RuntimeError(
                    "The SDK and the official Interactions REST endpoint both "
                    f"rejected the key. REST error: {error_rest}"
                ) from error_rest
            raise RuntimeError(
                f"SDK error: {error_sdk}; REST fallback error: {error_rest}"
            ) from error_rest


def preguntar_a_novalens(pregunta: str) -> str:
    pregunta = pregunta.strip()
    if not pregunta:
        return _t("no_question")

    try:
        respuesta = _generar_interaccion(_texto_con_instrucciones(pregunta))
        return respuesta or _t("empty")
    except Exception as error:
        return _mensaje_error(error)


def _entrada_multimodal(prompt: str, datos: bytes, mime_type: str, tipo: str) -> list[dict[str, str]]:
    return [
        {"type": "text", "text": _texto_con_instrucciones(prompt)},
        {
            "type": tipo,
            "data": base64.b64encode(datos).decode("ascii"),
            "mime_type": mime_type,
        },
    ]


def analizar_captura_pantalla(imagen_jpeg: bytes) -> str:
    if not imagen_jpeg:
        return "No screenshot data was captured." if _idioma() == "english" else "No se capturaron datos de pantalla."

    prompt = (
        "Analyze the entire screenshot. Detect and answer the main visible "
        "question, problem, or exercise. If several questions are clearly "
        "visible, answer them in order. Do not describe the whole screen."
    )
    try:
        texto = _generar_interaccion(
            _entrada_multimodal(prompt, imagen_jpeg, "image/jpeg", "image")
        )
        return texto or _t("empty")
    except Exception as error:
        return _mensaje_error(error)


def transcribir_y_responder_audio(audio_wav: bytes) -> str:
    if not audio_wav:
        return "No audio was recorded." if _idioma() == "english" else "No se grabó ningún audio."

    prompt = (
        "Listen to this audio. Transcribe the spoken question and answer it. "
        "Keep the original language. Format the response as: Transcription: "
        "<text> followed by Answer: <clear answer>."
    )
    try:
        texto = _generar_interaccion(
            _entrada_multimodal(prompt, audio_wav, "audio/wav", "audio")
        )
        return texto or _t("empty")
    except Exception as error:
        return _mensaje_error(error)
