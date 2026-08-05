# NovaLens

**NovaLens — Powered by Google Gemini**

NovaLens es un asistente de escritorio para Windows que permite hacer preguntas a una inteligencia artificial desde cualquier aplicación mediante un popup flotante.

La aplicación permanece ejecutándose en segundo plano, puede abrirse mediante un atajo global y permite continuar usando la ventana ubicada detrás gracias al modo click-through.

> NovaLens se encuentra actualmente en fase **Beta**.

---

## Estado del proyecto

- **Versión:** `v0.1.0-beta`
- **Sistema compatible:** Windows
- **Lenguaje:** Python
- **Interfaz:** Flet
- **Proveedor de IA:** Google Gemini

Esta versión se distribuye como código fuente y está dirigida principalmente a desarrolladores, colaboradores y personas que quieran probar el proyecto.

---

## Funciones disponibles

- Ejecución permanente en segundo plano.
- Popup flotante siempre encima de otras aplicaciones.
- Integración con Google Gemini.
- Preguntas escritas directamente desde el popup.
- Preguntas de seguimiento.
- Contexto básico entre preguntas consecutivas.
- Atajos globales.
- Animación de entrada desde la parte superior.
- Animación de salida mediante fade out.
- Cierre automático después de 10 segundos sin interacción.
- Reinicio del temporizador al escribir, hacer clic o desplazarse.
- Click-through automático cuando el popup pierde el foco.
- Botón para copiar respuestas.
- Botón para ocultar el popup.
- Altura dinámica según el tamaño de la respuesta.
- Scroll interno para respuestas largas.
- Prevención de múltiples instancias.
- Ejecución sin consola mediante `pythonw.exe`.

---

## Atajos actuales

| Acción | Atajo |
|---|---|
| Abrir o reactivar NovaLens | `P + Enter` |
| Cerrar NovaLens completamente | `P + Backspace` |
| Cerrar NovaLens completamente | `P + Delete` |

Los atajos serán personalizables desde una futura interfaz de configuración.

---

## Funcionamiento

Al ejecutar NovaLens, la aplicación permanece en segundo plano esperando una combinación de teclas.

Cuando se presiona `P + Enter`:

1. El popup aparece desde la parte superior.
2. El usuario escribe una pregunta.
3. NovaLens envía la solicitud a Google Gemini.
4. La respuesta aparece dentro del mismo popup.
5. El usuario puede realizar preguntas de seguimiento.
6. Después de 10 segundos sin interacción, el popup desaparece.

Cuando el popup pierde el foco, activa automáticamente el modo click-through.

Esto permite hacer clic y trabajar normalmente en la aplicación ubicada detrás del popup, aunque NovaLens continúe visible.

Para volver a interactuar con NovaLens se presiona nuevamente `P + Enter`.

---

## Apariencia actual

El diseño predeterminado incluye:

- Fondo café semitransparente.
- Color principal: `#522E18`.
- Transparencia aproximada del `60 %`.
- Texto en tonos crema.
- Bordes redondeados.
- Posición en la parte superior de la pantalla.
- Margen respecto a los bordes del monitor.
- Altura dinámica.
- Altura máxima aproximada de 10 cm.
- Animación de entrada tipo cortina.
- Animación de salida mediante fade out.

En futuras versiones será posible cambiar estos valores desde una interfaz de configuración.

---

## Estructura del proyecto

```text
NovaLens/
├── backend.py
├── main.py
├── popup.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
└── .venv/
```

### Archivos principales

- `main.py`: mantiene NovaLens activo en segundo plano y controla los atajos globales.
- `popup.py`: contiene la interfaz flotante, las animaciones, el temporizador y el modo click-through.
- `backend.py`: administra la conexión con Google Gemini.
- `requirements.txt`: contiene las dependencias necesarias.
- `.env`: almacena localmente la API key de Google Gemini.
- `.gitignore`: evita subir archivos privados, temporales y entornos virtuales.

> El archivo `.env` contiene información privada y nunca debe subirse a GitHub.

---

## Instalación para desarrolladores

Actualmente, NovaLens Beta se distribuye como código fuente y todavía no cuenta con un instalador o archivo `.exe`.

Estas instrucciones están dirigidas a desarrolladores o personas que quieran probar, estudiar o colaborar con el proyecto.

### 1. Clonar el repositorio

```powershell
git clone https://github.com/uryastra-beep/NovaLens.git
cd NovaLens
```

### 2. Crear un entorno virtual

```powershell
python -m venv .venv
```

### 3. Activar el entorno virtual

En PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Instalar las dependencias

```powershell
python -m pip install -r requirements.txt
```

---

## Configurar Google Gemini

Por razones de seguridad, NovaLens no incluye la API key utilizada por el desarrollador.

Cada persona que ejecute el proyecto desde el código fuente debe utilizar su propia API key de Google Gemini.

Creá un archivo llamado `.env` dentro de la carpeta principal:

```env
GEMINI_API_KEY=TU_PROPIA_API_KEY
```

No agregues comillas alrededor de la API key.

El archivo `.env` está excluido del repositorio mediante `.gitignore` y nunca debe publicarse.

---

## Ejecutar NovaLens desde el código fuente

### Modo de desarrollo

```powershell
python main.py
```

La terminal permanecerá abierta mientras NovaLens esté funcionando.

### Modo en segundo plano

```powershell
.\.venv\Scripts\pythonw.exe main.py
```

En este modo NovaLens se ejecutará sin mostrar una terminal.

Para abrir o reactivar el popup:

```text
P + Enter
```

Para cerrar NovaLens completamente:

```text
P + Backspace
```

o:

```text
P + Delete
```

---

## Dependencias

```text
google-genai
python-dotenv
flet
keyboard
```

---

## Privacidad

NovaLens únicamente procesa información enviada voluntariamente por el usuario.

El proyecto no debe:

- Capturar la pantalla sin autorización.
- Escuchar el micrófono sin autorización.
- Grabar video en secreto.
- Guardar grabaciones sin permiso.
- Incluir API keys dentro del código.
- Subir información privada automáticamente.
- Ejecutar funciones ocultas sin indicación del usuario.

Las futuras funciones de pantalla, audio y video deberán activarse mediante acciones o atajos explícitos.

---

## Limitaciones de la versión Beta

- Actualmente solo funciona en Windows.
- Los atajos todavía están definidos directamente en el código.
- La interfaz de configuración aún no está disponible.
- La captura de pantalla todavía no está implementada.
- El análisis de imágenes todavía no está implementado.
- La grabación y transcripción de audio todavía no están implementadas.
- El análisis de video todavía no está implementado.
- El botón para informar errores todavía no envía reportes.
- No existe todavía un instalador o ejecutable oficial.
- Cada desarrollador debe utilizar su propia API key.
- Las respuestas generadas por la IA pueden contener errores.

---

## Plan de desarrollo

- [x] Conexión con Google Gemini.
- [x] Popup flotante.
- [x] Preguntas desde el popup.
- [x] Preguntas de seguimiento.
- [x] Contexto básico entre preguntas.
- [x] Animación de entrada.
- [x] Fade out.
- [x] Cierre automático.
- [x] Click-through.
- [x] Atajos globales.
- [x] Ejecución en segundo plano.
- [x] Prevención de múltiples instancias.
- [ ] Interfaz de configuración.
- [ ] Atajos personalizables.
- [ ] Selector de color.
- [ ] Control de transparencia.
- [ ] Fuente y tamaño configurables.
- [ ] Posiciones configurables.
- [ ] Tiempo de cierre configurable.
- [ ] Modo compacto y modo normal.
- [ ] Captura de regiones de la pantalla.
- [ ] Análisis de imágenes.
- [ ] Grabación y transcripción de audio.
- [ ] Análisis de fragmentos de video.
- [ ] Sistema para informar errores.
- [ ] Inicio automático con Windows.
- [ ] Creación de un ejecutable `.exe`.
- [ ] Instalador para Windows.

---

## Release actual

La primera versión beta pública está disponible como:

```text
v0.1.0-beta
```

Esta versión representa la primera base funcional de NovaLens.

---

## Contribuciones

NovaLens todavía se encuentra en una etapa temprana de desarrollo.

Las sugerencias, reportes de errores y contribuciones serán bienvenidas conforme avance el proyecto.

---

## Aviso

NovaLens puede generar respuestas incorrectas, incompletas o desactualizadas.

Las respuestas relacionadas con temas importantes deben verificarse antes de utilizarlas.

NovaLens no está diseñado para reemplazar asesoramiento médico, legal, financiero o profesional.

---

## Licencia

La licencia del proyecto todavía no ha sido definida.

---

Made with Python, Flet and Google Gemini.
