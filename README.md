# Nova Lens

**Nova Lens — Powered by Google Gemini**

Nova Lens is a Windows desktop AI assistant that runs in the background and gives you fast access to Google Gemini from any application.

Use a floating popup for text questions, analyze a selected screen region, or ask about something spoken during a configurable recent-audio window.

## Current Release

- **Version:** `v2.0.0`
- **Platform:** Windows x64
- **Download:** `NovaLens-Setup-v2.0.0-Windows-x64.exe`
- **AI provider:** Google Gemini
- **License:** No project license has been selected yet

## What's New in 2.0.0

Nova Lens 2.0.0 adds a guided first-launch setup, configurable screen and audio hotkeys, normal and compact popup modes, a safe in-app bug-report flow, a per-user Windows installer, and major popup-rendering stability improvements.

## Download and Install

1. Open the latest release on GitHub.
2. Download `NovaLens-Setup-v2.0.0-Windows-x64.exe`.
3. Run the installer and follow the setup wizard.
4. Open Nova Lens and complete the first-launch guide.

Windows may display a SmartScreen warning because Nova Lens is not currently code-signed.

## First Launch

Nova Lens uses a bring-your-own-key system. The application does not include a shared Gemini API key.

On first launch, Nova Lens automatically opens Settings with a **Welcome to Nova Lens** setup guide. Add your Gemini API key, choose the interface and shortcuts, review the audio options, and press **Save changes**. The welcome guide is then marked as completed and normal launches continue in the background.

Nova Lens stores the API key locally at:

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
- Selectable screen-region analysis.
- Configurable rolling microphone buffer stored in memory.
- Audio transcription followed by an automatic answer.
- Scrollable screenshot and audio responses.
- Microphone activity indicator.
- Persistent Open / Close control bubble.
- Movable audio and control bubbles with saved positions.
- Entry and fade-out popup animations.
- Automatic hiding after inactivity.
- Click-through behavior after the popup loses focus.
- Dynamic popup height and scrolling for long responses.
- Copy-response button.
- Prevention of multiple Nova Lens background instances.
- Graphical Settings interface.
- Guided first-launch setup inside the Settings interface.
- Custom colors, transparency, font size, border radius, margin, and popup position.
- Configurable auto-hide timer.
- Configurable microphone capture duration from 3 to 30 seconds.
- Optional microphone buffer and activity indicator.
- Customizable text-popup and close hotkeys.
- Customizable screen-region and recent-audio hotkeys.
- Normal full-width and centered compact popup modes.
- In-app bug-report button that opens a prefilled GitHub draft for review.
- Per-user Windows installer.
- English and Spanish interface localization.
- Optional startup with Windows.
- Local API-key and settings storage.

## Default Hotkeys

| Action | Hotkey |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Settings | `P + Shift + Enter` |
| Select and analyze a screen region | `P + Shift + S` |
| Transcribe and answer the previous 10 seconds of microphone audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` |
| Alternative close shortcut | `P + Delete` |

All six shortcuts can be changed from the Settings interface.

## How the Main Modes Work

### Text popup

Press `P + Enter`, write a question, and press Enter or click **Enviar**. Nova Lens sends the request to Gemini and displays the answer inside the same popup.

The popup remains alive in the background while hidden. Nova Lens synchronizes its native Windows surface before the first visible frame to keep compact and normal modes aligned on scaled displays.

### Screen analysis

Press `P + Shift + S` to open the screen selector. Drag over the exact region you want to analyze and release the mouse button. Nova Lens sends only that selected region to Gemini and displays the answer in a scrollable temporary response window.

Press `Esc` or right-click to cancel the selection without sending an image.

### Recent audio

While Nova Lens is running, it can keep the newest 3 to 30 seconds of microphone input in a circular memory buffer. The duration, microphone buffer, and activity indicator can be configured from Settings. Older audio is continuously overwritten.

Press `P + Shift + A` to send a snapshot of that recent audio to Gemini for transcription and an answer.

Nova Lens does not capture desktop or system audio. It uses the Windows default microphone input.

### Floating controls

Nova Lens includes a persistent control bubble with **Open** and **Close** buttons. **Open** activates the text popup, while **Close** hides only the text popup and leaves Nova Lens running.

In Settings, enable **Unlock floating bubbles to move them**, drag the microphone indicator or the Open / Close bubble, and press **Save changes**. Their positions are stored locally and restored on the next launch.

## Privacy and Security

- Your Gemini API key is stored locally in `%APPDATA%\NovaLens\.env`.
- The API key is not bundled in the executable or installer.
- The rolling microphone buffer is kept in RAM.
- Older microphone audio is continuously overwritten.
- Audio is sent to Gemini only after `P + Shift + A` is pressed.
- A temporary WAV file is created only for processing and is deleted afterward.
- A selected screen region is sent to Gemini only after the selection is completed.
- Closing Nova Lens stops the microphone stream and clears the in-memory audio buffer.
- Never include API keys in screenshots, logs, issues, or public repositories.
- The in-app report button creates only a local browser draft; the user reviews and submits it manually.

Do not run Nova Lens around private conversations unless everyone present understands that the rolling microphone buffer is active.

## Known Limitations

- Windows x64 is the only packaged platform.
- The application and installer are not code-signed yet.
- The selected default Windows microphone must work correctly.
- Reporting an error requires a browser and a GitHub account to submit the draft.
- Video analysis is not implemented.
- AI answers and transcriptions may be incorrect.
- Gemini access depends on the user's Google project, API key status, quota, and service availability.

## Project Structure

```text
NovaLens/
├── .github/
│   └── workflows/
├── audio_indicator.py
├── app_info.py
├── assets/
├── backend.py
├── bubble_layout.py
├── build_exe.ps1
├── build_installer.ps1
├── config.py
├── config_manager.py
├── control_bubble.py
├── launcher.py
├── main.py
├── multimodal.py
├── native_clickthrough.py
├── popup.py
├── popup_exe.py
├── popup_layout.py
├── reporting.py
├── rolling_audio.py
├── screen_selector.py
├── tests/
├── requirements-build.txt
├── requirements.txt
├── README.md
├── RELEASE_NOTES_v2.0.0.md
└── .gitignore
```

### Main Files

- `launcher.py`: packaged application entry point and AppData path configuration.
- `main.py`: background process, global hotkeys, child processes, and rolling-audio control.
- `popup.py`: development entry point for the shared text-popup implementation.
- `popup_exe.py`: shared source and packaged popup implementation with stable hiding and animations.
- `multimodal.py`: scrollable screen-region and recent-audio response windows.
- `screen_selector.py`: native screen-region selection and exact image capture.
- `audio_indicator.py`: movable microphone activity bubble.
- `control_bubble.py`: persistent Open / Close control bubble.
- `bubble_layout.py`: local floating-bubble position and unlock-state management.
- `native_clickthrough.py`: native Windows click-through protection.
- `rolling_audio.py`: circular in-memory microphone buffer.
- `backend.py`: Google Gemini text, image, and audio requests.
- `config.py`: graphical Settings interface.
- `config_manager.py`: local configuration, API-key storage, and Windows startup management.
- `build_exe.ps1`: clean Windows build, ZIP packaging, and SHA-256 checksum generation.
- `build_installer.ps1`: Inno Setup build and installer checksum generation.
- `installer/NovaLens.iss`: per-user Windows installer definition.

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
NovaLens-v2.0.0-Windows-x64.zip
NovaLens-v2.0.0-Windows-x64.zip.sha256
```

The ZIP must contain the complete `NovaLens` folder, including both `NovaLens.exe` and `_internal`.

### Build the Windows installer

Install Inno Setup 6, then run:

```powershell
.\build_installer.ps1
```

This builds the portable application first and then creates:

```text
installer-output\NovaLens-Setup-v2.0.0-Windows-x64.exe
installer-output\NovaLens-Setup-v2.0.0-Windows-x64.exe.sha256
```

To reuse an already-built `dist\NovaLens` folder, run `.\build_installer.ps1 -SkipPortableBuild`.

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
- [x] Guided first-launch onboarding.
- [x] Custom appearance and text-popup hotkeys.
- [x] Optional startup with Windows.
- [x] Selectable screen-region analysis.
- [x] Configurable rolling microphone buffer.
- [x] Audio transcription and automatic answers.
- [x] Windows x64 executable package.
- [x] Microphone activity indicator.
- [x] Enable or disable rolling audio from Settings.
- [x] Configurable rolling-audio duration.
- [x] Persistent Open / Close control bubble.
- [x] Movable floating bubbles with saved positions.
- [x] Scrollable screen and audio responses.
- [x] Configurable screen and audio hotkeys.
- [x] Compact and normal display modes.
- [x] Stable first-frame popup rendering on scaled Windows displays.
- [x] Official Discord server and community integration.
- [x] Functional in-app error-reporting button.
- [x] Windows installer build.
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
