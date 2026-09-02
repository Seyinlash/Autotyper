# Auto Typer

A simple desktop app that types text for you — like an auto-clicker, but for your keyboard. Built with Python and Tkinter, using `pyautogui` to simulate real keystrokes anywhere on your screen (browser, chat, docs, code editor, etc).

## Features

- **GUI text input** — paste or write whatever you want typed
- **Human-like typing** — randomized delays between keystrokes and occasional "thinking" pauses, so it doesn't look like an instant paste
- **Adjustable speed** — control the base delay per character
- **Start delay countdown** — gives you time to click into the target window before typing begins
- **Loop mode** — repeat the same text continuously
- **Code-safe newlines** — clears editor auto-indent (e.g. in VS Code) after each Enter press so your own formatting doesn't get mangled
- **Presets** — save and reload frequently used text snippets
- **Failsafe** — flick your mouse to any screen corner to instantly abort typing

## Requirements

- Python 3.x
- [`pyautogui`](https://pypi.org/project/PyAutoGUI/)
- (Optional) [`keyboard`](https://pypi.org/project/keyboard/) — enables a global F8 stop hotkey

Install dependencies:

```bash
pip install pyautogui keyboard
```

## How to run it

Once it's open (any method below), using it is the same:
1. Paste or type the text you want typed out
2. Set a start delay (time to click into your target window)
3. Adjust typing speed and toggle human-like variation / code-safe newlines as needed
4. Click **Start** — it'll count down, then begin typing automatically wherever your cursor is

There are three ways to launch it:

### 1. From the command line

```bash
pip install pyautogui
python auto_typer.py
```

### 2. One-click `.bat` file (Windows, no terminal needed)

Place `Run Auto Typer.bat` in the same folder as `auto_typer.py` and double-click it. It launches the app directly using `pythonw` (no visible console window). Still requires Python + pyautogui installed on the machine.

### 3. Standalone `.exe` (Windows, no Python required at all)

Build it once with [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "AutoTyper" auto_typer.py
```

The finished exe will be at `dist/AutoTyper.exe` — move it anywhere and double-click to run. Windows SmartScreen may warn about it the first time since it's unsigned; click "More info" → "Run anyway."

> Note: `.exe` builds don't currently work reliably with the F8 global-hotkey feature (`keyboard` module) — if you build the exe and F8 doesn't stop typing, use the mouse-corner failsafe or the on-screen Stop button instead.

## Notes

- Works in any application that accepts keyboard input — it's simulating real keystrokes system-wide, not pasting.
- Built as a personal automation tool.

## License

MIT
