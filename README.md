# Nova Lens

**Nova Lens — Powered by Google Gemini**

Nova Lens is a Windows desktop assistant that lets you ask an AI questions from any application through a floating popup.

The app runs in the background, can be opened with global hotkeys, can detect questions visible on the screen, and can transcribe and answer recent spoken questions.

> Nova Lens is currently in **Beta**.

---

## Project Status

- **Latest public release:** `v0.2.0-beta`
- **Development branch:** includes experimental screen and rolling-audio support
- **Supported platform:** Windows
- **Language:** Python
- **Interface:** Flet
- **AI provider:** Google Gemini

Nova Lens is currently distributed as source code and is intended mainly for developers, collaborators, and early testers.

---

## Available Features

- Persistent background execution.
- Always-on-top floating popup.
- Google Gemini integration.
- Questions written directly inside the popup.
- Follow-up questions.
- Basic context between consecutive questions.
- Full-screen question detection.
- Automatic screenshot analysis with Gemini.
- Rolling 10-second microphone buffer stored in memory.
- Audio transcription followed by an automatic answer.
- Global hotkeys.
- Entry and fade-out animations.
- Automatic hiding after inactivity.
- Timer reset when typing, clicking, or scrolling.
- Automatic click-through when the text popup loses focus.
- Button to copy responses.
- Dynamic height based on response length.
- Internal scrolling for long responses.
- Prevention of multiple Nova Lens instances.
- Background execution without a console through `pythonw.exe`.
- Graphical settings interface.
- Persistent settings through `config.json`.
- Customizable colors and transparency.
- Configurable font size, border radius, margin, and popup position.
- Configurable auto-hide timer.
- Customizable text-popup hotkeys.
- Optional startup with Windows.

---

## Default Hotkeys

| Action | Hotkey |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Nova Lens settings | `P + Shift + Enter` |
| Analyze the visible screen | `P + Shift + S` |
| Transcribe and answer the previous 10 seconds of audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` |
| Completely close Nova Lens | `P + Delete` |

The text-popup, settings, and close hotkeys can be changed from the settings interface.

The screen and audio hotkeys are currently fixed while the multimodal system is still experimental.

---

## How It Works

### Text questions

When `P + Enter` is pressed:

1. The floating popup appears.
2. The user writes a question.
3. Nova Lens sends the request to Google Gemini.
4. The answer appears inside the same popup.
5. The user can ask follow-up questions.
6. After the configured inactivity period, the popup fades out.

### Screen question detection

When `P + Shift + S` is pressed:

1. Nova Lens captures the full visible desktop, including connected displays.
2. The screenshot is sent directly to Gemini.
3. Gemini detects the main visible question, problem, or exercise.
4. Nova Lens displays the answer in a temporary popup.

The screenshot is captured before the response popup appears, so the Nova Lens window is not included in the image.

### Recent spoken questions

While Nova Lens is running, it continuously keeps only the latest 10 seconds of microphone audio in a circular memory buffer.

When `P + Shift + A` is pressed:

1. Nova Lens takes a snapshot of the previous 10 seconds from the in-memory buffer.
2. The audio is prepared as a temporary WAV file.
3. Gemini transcribes the spoken question.
4. Gemini answers the transcribed question.
5. Nova Lens displays both the transcription and the answer.
6. The temporary WAV file is deleted immediately after it is read or when the process closes.

Older audio is continuously overwritten and is never sent to Gemini unless the audio hotkey is pressed.

---

## Settings Interface

Open the graphical settings window with:

```text
P + Shift + Enter
```

The settings interface currently allows you to change:

- Primary popup color.
- Text color.
- Secondary text color.
- Border color.
- Transparency.
- Font size.
- Border radius.
- Screen margin.
- Popup position.
- Auto-hide time.
- Click-through behavior.
- Text-popup and close hotkeys.
- Startup with Windows.

Settings are stored locally in `config.json`.

---

## Project Structure

```text
NovaLens/
├── backend.py
├── config.py
├── config_manager.py
├── main.py
├── multimodal.py
├── popup.py
├── rolling_audio.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
├── config.json
└── .venv/
```

### Main Files

- `main.py`: keeps Nova Lens running, manages hotkeys, maintains the rolling audio buffer, and launches child processes.
- `popup.py`: contains the persistent text popup, animations, timer, and click-through behavior.
- `multimodal.py`: captures the screen, reads recent buffered audio, and displays multimodal responses.
- `rolling_audio.py`: keeps only the latest microphone audio in a circular in-memory buffer.
- `backend.py`: manages text, screenshot, and audio requests sent to Google Gemini.
- `config.py`: contains the graphical settings interface.
- `config_manager.py`: loads, validates, saves, and restores Nova Lens settings.
- `requirements.txt`: contains the project dependencies.
- `.env`: stores the Google Gemini API key locally.
- `config.json`: stores local user preferences.
- `.gitignore`: prevents private, temporary, and local files from being uploaded.

> The `.env` file contains private information and must never be uploaded to GitHub.

---

## Installation for Developers

Nova Lens Beta is currently distributed as source code and does not yet include an official installer or `.exe` file.

### 1. Clone the repository

```powershell
git clone https://github.com/uryastra-beep/NovaLens.git
cd NovaLens
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install or update the dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## Configure Google Gemini

Every person running Nova Lens from source code must use their own Google Gemini API key.

Create a file named `.env` in the project folder:

```env
GEMINI_API_KEY=YOUR_OWN_API_KEY
```

Do not add quotation marks around the API key.

The `.env` file is excluded from the repository through `.gitignore` and must never be published.

---

## Run Nova Lens from Source

### Development mode

```powershell
python main.py
```

### Background mode

```powershell
.\.venv\Scripts\pythonw.exe main.py
```

---

## Dependencies

```text
google-genai
python-dotenv
flet
keyboard
Pillow
numpy
sounddevice
```

---

## Privacy

Nova Lens uses the microphone while the app is running so it can recover a question that was spoken immediately before the audio hotkey was pressed.

- Only the latest 10 seconds are kept in a circular RAM buffer.
- Older microphone audio is continuously overwritten.
- The rolling buffer is not intentionally written to disk.
- Audio is not sent to Gemini until `P + Shift + A` is pressed.
- After the hotkey is pressed, Nova Lens creates a temporary WAV file for the child process and deletes it immediately after reading it or when the process closes.
- `P + Shift + S` captures the full visible desktop and sends the screenshot to Google Gemini.
- Closing Nova Lens stops the microphone stream and clears the in-memory audio buffer.
- API keys must never be included directly in the source code or shared in bug reports.

Do not run Nova Lens around private conversations unless everyone present understands that the microphone buffer is active.

---

## Beta Limitations

- Nova Lens currently only supports Windows.
- Screen detection captures the complete desktop instead of a selected region.
- The screen and audio hotkeys are not configurable yet.
- The rolling audio duration is currently fixed at 10 seconds.
- The selected default microphone must work correctly in Windows.
- Nova Lens currently has no tray indicator showing that the microphone buffer is active.
- Video analysis has not been implemented yet.
- The error-reporting button does not submit reports yet.
- There is no official installer or executable yet.
- AI-generated answers and transcriptions may contain errors.

---

## Development Roadmap

- [x] Google Gemini integration.
- [x] Floating text popup.
- [x] Follow-up questions.
- [x] Basic context between questions.
- [x] Entry and fade-out animations.
- [x] Automatic hiding.
- [x] Stable click-through behavior.
- [x] Global hotkeys.
- [x] Background execution.
- [x] Prevention of multiple instances.
- [x] Graphical settings interface.
- [x] Customizable text-popup hotkeys.
- [x] Color, transparency, font, and position settings.
- [x] Optional startup with Windows.
- [x] Full-screen question detection.
- [x] Screenshot analysis and automatic answers.
- [x] Rolling 10-second microphone buffer.
- [x] Audio transcription and automatic answers.
- [ ] Microphone activity indicator.
- [ ] Option to enable or disable the rolling audio buffer.
- [ ] Configurable rolling-audio duration.
- [ ] Configurable screen and audio hotkeys.
- [ ] Screen region selection.
- [ ] Compact and normal display modes.
- [ ] Short video analysis.
- [ ] Error-reporting system and Discord integration.
- [ ] Windows `.exe` build.
- [ ] Windows installer.
- [ ] Native Linux version.

---

## Current Release

The latest public beta release is:

```text
v0.2.0-beta
```

The multimodal screen and rolling-audio features are currently available on the development branch and should be tested before the next public beta release.

---

## Contributions and Support

Suggestions, bug reports, and contributions are welcome.

For bug reports, technical support, community discussions, and project updates, join the official Nova Lens Discord server:

https://discord.gg/Dfns48WEqH

---

## Disclaimer

Nova Lens may generate incorrect, incomplete, or outdated responses.

Important information should always be verified before use.

Nova Lens is not intended to replace medical, legal, financial, or other professional advice.

---

## License

A project license has not been selected yet.

---

Made with Python, Flet, and Google Gemini.

**Join our Discord for more information:** https://discord.gg/Dfns48WEqH
