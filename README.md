# Auto Typer

An  app that types text for you. Built with Python and Tkinter, using `pyautogui` to simulate real keystrokes anywhere on your screen (browser, chat, docs, code editor, etc).

## Features

- **GUI text input** - paste or write whatever you want typed
- **Human-like typing** - random delays between keystrokes and occasional pauses, so it doesn't look like an instant paste
- **Adjustable speed** - control the base delay per character
- **Start delay countdown** - gives you time to click into the target window before typing begins
- **Loop mode** - repeat the same text continuously
- **Emergency stop** - flick your mouse to any screen corner to instantly abort typing

## Requirements

- Python 3.x
- [`pyautogui`](https://pypi.org/project/PyAutoGUI/)
- (Optional) [`keyboard`](https://pypi.org/project/keyboard/) - enables a global F8 stop hotkey

Install dependencies:

```bash
pip install pyautogui keyboard
```

## How to run it

Once it's open (any method below), using it is the same:
1. Paste or type the text you want typed out
2. Set a start delay (time to click into your target window)
3. Adjust typing speed and toggle human-like variation / code-safe newlines as needed
4. Click Start  it'll count down, then begin typing automatically wherever your cursor is

There are three ways to launch it:

### 1. From the command line

```bash
pip install pyautogui
python auto_typer.py
```

### 2. Click `.bat` file (Windows, no terminal needed)

Place `Run Auto Typer.bat` in the same folder as `auto_typer.py` and double-click it. It launches the app directly using `pythonw` (no visible console window). Still requires Python + pyautogui installed on the machine.

### 3. Standalone `.exe` (Windows, no Python required at all)

Build it once with [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "AutoTyper" auto_typer.py
```

Antivirus may warn about it the first time since it's unsigned; click "More info" then "Run anyway."


## Notes

- Works in any app that accepts keyboard input  it's simulating real keystrokes system-wide, not pasting.
- I built it as a personal automation tool.

## License

MIT
