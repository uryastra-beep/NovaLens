# Nova Lens v1.0.1 — First Windows Release

**Release date:** August 7, 2026

Nova Lens v1.0.1 is the first official release with a packaged Windows executable. It is distributed as a portable ZIP and does not require an installer.

## Highlights

- Added the official portable Windows x64 package.
- Added bring-your-own-key setup for Google Gemini, with the API key and settings stored locally in the user's AppData folder.
- Added a persistent background process and global hotkeys.
- Added the floating text popup with follow-up questions and short conversation context.
- Added reliable scrolling for long popup answers.
- Added full visible-desktop screenshot analysis.
- Added rolling 10-second microphone capture, transcription, and automatic answers.
- Added the graphical Settings interface with live preview and Restore Defaults.
- Added English and Spanish localization across the application.
- Added customizable popup colors, transparency, font size, border radius, margin, position, auto-hide time, and supported shortcuts.
- Added optional startup with Windows.
- Added pinned dependencies, regression tests, and a manually triggered release workflow.

## Reliability and Safety Fixes

- Fixed repeated popup collapse and ghost-window behavior by keeping the native window alive while hidden.
- Fixed click-through after the popup hides so the desktop remains interactive.
- Restored safe popup entry and fade-out animations.
- Fixed invalid, duplicate, and reserved custom-hotkey handling.
- Prevented the popup from appearing inside screenshots captured for analysis.
- Prevented user API keys, settings, temporary credentials, and debug files from being included in release packages.
- Improved microphone stream recovery and cleanup of temporary audio files.
- Updated the Gemini integration to Google GenAI and Gemini 3.6 Flash with clearer authentication and runtime errors.

## Download

Download:

```text
NovaLens-v1.0.1-Windows-x64.zip
```

A SHA-256 checksum file is included as a separate release asset.

## Installation

1. Download the Windows ZIP.
2. Extract the entire ZIP.
3. Keep `NovaLens.exe` and `_internal` together.
4. Open `NovaLens.exe`.
5. Add your own Gemini API key in Settings.

Do not run the executable from inside the ZIP file.

Windows may show a SmartScreen warning because this release is not code-signed.

## Default Hotkeys

| Action | Hotkey |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Settings | `P + Shift + Enter` |
| Analyze the visible desktop | `P + Shift + S` |
| Analyze the previous 10 seconds of microphone audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` or `P + Delete` |

## Privacy

Nova Lens does not include a shared API key. Each user supplies their own Gemini API key, which is stored locally in `%APPDATA%\NovaLens\.env`.

The rolling microphone buffer stays in memory, keeps only the newest 10 seconds, and is sent to Gemini only when the audio hotkey is pressed.

## Known Limitations

- Windows x64 only.
- No installer or code signing yet.
- Screenshot analysis captures the complete visible desktop.
- Screen and audio shortcuts are currently fixed.
- The microphone duration is fixed at 10 seconds.
- There is no microphone activity tray indicator.
- The error-reporting button is not connected yet.
- Gemini availability depends on the user's API key, project, quota, and Google service status.

## Support

Discord: https://discord.gg/Dfns48WEqH
