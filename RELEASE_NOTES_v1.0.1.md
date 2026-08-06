# Nova Lens v1.0.1 — First Windows Release

**Release date:** August 6, 2026

Nova Lens v1.0.1 is the first official release that includes a packaged Windows executable. It is distributed as a portable ZIP package and does not require an installer.

## Highlights

- Added the official Windows x64 `.exe` package.
- Added a bring-your-own-key setup for Google Gemini.
- Added local API-key and settings storage in the user's AppData folder.
- Added a persistent background process and global hotkeys.
- Added the floating text popup with follow-up questions and short conversation context.
- Added full visible-desktop screenshot analysis.
- Added rolling 10-second microphone capture, transcription, and automatic answers.
- Added the graphical Settings interface.
- Added customizable popup colors, transparency, font size, border radius, margin, position, and auto-hide time.
- Added customizable text-popup and close shortcuts.
- Added optional startup with Windows.
- Fixed repeated popup collapse in the packaged build by keeping the native window alive while hidden.
- Restored safe popup entry and fade-out animations.
- Updated the Gemini integration to the current Google GenAI SDK and Gemini 3.6 Flash.

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
