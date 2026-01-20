# GPO Fishing Macro

Automated fishing bot for Grand Piece Online with a clean web UI and PD control.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)

## Features

- **PD Controller** for smooth fishing minigame tracking
- **Auto-buy bait** - configurable purchase intervals
- **Auto-store devil fruits**
- **Anti-macro detection** - clears black screens automatically
- **Hybrid-based UI** - no tkinter nonsense
- **Real-time stats** - fish count, time, fish/hour
- **Customizable everything** - hotkeys, timings, automation settings

## Installation
```bash
git clone https://github.com/K3nD4rk-Code-Developer/Grand-Piece-Online-Fishing.git
cd gpo-fishing-macro
pip install -r requirements.txt
```

## Usage

1. Run the app:
```bash
   npm run tauri dev -- --no-watch
```

That's it. The bot handles the rest.

## Hotkeys

- `F1` - Start/Stop
- `F2` - Change area
- `F3` - Exit

You can rebind these in the UI.

## Configuration

The bot auto-saves to `Auto Fish Settings.json`. Everything is configurable through the interface.

### PD Tuning

If the fishing tracker is too aggressive or sluggish, adjust these:

- **Kp** - How hard it chases the target (default: 1.4)
- **Kd** - Damping to prevent overshooting (default: 0.6)
- **Approaching Damping** - Extra brake when moving toward target (default: 2.0)

Most people don't need to touch these.

### Auto-Buy Bait

Enable this to automatically purchase bait every N loops. You'll need to set three points:
- Left button (shop option)
- Middle button (quantity confirm)
- Right button (purchase confirm)

## How It Works

The bot uses color detection to find the fishing minigame bars, then applies a PD controller to keep your position on the target. It's basically the same algorithm used in drones and robots, just for fishing in Roblox.

The "approaching damping" feature slows down when getting close to prevent overshooting. The "chasing damping" is lower so it can quickly catch up when far away.

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

## Troubleshooting

**The bot doesn't detect the minigame**
- Make sure the blue area box covers the entire fishing bar
- Check your screen scaling settings (should work with DPI awareness)

**Auto-buy bait doesn't work**
- Set all three points (Left, Middle, Right) correctly
- Increase the click delays in Advanced settings if your game is laggy

**It keeps missing the fish**
- Lower Kp if it's too aggressive
- Raise Kd if it's oscillating back and forth
- Increase approaching damping if it overshoots

## License

MIT - do whatever you want with it, just credit