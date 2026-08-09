# Nova Lens v2.0.1 — Bug Fixes

Nova Lens v2.0.1 is a focused Windows maintenance release that stabilizes the persistent control bubble and improves recovery when the interface is hidden or unresponsive.

## Highlights

- Restored the persistent **Open / Close / Reset** control bubble when Windows hides its native window.
- Fixed the automatic infinite close-and-reopen loop reported after startup.
- Fixed the separate click-triggered close-and-reopen loop.
- Added a safe full **Reset** action and a post-reset prompt with an optional Discord error-report path.
- Improved first-run bubble visibility and native window recovery without restarting healthy processes.

## Control Bubble Reliability

- Reworked supervision to trust a live process with a fresh heartbeat instead of requiring the visible Flet window to belong to one exact process ID.
- Added heartbeat-based health checks so a healthy packaged bubble is not repeatedly destroyed and recreated.
- Added native visibility repair using the bubble's unique window title.
- Added duplicate-click throttling to prevent repeated identical commands.
- Latched the Reset command so one click results in one controlled restart.
- Kept the saved movable-bubble position and Settings unlock behavior.

## Interface and Project Updates

- Added the **Reset** control beside Open and Close.
- Added a recovery prompt after Reset with an optional link to the official Nova Lens Discord server.
- Polished Settings and shortcut icons.
- Refreshed Nova Lens application branding and Windows assets.
- Changed the interface action label from **Enviar** to **Send**.
- Added the GNU General Public License v3.0 only (`GPL-3.0-only`).

## Validation

- Passed the complete automated regression suite: 53 tests.
- Passed the GitHub Actions Python checks.
- Built and verified the Windows x64 installer through the release workflow.

## Installation

1. Download `NovaLens-Setup-v2.0.1-Windows-x64.exe`.
2. Close any running Nova Lens instance.
3. Run the installer and follow the setup wizard.
4. Launch Nova Lens normally after installation.

Existing Gemini keys and user settings under `%APPDATA%\NovaLens` are preserved during the upgrade.

## Release Asset

- `NovaLens-Setup-v2.0.1-Windows-x64.exe` — recommended Windows x64 installer.

Windows may display a SmartScreen warning because Nova Lens is not currently code-signed.

## Known Limitations

- Windows x64 is the only packaged platform.
- The application and installer are not code-signed.
- Gemini access depends on the user's API key, Google project, quota, and service availability.
- AI responses and transcriptions may be incorrect and should be verified when accuracy matters.
