# Pleiada Recorder

**Pleiada Recorder** is an open-source Windows utility developed by [Pleiada](https://pleiada.ai) for the **Gameplay Alliance** program. It automates gameplay recording via OBS Studio while simultaneously capturing anonymized, time-synchronized keyboard and mouse activity logs — enabling behavioral research on gaming sessions without collecting any personally identifiable information.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Components](#components)
  - [gameplay\_logger.ahk](#gameplay_loggerahk)
  - [obs\_control.py](#obs_controlpy)
  - [configure\_obs.py](#configure_obspy)
  - [pleiada\_setup\_wizard.pyw](#pleiada_setup_wizardpyw)
  - [pleiada\_check.pyw](#pleiada_checkpyw)
- [Installer](#installer)
- [Building from Source](#building-from-source)
- [Privacy & Data Collection](#privacy--data-collection)
- [Dependencies](#dependencies)
- [License](#license)

---

## Overview

Participants in the Gameplay Alliance program install Pleiada Recorder on their gaming PC. When they start a gameplay session, a small floating window appears on screen. Pressing **Iniciar grabación** simultaneously:

1. Starts an OBS Studio screen capture
2. Begins logging every keyboard and mouse event with millisecond timestamps

When the session ends, pressing **Detener grabación** stops both the video recording and the input log, and moves both files into a timestamped session folder. The Synch Checker tool (`pleiada_check.pyw`) can then be used to verify that the video and log files are properly time-aligned before upload.

---

## Features

- One-click start/stop for synchronized video + input recording
- Floating, always-on-top GUI positioned below the game window (does not appear in recordings)
- Automatic OBS launch and WebSocket connection with self-healing on bad state
- Desktop audio captured; microphone always muted
- Anonymized input logs (key names and mouse positions only — no content, no screenshots)
- Post-install configuration wizard for first-time OBS setup
- Sync verification tool with automatic session folder detection
- Fully automated installer: installs Python, AutoHotkey, OBS, Python packages, and configures OBS in one pass

---

## Architecture

```
┌─────────────────────────────────────────────┐
│            gameplay_logger.ahk              │
│  (AutoHotkey v2 — floating GUI + input log) │
└────────────────────┬────────────────────────┘
                     │ subprocess calls
          ┌──────────┴──────────┐
          │                     │
          ▼                     ▼
  obs_control.py start    obs_control.py stop
  (Python — OBS WebSocket v5 client)
          │
          │ ws://localhost:4455
          ▼
  ┌───────────────┐
  │  OBS Studio   │  ← configured by configure_obs.py at install time
  │  (recording)  │
  └───────────────┘

Session output folder:
  %OneDrive%\Documents\Pleiada Recordings\
    └── 2026-04-26 15-13-40 recording\
          ├── 2026-04-26 15-13-42.mp4   ← video (moved from OBS output)
          └── gameplay_log_....txt       ← input event log
```

---

## Components

### `gameplay_logger.ahk`

**Runtime:** AutoHotkey v2.0+  
**Role:** Main user-facing process. Handles the GUI, input logging, and orchestration.

#### GUI
- Frameless floating window (`-Caption +ToolWindow +AlwaysOnTop`)
- Positioned at the bottom center of the primary monitor's work area using `MonitorGetWorkArea`, 8 px above the taskbar
- Draggable via a header strip that returns `HTCAPTION (2)` on `WM_NCHITTEST` for the top 28 px
- Does not appear in OBS recordings because it sits outside the game window bounds and the OBS scene captures the full monitor

#### Recording flow
1. User clicks **Iniciar grabación**
2. A timestamped session folder is created under `%OneDrive%\Documents\Pleiada Recordings\`
3. `obs_control.py start` is launched via `Run` (hidden window)
4. A live timer starts updating in the GUI every second
5. Input hooks (`InputHook`, `OnMessage WM_INPUT`) begin capturing raw keyboard and mouse events
6. User clicks **Detener grabación**
7. Input hooks are released and the log file is flushed
8. `obs_control.py stop <session_folder>` is launched — OBS stops recording and moves the video into the session folder

#### Input log format
Plain text, one event per line:

```
[HH:MM:SS.mmm] KEY_DOWN  a
[HH:MM:SS.mmm] KEY_UP    a
[HH:MM:SS.mmm] MOUSE_MOVE  x=1024 y=768
[HH:MM:SS.mmm] MOUSE_DOWN  LEFT
[HH:MM:SS.mmm] MOUSE_UP    LEFT
[HH:MM:SS.mmm] MOUSE_WHEEL delta=120
```

All coordinates are in screen pixels. Key names follow AutoHotkey's key name conventions. No text content, clipboard data, or application context is logged.

---

### `obs_control.py`

**Runtime:** Python 3.12+  
**Dependencies:** `websocket-client`  
**Role:** CLI wrapper around the OBS WebSocket v5 API. Called by `gameplay_logger.ahk` as a subprocess.

#### Usage

```
python obs_control.py start
python obs_control.py stop [session_folder]
```

#### Start sequence

1. **OBS detection** — checks `tasklist` for `obs64.exe`
2. **Launch if needed** — locates `obs64.exe` via a priority list of known paths, then Windows Registry, then glob fallback; launches with `subprocess.Popen`
3. **WebSocket connect** — polls `ws://localhost:4455` for up to 30 seconds; authenticates via OBS WebSocket v5 protocol (SHA-256 + base64 challenge/response)
4. **Self-healing** — if the WebSocket connect raises any exception (connection refused, timeout, protocol error), on the first attempt the script kills `obs64.exe` via `taskkill /F` and re-launches from scratch; the second attempt is final
5. **Audio setup** — calls `GetInputList`; unmutes `wasapi_output_capture` (desktop/game audio); mutes all `wasapi_input_capture` sources (microphone); creates the desktop audio source if absent using the active scene name from `GetCurrentProgramScene`
6. **Start recording** — calls `StartRecord`; polls `GetRecordStatus.outputActive` up to 50 times (100 ms intervals) to confirm the recording is live

#### Stop sequence

1. Connects and authenticates to OBS WebSocket
2. Calls `StopRecord`; reads `outputPath` from the response
3. Falls back to scanning `~/Videos` for the most recently modified video file if `outputPath` is empty or the file is missing
4. Moves the video file into `session_folder` with up to 20 retries and 500 ms intervals (handles the case where OBS has not yet finished flushing the file)

#### Debug log

All operations are appended to `%TEMP%\pleiada_obs_debug.txt` with `[HH:MM:SS]` timestamps.

---

### `configure_obs.py`

**Runtime:** Python 3.12+  
**Role:** Runs once during installation (via Inno Setup `[Run]` section, hidden). Configures OBS for Pleiada without requiring user interaction.

#### What it configures

| Target | File | Action |
|--------|------|--------|
| WebSocket plugin | `%APPDATA%\obs-studio\plugin_config\obs-websocket\config.json` | Enables server on port 4455, no authentication, suppresses first-run alert |
| Recording profile | `%APPDATA%\obs-studio\basic\profiles\Pleiada\basic.ini` | MP4, 1920×1080, 60 fps, 2500 kbps video, 160 kbps audio |
| Scene collection | `%APPDATA%\obs-studio\basic\scenes\Pleiada.json` | Scene "Escena" with `monitor_capture` (primary monitor) + `wasapi_output_capture` (default desktop audio), no microphone source |
| Active profile/scene | `%APPDATA%\obs-studio\global.ini` | Points `[Basic]` to profile `Pleiada` and scene collection `Pleiada`; sets `FirstRun=false` to suppress the auto-configure wizard |

The profile and scene collection files are only created if they do not already exist, preserving any prior user customization.

---

### `pleiada_setup_wizard.pyw`

**Runtime:** Python 3.12+ (Tkinter)  
**Role:** 3-page post-install wizard that guides the user through the first OBS configuration. Launched automatically at the end of the Inno Setup installer.

#### Pages

| Page | Content |
|------|---------|
| 1 — OBS Setup | Instructions to open OBS, run the auto-configuration wizard (select "Optimize for recording only", 1080p, 60 or 30 fps), and confirm completion with a checkbox |
| 2 — Recorder | Instructions for using the floating recorder window: how to start and stop a session, where files are saved |
| 3 — Sync Checker | Instructions for using `pleiada_check.pyw` to verify session files; link to `pleiada.ai/faqs` |

The window is 580×560 px, centered on screen. The footer (navigation buttons) is packed before the content frame to guarantee button visibility regardless of content height. The application icon is loaded from the same directory as `__file__` rather than `sys.argv[0]` to ensure reliability when launched via shell file association.

---

### `pleiada_check.pyw`

**Runtime:** Python 3.12+ (Tkinter + OpenCV + Pillow)  
**Role:** Standalone sync verification tool. Allows the participant or researcher to confirm that the video recording and the input log file in a session folder are properly time-aligned.

---

## Installer

The installer is built with [Inno Setup 6](https://jrsoftware.org/isinfo.php) from `pleiada_installer/setup.iss`.

### What the installer does

1. Presents a consent and information page (required checkbox before proceeding)
2. Installs Python 3.12.8 silently (user-scope, `PrependPath=1`) if `HKCU\Software\Python\PythonCore\3.12` does not exist
3. Installs AutoHotkey v2.0.24 (interactive, standard wizard)
4. Closes OBS if running, then installs OBS Studio 32.1.2 (interactive)
5. Closes OBS if the OBS installer re-launched it
6. Installs Python packages: `websocket-client`, `Pillow`, `opencv-python` via pip
7. Runs `configure_obs.py` to configure OBS automatically
8. Launches `pleiada_setup_wizard.pyw` to guide first-time setup

### Installer output

`pleiada_installer/Output/PleiadaRecorder_Setup_V<N>.exe`

### Desktop shortcuts created

| Shortcut | Target | Purpose |
|----------|--------|---------|
| Pleiada Recorder | `gameplay_logger.ahk` | Start a recording session |
| Synch Checker | `pleiada_check.pyw` | Verify session sync |

---

## Building from Source

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Windows | 10 / 11 x64 | Build and target platform |
| [Inno Setup 6](https://jrsoftware.org/isdl.php) | 6.x | Installer compiler |
| PowerShell | 5.1+ | Bundled with Windows |
| Internet access | — | To download deps during build |

The build script (`BuildPleiadaSetup.ps1`) downloads all three dependency installers automatically if they are not already present in `pleiada_installer/deps/`.

### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/<org>/pleiada-recorder.git
cd pleiada-recorder

# 2. Allow script execution for this session
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# 3. Run the build script (downloads deps + compiles)
cd pleiada_installer
.\BuildPleiadaSetup.ps1
```

The compiled installer is written to `pleiada_installer/Output/`.

### CI/CD (GitHub Actions)

Pushing a tag triggers an automated build on a `windows-latest` GitHub Actions runner:

```bash
git tag v0.17
git push origin v0.17
```

The workflow (`.github/workflows/build.yml`):
- Downloads all three dependency installers
- Installs Inno Setup 6 silently
- Compiles `setup.iss`
- Uploads the `.exe` as a workflow artifact (available on every build)
- Publishes a GitHub Release with the `.exe` as a downloadable asset (tag builds only)

---

## Privacy & Data Collection

Pleiada Recorder is designed with privacy as a hard constraint.

| Data type | Collected | Notes |
|-----------|-----------|-------|
| Screen video | Yes | Local file only; uploaded manually by participant |
| Key names | Yes | e.g. `a`, `Space`, `LShift` — no key sequences or text content |
| Mouse position | Yes | Pixel coordinates relative to screen |
| Mouse buttons / wheel | Yes | Button identifier and wheel delta only |
| Application names | No | — |
| Clipboard content | No | — |
| Network traffic | No | — |
| Personal identifiers | No | — |
| Microphone / camera | No | Mic source is always muted |

All data remains local until the participant uploads it manually via the process defined by the Gameplay Alliance program. No telemetry, no automatic upload, no remote connections.

---

## Dependencies

| Package | Version | License | Purpose |
|---------|---------|---------|---------|
| [AutoHotkey v2](https://www.autohotkey.com/) | 2.0.24 | GPL-2.0 | GUI, input hooks, subprocess orchestration |
| [OBS Studio](https://obsproject.com/) | 32.1.2 | GPL-2.0 | Screen and audio recording |
| [Python](https://www.python.org/) | 3.12.8 | PSF-2.0 | Runtime for control and verification scripts |
| [websocket-client](https://github.com/websocket-client/websocket-client) | latest | Apache-2.0 | OBS WebSocket v5 communication |
| [Pillow](https://python-pillow.org/) | latest | HPND | Image processing in sync checker |
| [opencv-python](https://github.com/opencv/opencv-python) | latest | MIT | Video frame analysis in sync checker |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | 6.x | ISL (custom) | Installer compiler (build-time only) |

All runtime dependencies are open source. Inno Setup is used only at build time and is not redistributed.

---

## License

This project is licensed under the [MIT License](LICENSE).

Copyright © 2026 Pleiada

---

## Contact

Program information: [pleiada.ai](https://pleiada.ai)  
FAQ: [pleiada.ai/faqs](https://pleiada.ai/faqs)  
Terms: [pleiada.ai/terms](https://pleiada.ai/terms)
