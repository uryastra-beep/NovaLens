# Nova Lens v1.1.0 — Screen, Audio & Floating Controls

Nova Lens v1.1.0 expands the Windows desktop assistant with selectable screen analysis, configurable recent-audio capture, persistent floating controls, and a broad set of stability improvements.

## Highlights

- Select an exact screen region with `P + Shift + S` and send only that region to Gemini.
- Ask about recent microphone audio with `P + Shift + A`.
- Configure the rolling microphone buffer from 3 to 30 seconds.
- Enable or disable recent-audio capture and its activity indicator from Settings.
- Use the persistent **Open / Close** control bubble without relying only on shortcuts.
- Unlock, drag, and save the positions of the microphone and control bubbles.

## Interface Improvements

- Added reliable scrolling for long text, screenshot, and audio responses.
- Added English and Spanish interface localization.
- Added customizable bubble colors, transparency, margins, and saved positions.
- Preserved global keyboard shortcuts alongside the new floating controls.
- Added clearer microphone activity feedback.

## Stability and Reliability

- Fixed distorted screen-region previews and inaccurate selections on scaled displays.
- Improved DPI handling for screen capture and floating windows.
- Fixed leftover Flet **Working...** windows when Nova Lens closes.
- Nova Lens now terminates only its own packaged process trees.
- Improved cleanup of build output, temporary audio, and transient UI files.
- Added configuration validation, collision-safe hotkeys, and additional regression coverage.

## Privacy

- The Gemini API key remains stored locally in `%APPDATA%\NovaLens\.env`.
- Microphone audio stays in a rolling in-memory buffer until the audio shortcut is used.
- Only the selected screen region is sent after completing a screen selection.
- Saved settings and floating-window positions stay on the local device.

## Installation

1. Download `NovaLens-v1.1.0-Windows-x64.zip` and its optional `.sha256` checksum.
2. Extract the complete ZIP file.
3. Keep `NovaLens.exe` and the `_internal` folder together.
4. Open `NovaLens.exe` and save your personal Gemini API key in Settings.

Do not run Nova Lens directly from inside the ZIP file.

Windows may display a SmartScreen warning because the application is not currently code-signed.

## Default Shortcuts

| Action | Shortcut |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Settings | `P + Shift + Enter` |
| Select and analyze a screen region | `P + Shift + S` |
| Analyze recent microphone audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` |
| Alternative close shortcut | `P + Delete` |

## Known Limitations

- Windows x64 is the only packaged platform in this release.
- The application is not code-signed and does not include an installer yet.
- Screen and audio shortcuts are not configurable yet.
- The in-app error-reporting button does not submit reports yet.
- Video analysis is not implemented.
- Gemini responses and transcriptions may be incorrect.

Thank you for testing Nova Lens and reporting reproducible issues through GitHub or the official Discord community.
