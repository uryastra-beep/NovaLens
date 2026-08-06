# Nova Lens

**Nova Lens — Powered by Google Gemini**

Nova Lens is a Windows desktop AI assistant that runs in the background and gives you fast access to Google Gemini from any application.

Use a floating popup for text questions, analyze the visible desktop, or ask about something spoken during the previous 10 seconds.

## Current Release

- **Version:** `v1.0.1`
- **Platform:** Windows x64
- **Download:** `NovaLens-v1.0.1-Windows-x64.zip`
- **AI provider:** Google Gemini
- **License:** No project license has been selected yet

## Download and Install

1. Open the latest release on GitHub.
2. Download `NovaLens-v1.0.1-Windows-x64.zip`.
3. Extract the entire ZIP file.
4. Keep `NovaLens.exe` and the `_internal` folder together.
5. Open `NovaLens.exe`.
6. Add your own Gemini API key in Settings and save it.

Do not run the executable directly from inside the ZIP file.

Windows may display a SmartScreen warning because Nova Lens is not currently code-signed.

## First Launch

Nova Lens uses a bring-your-own-key system. The application does not include a shared Gemini API key.

On first launch, open Settings and paste your own Google Gemini API key. Nova Lens stores it locally at:

```text
%APPDATA%\NovaLens\.env
```

User settings are stored locally at:

```text
%APPDATA%\NovaLens\config.json
```

Neither file is included in the release package or committed to this repository.

## Features

- Background execution without a visible console window.
- Always-on-top floating text popup.
- Text questions and follow-up questions.
- Short conversation context inside the popup.
- Full visible-desktop screenshot analysis.
- Rolling 10-second microphone buffer stored in memory.
- Audio transcription followed by an automatic answer.
- Entry and fade-out popup animations.
- Automatic hiding after inactivity.
- Click-through behavior after the popup loses focus.
- Dynamic popup height and scrolling for long responses.
- Copy-response button.
- Prevention of multiple Nova Lens background instances.
- Graphical Settings interface.
- Custom colors, transparency, font size, border radius, margin, and popup position.
- Configurable auto-hide timer.
- Customizable text-popup and close hotkeys.
- Optional startup with Windows.
- Local API-key and settings storage.

## Default Hotkeys

| Action | Hotkey |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Settings | `P + Shift + Enter` |
| Analyze the visible desktop | `P + Shift + S` |
| Transcribe and answer the previous 10 seconds of microphone audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` |
| Alternative close shortcut | `P + Delete` |

The text-popup, Settings, and close shortcuts can be changed from the Settings interface.

The screen and audio shortcuts are fixed in v1.0.1.

## How the Main Modes Work

### Text popup

Press `P + Enter`, write a question, and press Enter or click **Enviar**. Nova Lens sends the request to Gemini and displays the answer inside the same popup.

The popup remains alive in the background while hidden. This avoids repeated native-window recreation and improves stability in the packaged Windows build.

### Screen analysis

Press `P + Shift + S` to capture the full visible desktop across connected displays. Nova Lens sends the screenshot to Gemini and displays an answer in a temporary response window.

The current version captures the complete visible desktop. Region selection is not implemented yet.

### Recent audio

While Nova Lens is running, it keeps only the newest 10 seconds of microphone input in a circular memory buffer. Older audio is continuously overwritten.

Press `P + Shift + A` to send a snapshot of that recent audio to Gemini for transcription and an answer.

Nova Lens does not capture desktop or system audio. It uses the Windows default microphone input.

## Privacy and Security

- Your Gemini API key is stored locally in `%APPDATA%\NovaLens\.env`.
- The API key is not bundled in the executable or release ZIP.
- The rolling microphone buffer is kept in RAM.
- Older microphone audio is continuously overwritten.
- Audio is sent to Gemini only after `P + Shift + A` is pressed.
- A temporary WAV file is created only for processing and is deleted afterward.
- A screenshot is sent to Gemini only after `P + Shift + S` is pressed.
- Closing Nova Lens stops the microphone stream and clears the in-memory audio buffer.
- Never include API keys in screenshots, logs, issues, or public repositories.

Do not run Nova Lens around private conversations unless everyone present understands that the rolling microphone buffer is active.

## Known Limitations

- Windows x64 is the only packaged platform in v1.0.1.
- The application is not code-signed and has no installer yet.
- Screen analysis captures the entire visible desktop instead of a selected region.
- Screen and audio hotkeys are not configurable yet.
- The rolling-audio duration is fixed at 10 seconds.
- The selected default Windows microphone must work correctly.
- There is no tray indicator showing that the microphone buffer is active.
- The **Informar error** button does not submit reports yet.
- Video analysis is not implemented.
- AI answers and transcriptions may be incorrect.
- Gemini access depends on the user's Google project, API key status, quota, and service availability.

## Project Structure

```text
NovaLens/
├── .github/
│   └── workflows/
├── assets/
├── backend.py
├── build_exe.ps1
├── config.py
├── config_manager.py
├── launcher.py
├── main.py
├── multimodal.py
├── popup.py
├── popup_exe.py
├── rolling_audio.py
├── requirements-build.txt
├── requirements.txt
├── README.md
└── .gitignore
```

### Main Files

- `launcher.py`: packaged application entry point and AppData path configuration.
- `main.py`: background process, global hotkeys, child processes, and rolling-audio control.
- `popup.py`: source-mode text popup.
- `popup_exe.py`: packaged popup implementation with stable hiding and animations.
- `multimodal.py`: screenshot and recent-audio response windows.
- `rolling_audio.py`: circular in-memory microphone buffer.
- `backend.py`: Google Gemini text, image, and audio requests.
- `config.py`: graphical Settings interface.
- `config_manager.py`: local configuration, API-key storage, and Windows startup management.
- `build_exe.ps1`: clean Windows build, ZIP packaging, and SHA-256 checksum generation.

## Run from Source

### Requirements

- Windows
- Python 3.14 recommended for the current build workflow
- A personal Google Gemini API key

### Clone the repository

```powershell
git clone https://github.com/uryastra-beep/NovaLens.git
cd NovaLens
```

### Create and activate a virtual environment

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install --upgrade -r requirements.txt
```

### Configure Gemini for source mode

Create a `.env` file in the project directory:

```env
GEMINI_API_KEY=YOUR_OWN_API_KEY
```

Never commit or publish this file.

### Run in development mode

```powershell
python main.py
```

### Run without a console

```powershell
.\.venv\Scripts\pythonw.exe main.py
```

## Build the Windows Release

From an activated virtual environment, run:

```powershell
.\build_exe.ps1
```

The script stops old Nova Lens processes, removes previous build folders, installs current dependencies, builds the packaged application, removes local secret files, and creates:

```text
dist\NovaLens\NovaLens.exe
NovaLens-v1.0.1-Windows-x64.zip
NovaLens-v1.0.1-Windows-x64.zip.sha256
```

The ZIP must contain the complete `NovaLens` folder, including both `NovaLens.exe` and `_internal`.

## Development Roadmap

- [x] Google Gemini integration.
- [x] Floating text popup.
- [x] Follow-up questions and short context.
- [x] Stable packaged popup lifecycle.
- [x] Entry and fade-out animations.
- [x] Global hotkeys.
- [x] Background execution.
- [x] Single-instance protection.
- [x] Graphical Settings interface.
- [x] Custom appearance and text-popup hotkeys.
- [x] Optional startup with Windows.
- [x] Full-desktop screenshot analysis.
- [x] Rolling 10-second microphone buffer.
- [x] Audio transcription and automatic answers.
- [x] Windows x64 executable package.
- [ ] Microphone activity indicator.
- [ ] Enable or disable rolling audio from Settings.
- [ ] Configurable rolling-audio duration.
- [ ] Configurable screen and audio hotkeys.
- [ ] Screen region selection.
- [ ] Compact and normal display modes.
- [ ] Short video analysis.
- [ ] Error-reporting and Discord integration.
- [ ] Windows installer and code signing.
- [ ] Native Linux version.

## Support and Community

For bug reports, technical support, project updates, and community discussion, join the official Discord server:

https://discord.gg/Dfns48WEqH

GitHub issues are also available for reproducible bugs and feature requests. Do not include API keys or private information in reports.

## Disclaimer

Nova Lens may generate incorrect, incomplete, or outdated responses. Important information should always be verified.

Nova Lens is not intended to replace medical, legal, financial, or other professional advice.

## License

A project license has not been selected yet. Until a license is added, copyright law applies by default and reuse rights are not granted automatically.

---

Made with Python, Flet, and Google Gemini.
