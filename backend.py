from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


CARPETA_PROYECTO = Path(__file__).resolve().parent
ARCHIVO_ENV = CARPETA_PROYECTO / ".env"

# Cargar específicamente el .env ubicado junto al código
load_dotenv(ARCHIVO_ENV)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "No encontré GEMINI_API_KEY dentro del archivo .env."
    )


MODELO = "gemini-3.5-flash"

INSTRUCCIONES_NOVALENS = (
    "Sos NovaLens, un asistente que responde preguntas detectadas "
    "en capturas de pantalla, audio o video. "
    "Respondé en el mismo idioma de la pregunta. "
    "Da respuestas claras, directas y relativamente breves. "
    "Cuando sea un ejercicio, explicá solamente los pasos necesarios. "
    "Si falta información, indicá qué falta y no inventés datos."
)


client = genai.Client(api_key=API_KEY)


def preguntar_a_novalens(pregunta: str) -> str:
    """
    Envía una pregunta a Gemini y devuelve únicamente la respuesta.
    """

    pregunta = pregunta.strip()

    if not pregunta:
        return "No detecté ninguna pregunta."

    try:
        interaction = client.interactions.create(
            model=MODELO,
            system_instruction=INSTRUCCIONES_NOVALENS,
            input=pregunta,
        )

        respuesta = (interaction.output_text or "").strip()

        if not respuesta:
            return "Gemini respondió, pero no devolvió texto."

        return respuesta

    except Exception as error:
        return (
            "No pude obtener una respuesta de Gemini.\n\n"
            f"Tipo de error: {type(error).__name__}\n"
            f"Detalle: {error}"
        )