from __future__ import annotations

import base64
import hashlib
import json
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
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1/interactions"
REQUEST_TIMEOUT_SECONDS = 60.0

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
            "Google rejected this Gemini credential before Nova Lens could complete "
            "the request. Verify the key and its Google AI Studio project, then save "
            "the key again in Settings."
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
            "Google rechazó esta credencial de Gemini antes de que Nova Lens pudiera "
            "completar la solicitud. Verificá la key y su proyecto de Google AI Studio "
            "y guardala nuevamente en Configuración."
        ),
        "generic_error": "Nova Lens no pudo obtener una respuesta de Gemini.",
    },
}


class NovaLensBackendError(RuntimeError):
    """User-displayable backend failure that should not enter chat history."""


class GeminiAuthenticationError(RuntimeError):
    pass


class RestInteractionError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"REST HTTP {status_code}: {detail}")


def _idioma() -> str:
    idioma = cargar_configuracion().get("system", {}).get("language", "english")
    return idioma if idioma in TEXTOS else "english"


def _t(clave: str) -> str:
    return TEXTOS[_idioma()][clave]


def _obtener_api_key() -> str:
    clave = cargar_api_key().strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not clave:
        raise NovaLensBackendError(_t("no_key"))
    return clave


def _diagnostico_key(clave: str) -> str:
    prefijo = "AQ." if clave.startswith("AQ.") else "AIza" if clave.startswith("AIza") else clave[:3]
    huella = hashlib.sha256(clave.encode("utf-8")).hexdigest()[:10]
    return f"key_type={prefijo or 'unknown'}, length={len(clave)}, fingerprint={huella}"


def _extraer_texto(respuesta: object) -> str:
    texto = getattr(respuesta, "output_text", None) or getattr(respuesta, "text", None)
    return str(texto or "").strip()


def _extraer_texto_rest(datos: Any) -> str:
    if not isinstance(datos, dict):
        return ""

    # output_text is SDK sugar, but accepting it makes this parser tolerant of
    # proxy/test responses. The official REST schema uses model_output steps.
    directo = datos.get("output_text")
    if isinstance(directo, str) and directo.strip():
        return directo.strip()

    textos: list[str] = []
    pasos = datos.get("steps")
    if isinstance(pasos, list):
        for paso in pasos:
            if not isinstance(paso, dict) or paso.get("type") != "model_output":
                continue
            contenido = paso.get("content")
            if not isinstance(contenido, list):
                continue
            for bloque in contenido:
                if not isinstance(bloque, dict) or bloque.get("type") != "text":
                    continue
                texto = bloque.get("text")
                if isinstance(texto, str) and texto.strip():
                    textos.append(texto.strip())

    return "\n".join(textos).strip()


def _es_error_tipo_credencial(error: Exception | str) -> bool:
    detalle = str(error).upper()
    return any(
        marcador in detalle
        for marcador in (
            "ACCESS_TOKEN_TYPE_UNSUPPORTED",
            "UNAUTHENTICATED",
            "HTTP 401",
            "401 UNAUTHORIZED",
            "API KEY NOT VALID",
            "API_KEY_INVALID",
        )
    )


def _detalle_respuesta_http(respuesta: httpx.Response) -> str:
    try:
        cuerpo: Any = respuesta.json()
        detalle = json.dumps(cuerpo, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        detalle = respuesta.text.strip()

    if not detalle:
        detalle = respuesta.reason_phrase or "No response body"

    return detalle[:6000]


def _crear_interaccion_sdk(entrada: Any) -> str:
    clave = _obtener_api_key()
    cliente = genai.Client(
        api_key=clave,
        http_options={"api_version": "v1"},
    )
    respuesta = cliente.interactions.create(
        model=MODELO,
        input=entrada,
        system_instruction=_t("instructions"),
        store=False,
    )
    return _extraer_texto(respuesta)


def _crear_interaccion_rest(entrada: Any) -> str:
    clave = _obtener_api_key()
    respuesta = httpx.post(
        INTERACTIONS_URL,
        headers={
            "x-goog-api-key": clave,
            "Content-Type": "application/json",
        },
        json={
            "model": MODELO,
            "input": entrada,
            "system_instruction": _t("instructions"),
            "store": False,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if respuesta.is_error:
        raise RestInteractionError(
            respuesta.status_code,
            _detalle_respuesta_http(respuesta),
        )

    try:
        datos = respuesta.json()
    except ValueError as error:
        raise RuntimeError("Gemini REST returned a non-JSON success response.") from error

    return _extraer_texto_rest(datos)


def _generar_interaccion(entrada: Any) -> str:
    try:
        return _crear_interaccion_sdk(entrada)
    except Exception as error_sdk:
        # Do not duplicate quota, timeout, or server failures through another
        # endpoint. REST is used only as an independent authentication check.
        if not _es_error_tipo_credencial(error_sdk):
            raise

        try:
            return _crear_interaccion_rest(entrada)
        except Exception as error_rest:
            if _es_error_tipo_credencial(error_rest):
                clave = _obtener_api_key()
                raise GeminiAuthenticationError(
                    "Gemini Interactions v1 rejected the credential through both "
                    f"the SDK and direct REST. {_diagnostico_key(clave)}. "
                    f"SDK detail: {error_sdk}; REST detail: {error_rest}"
                ) from error_rest

            raise RuntimeError(
                "The SDK rejected authentication, but the independent REST check "
                f"failed for a different reason. SDK detail: {error_sdk}; "
                f"REST detail: {error_rest}"
            ) from error_rest


def _ejecutar_interaccion(entrada: Any) -> str:
    try:
        respuesta = _generar_interaccion(entrada)
        return respuesta or _t("empty")
    except NovaLensBackendError:
        raise
    except GeminiAuthenticationError as error:
        raise NovaLensBackendError(
            f"{_t('auth_error')}\n\nTechnical detail: {error}"
        ) from error
    except Exception as error:
        raise NovaLensBackendError(
            f"{_t('generic_error')}\n\n{type(error).__name__}: {error}"
        ) from error


def preguntar_a_novalens(pregunta: str) -> str:
    pregunta = pregunta.strip()
    if not pregunta:
        return _t("no_question")
    return _ejecutar_interaccion(pregunta)


def _entrada_multimodal(
    prompt: str,
    datos: bytes,
    mime_type: str,
    tipo: str,
) -> list[dict[str, str]]:
    return [
        {"type": "text", "text": prompt},
        {
            "type": tipo,
            "data": base64.b64encode(datos).decode("ascii"),
            "mime_type": mime_type,
        },
    ]


def analizar_captura_pantalla(imagen_jpeg: bytes) -> str:
    if not imagen_jpeg:
        return (
            "No screenshot data was captured."
            if _idioma() == "english"
            else "No se capturaron datos de pantalla."
        )

    prompt = (
        "Analyze the entire screenshot. Detect and answer the main visible "
        "question, problem, or exercise. If several questions are clearly "
        "visible, answer them in order. Do not describe the whole screen."
    )
    return _ejecutar_interaccion(
        _entrada_multimodal(prompt, imagen_jpeg, "image/jpeg", "image")
    )


def transcribir_y_responder_audio(audio_wav: bytes) -> str:
    if not audio_wav:
        return (
            "No audio was recorded."
            if _idioma() == "english"
            else "No se grabó ningún audio."
        )

    prompt = (
        "Listen to this audio. Transcribe the spoken question and answer it. "
        "Keep the original language. Format the response as: Transcription: "
        "<text> followed by Answer: <clear answer>."
    )
    return _ejecutar_interaccion(
        _entrada_multimodal(prompt, audio_wav, "audio/wav", "audio")
    )
