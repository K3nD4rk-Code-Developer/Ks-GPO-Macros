# K's Macro Launcher

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## Features

- **PD Controller** for smooth fishing minigame tracking
- **Auto-craft bait** - configurable purchase intervals
- **Auto-buy bait** - configurable craft intervals
- **Auto-store devil fruits** - ability to store to ` backpack instead
- **Anti-macro detection** - clears black screens automatically
- **Hybrid-based UI** - no tkinter nonsense
- **Real-time stats** - fish count, time, fish/hour
- **Customizable everything** - hotkeys, timings, automation settings

## Installation
```bash
git clone https://github.com/K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing.git
cd gpo-fishing-macro
pip install -r requirements.txt
python -m PyInstaller backend.py
```

## Usage

1. Run the app:
```bash
   npm run tauri dev -- --no-watch
```

That's it. The bot handles the rest.

## Hotkeys

- `F1` - Start/Stop
- `F3` - Exit

You can rebind these in the UI.

## Configuration

The bot auto-saves to `Auto Fish Settings.json`. Everything is configurable through the interface.

## Requirements
```
flask
flask-cors
keyboard
mss
numpy
pyautogui
pynput
pywin32
```

Windows only because of the `win32gui` and `keyboard` libraries.

## License

Personal Use LC - Do whatever you want with it, just credit. Don't publish or release partially modified verisons though.