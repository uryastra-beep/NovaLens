# Nova Lens v2.0.0 — Custom Controls, Installer & Popup Stability

Nova Lens v2.0.0 is the largest release of the Windows desktop assistant so far. It completes the configurable control system, introduces a guided setup and Windows installer, and includes a full overhaul of popup rendering and lifecycle stability.

## Highlights

- Added a modern per-user Windows installer with Start Menu and optional desktop shortcuts.
- Added a guided **Welcome to Nova Lens** experience for first-time setup.
- Added normal full-width and centered compact popup modes.
- Made screen-region and recent-audio shortcuts fully configurable.
- Added an in-app error-report button that opens a safe, prefilled GitHub draft for user review.
- Preserved the portable Windows ZIP for users who prefer installation-free usage.

## Popup and Interface Stability

- Fixed the intermittent crushed or vertically compressed popup in normal and compact modes.
- Added first-frame native surface synchronization for text, screenshot, and audio popups.
- Kept rendered pixels and clickable hitboxes aligned on scaled Windows displays.
- Unified the source and packaged text popup so both launch paths use the same implementation.
- Improved popup resizing, scrolling, hiding, focus handling, and click-through behavior.
- Improved process cleanup so Nova Lens closes only its own packaged child processes.

## Settings and Controls

- All six global shortcuts can now be customized from Settings.
- Added hotkey validation and collision prevention for text, Settings, screen, audio, and close actions.
- Added normal and compact display-mode selection.
- Added first-launch guidance for connecting Gemini, choosing the interface, reviewing controls, and saving settings.
- Existing appearance, audio, floating-bubble, language, and startup preferences remain stored locally.

## Privacy and Security

- Nova Lens continues to use a bring-your-own-key system; no shared Gemini API key is included.
- API keys and settings remain stored locally under `%APPDATA%\NovaLens`.
- The microphone buffer remains in memory and is sent only when the configured audio shortcut is used.
- Screen content is sent only after the user completes a region selection.
- Bug reports open as browser drafts and are never submitted automatically.
- Release packages exclude local keys, settings, temporary audio, and debug files.

## Installation

### Windows installer (recommended)

1. Download `NovaLens-Setup-v2.0.0-Windows-x64.exe`.
2. Run the setup wizard.
3. Open Nova Lens and complete the first-launch guide.

### Portable ZIP

1. Download `NovaLens-v2.0.0-Windows-x64.zip`.
2. Extract the complete ZIP.
3. Keep `NovaLens.exe` and the `_internal` folder together.
4. Run `NovaLens.exe` and complete the first-launch guide.

Do not run Nova Lens directly from inside the ZIP file.

## Release Assets

- `NovaLens-Setup-v2.0.0-Windows-x64.exe` — recommended Windows installer.
- `NovaLens-v2.0.0-Windows-x64.zip` — portable application package.
- `NovaLens-v2.0.0-Windows-x64.zip.sha256` — SHA-256 checksum for the portable ZIP.

Windows may show a SmartScreen warning because Nova Lens is not currently code-signed.

## Default Shortcuts

| Action | Shortcut |
|---|---|
| Open or reactivate the text popup | `P + Enter` |
| Open Settings | `P + Shift + Enter` |
| Select and analyze a screen region | `P + Shift + S` |
| Analyze recent microphone audio | `P + Shift + A` |
| Completely close Nova Lens | `P + Backspace` |
| Alternative close shortcut | `P + Delete` |

All shortcuts can be changed from Settings.

## Known Limitations

- Windows x64 is the only packaged platform in this release.
- The application and installer are not code-signed.
- Video analysis and automatic updates are not implemented yet.
- Gemini availability depends on the user's API key, Google project, quota, and service status.
- AI responses and transcriptions may be incorrect and should be verified when accuracy matters.

Thank you to everyone who tested Nova Lens, reproduced difficult popup bugs, and helped make v2.0.0 stable.
