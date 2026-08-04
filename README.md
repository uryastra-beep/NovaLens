# NovaLens

**NovaLens — Powered by OpenAI**

NovaLens es un asistente de escritorio que permite analizar preguntas o problemas detectados mediante capturas de pantalla, audio y fragmentos de video.

La respuesta aparece en un popup configurable sin necesidad de cambiar de aplicación.

> NovaLens se encuentra actualmente en desarrollo.

---

## Funciones planeadas

- Analizar preguntas mediante una captura de pantalla.
- Escuchar una pregunta y convertirla a texto.
- Analizar fragmentos cortos de video.
- Obtener respuestas mediante la API de Gemini.
- Copiar rápidamente la respuesta.
- Informar sobre respuestas incorrectas o errores.
- Cambiar la posición del popup.
- Activar la captura únicamente cuando el usuario lo decida.

---

## Estado actual

Actualmente, NovaLens puede:

- Recibir una pregunta escrita desde la terminal.
- Enviarla a la API de OpenAI.
- Mostrar la respuesta generada.

Las capturas de pantalla, el audio, el video y la interfaz gráfica serán agregados durante las siguientes etapas del proyecto.

---

## Estructura del proyecto

```text
NovaLens/
├── main.py
├── requirements.txt
├── README.md
├── .env
└── .gitignore
```

> El archivo `.env` contiene información privada y nunca debe subirse a GitHub.

---

## 🗺️ Plan de desarrollo

- [x] Conexión básica con OpenAI.
- [x] Preguntas escritas desde la terminal.
- [ ] Captura de una región de la pantalla.
- [ ] Análisis de imágenes.
- [ ] Grabación y transcripción de audio.
- [ ] Popup de respuestas.
- [ ] Posiciones configurables.
- [ ] Análisis de fragmentos de video.
- [ ] Sistema para informar errores.
- [ ] Aplicación ejecutable para Windows.

---

## 🔐 Privacidad

NovaLens solamente captura la pantalla, el audio o el video cuando el usuario activa voluntariamente una función.

El proyecto no debe:

- Capturar contenido en secreto.
- Guardar grabaciones sin permiso.
- Incluir API keys dentro del código.
- Subir información privada automáticamente.

---

## ⚠️ Aviso

NovaLens puede generar respuestas incorrectas. Las respuestas importantes deben verificarse antes de utilizarlas.

---

## 📄 Licencia

La licencia del proyecto todavía no ha sido definida.

---

Made with Python and OpenAI.
