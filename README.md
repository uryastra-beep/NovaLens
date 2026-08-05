# NovaLens

**NovaLens — Powered by Google Gemini**

NovaLens is a Windows desktop assistant that lets you ask an AI questions from any application through a floating popup.

The app runs in the background, can be opened with a global hotkey, and supports click-through mode so you can keep using the window behind it.

> NovaLens is currently in **Beta**.

---

## Project Status

- **Current version:** `v0.2.0-beta`
- **Supported platform:** Windows
- **Language:** Python
- **Interface:** Flet
- **AI provider:** Google Gemini

NovaLens currently includes a functional Gemini-powered popup and a graphical settings interface.

This release is distributed as source code and is intended mainly for developers, collaborators, and early testers.

---

## Available Features

- Persistent background execution.
- Always-on-top floating popup.
- Google Gemini integration.
- Questions written directly inside the popup.
- Follow-up questions.
- Basic context between consecutive questions.
- Global hotkeys.
- Entry animation from the top of the screen.
- Fade-out exit animation.
- Automatic hiding after inactivity.
- Timer reset when typing, clicking, or scrolling.
- Automatic click-through when the popup loses focus.
- Button to copy responses.
- Button to hide the popup.
- Dynamic height based on response length.
- Internal scrolling for long responses.
- Prevention of multiple NovaLens instances.
- Background execution without a console through `pythonw.exe`.
- Graphical settings interface.
- Persistent settings through `config.json`.
- Customizable colors and transparency.
- Configurable font size, border radius, margin, and popup position.
- Configurable auto-hide timer.
- Customizable global hotkeys.
- Optional startup with Windows.

---

## Default Hotkeys

| Action | Hotkey |
|---|---|
| Open or reactivate NovaLens | `P + Enter` |
| Open NovaLens settings | `P + Shift + Enter` |
| Completely close NovaLens | `P + Backspace` |
| Completely close NovaLens | `P + Delete` |

These hotkeys can be changed from the settings interface.

---

## How It Works

When NovaLens starts, it remains in the background waiting for a hotkey.

When `P + Enter` is pressed:

1. The popup appears from the top of the screen.
2. The user writes a question.
3. NovaLens sends the request to Google Gemini.
4. The answer appears inside the same popup.
5. The user can ask follow-up questions.
6. After the configured inactivity period, the popup fades out and disappears.

When the popup loses focus, it automatically enables click-through mode. This lets the user continue clicking and working normally in the application behind NovaLens.

Press `P + Enter` again to reactivate the popup and interact with it.

---

## Settings Interface

NovaLens includes a graphical settings window that can be opened with:

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
- Global hotkeys.
- Startup with Windows.

Settings are stored locally in `config.json`.

---

## Default Appearance

The default design includes:

- Semi-transparent brown background.
- Primary color: `#522E18`.
- Approximately `60%` transparency.
- Cream-colored text.
- Rounded corners.
- Position at the top of the screen.
- Margin from the monitor edges.
- Dynamic height.
- Maximum height of approximately 10 cm.
- Curtain-style entry animation.
- Fade-out exit animation.

---

## Project Structure

```text
NovaLens/
├── backend.py
├── config.py
├── config_manager.py
├── main.py
├── popup.py
├── requirements.txt
├── README.md
├── .env
├── .gitignore
├── config.json
└── .venv/
```

### Main Files

- `main.py`: keeps NovaLens running in the background and manages global hotkeys.
- `popup.py`: contains the floating interface, animations, timer, and click-through behavior.
- `backend.py`: manages the Google Gemini connection.
- `config.py`: contains the graphical settings interface.
- `config_manager.py`: loads, validates, saves, and restores NovaLens settings.
- `requirements.txt`: contains the project dependencies.
- `.env`: stores the Google Gemini API key locally.
- `config.json`: stores local user preferences.
- `.gitignore`: prevents private, temporary, and local files from being uploaded.

> The `.env` file contains private information and must never be uploaded to GitHub.

---

## Installation for Developers

NovaLens Beta is currently distributed as source code and does not yet include an official installer or `.exe` file.

These instructions are intended for developers or anyone who wants to test, study, or contribute to the project.

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

In PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 4. Install the dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## Configure Google Gemini

For security reasons, NovaLens does not include the developer's API key.

Anyone running NovaLens from source code must use their own Google Gemini API key.

Create a file named `.env` in the main project folder:

```env
GEMINI_API_KEY=YOUR_OWN_API_KEY
```

Do not add quotation marks around the API key.

The `.env` file is excluded from the repository through `.gitignore` and must never be published.

---

## Run NovaLens from Source

### Development mode

```powershell
python main.py
```

The terminal will remain open while NovaLens is running.

### Background mode

```powershell
.\.venv\Scripts\pythonw.exe main.py
```

NovaLens will run without displaying a terminal window.

To open or reactivate the popup:

```text
P + Enter
```

To open the settings interface:

```text
P + Shift + Enter
```

To completely close NovaLens:

```text
P + Backspace
```

or:

```text
P + Delete
```

---

## Dependencies

```text
google-genai
python-dotenv
flet
keyboard
```

---

## Privacy

NovaLens only processes information voluntarily submitted by the user.

The project must not:

- Capture the screen without permission.
- Listen to the microphone without permission.
- Record video secretly.
- Save recordings without permission.
- Include API keys directly in the source code.
- Upload private information automatically.
- Run hidden capture features without clear user action.

Future screen, audio, and video features must be activated through explicit actions or hotkeys.

---

## Beta Limitations

- NovaLens currently only supports Windows.
- Screenshot capture has not been implemented yet.
- Image analysis has not been implemented yet.
- Audio recording and transcription have not been implemented yet.
- Video analysis has not been implemented yet.
- The error-reporting button does not submit reports yet.
- There is no official installer or executable yet.
- Each developer must provide their own Google Gemini API key.
- AI-generated responses may contain errors.

---

## Development Roadmap

- [x] Google Gemini integration.
- [x] Floating popup.
- [x] Questions from the popup.
- [x] Follow-up questions.
- [x] Basic context between questions.
- [x] Entry animation.
- [x] Fade-out animation.
- [x] Automatic hiding.
- [x] Stable click-through behavior.
- [x] Global hotkeys.
- [x] Background execution.
- [x] Prevention of multiple instances.
- [x] Graphical settings interface.
- [x] Customizable hotkeys.
- [x] Color and transparency settings.
- [x] Configurable font size.
- [x] Configurable popup position.
- [x] Configurable auto-hide timer.
- [x] Optional startup with Windows.
- [ ] Compact and normal display modes.
- [ ] Screen region capture.
- [ ] Image analysis.
- [ ] Audio recording and transcription.
- [ ] Short video analysis.
- [ ] Error-reporting system.
- [ ] Windows `.exe` build.
- [ ] Windows installer.
- [ ] Native Linux version.

---

## Current Release

The latest public beta release is:

```text
v0.2.0-beta
```

This version adds the graphical settings interface, persistent configuration, customizable appearance and hotkeys, optional Windows startup, and major click-through and focus stability improvements.

---

## Contributions

NovaLens is still in an early stage of development.

Suggestions, bug reports, and contributions are welcome as the project continues to grow.

---

## Disclaimer

NovaLens may generate incorrect, incomplete, or outdated responses.

Important information should always be verified before use.

NovaLens is not intended to replace medical, legal, financial, or other professional advice.

---

## License

A project license has not been selected yet.

---

Made with Python, Flet, and Google Gemini.
