"""
Auto Typer - types out text for you, human-style
--------------------------------------------------
Requires: pyautogui  (install with: pip install pyautogui)

How it works:
1. Paste/write the text you want typed into the box.
2. Open Settings to set a "start delay" (time to click into the target
   window before typing begins), typing speed, human-like variation,
   auto-indent fix, typo simulation, and loop mode.
3. Hit Start. Move your mouse to the top-left corner of the screen
   at ANY time to abort instantly (pyautogui failsafe).

All settings (including dark mode) persist across restarts in
~/.auto_typer_settings.json
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random
import re
import json
import os

try:
    import pyautogui
except ImportError:
    pyautogui = None

pyautogui_failsafe = True  # moving mouse to screen corner aborts typing

LIGHT = {
    "bg": "#f2f2f2",
    "fg": "#111111",
    "text_bg": "#ffffff",
    "text_fg": "#111111",
    "status_fg": "#555555",
    "hint_fg": "#777777",
}
DARK = {
    "bg": "#1e1e1e",
    "fg": "#e8e8e8",
    "text_bg": "#2b2b2b",
    "text_fg": "#e8e8e8",
    "status_fg": "#aaaaaa",
    "hint_fg": "#888888",
}

SETTINGS_PATH = os.path.join(os.path.expanduser("~"), ".auto_typer_settings.json")
TYPO_CHARS = "abcdefghijklmnopqrstuvwxyz"

# Defaults for every persisted setting (used on first run / missing keys)
DEFAULT_SETTINGS = {
    "dark_mode": False,
    "start_delay": 5.0,
    "char_delay": 0.05,
    "human_mode": True,
    "loop_mode": False,
    "fix_indent": True,
    "typo_mode": False,
    "typo_chance": 6.0,
}


def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            data = json.load(f)
    except Exception:
        data = {}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass  # non-critical, just skip saving if it fails


def format_duration(total_seconds):
    """Shared by the live estimate and the 'Done in ...' status so the
    two never disagree on formatting again."""
    if total_seconds < 60:
        return f"{total_seconds:.1f}s"
    mins = int(total_seconds // 60)
    secs = total_seconds % 60
    return f"{mins}m {secs:.0f}s"


class SettingsWindow(tk.Toplevel):
    """Holds every configuration option. The main window only keeps the
    text box, Start/Stop/Clear, and status/estimate readouts."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title("Auto Typer - Settings")
        self.resizable(False, False)
        self.transient(app.root)

        pad = {"padx": 10, "pady": 6}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True)
        self.frm = frm

        ttk.Label(frm, text="Start delay (sec):").grid(row=0, column=0, sticky="w", **pad)
        ttk.Spinbox(frm, from_=0, to=60, increment=0.5, textvariable=app.start_delay,
                    width=8).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(frm, text="Base delay/char (sec):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Spinbox(frm, from_=0.0, to=1.0, increment=0.01, textvariable=app.char_delay,
                    width=8).grid(row=1, column=1, sticky="w", pady=6)

        ttk.Checkbutton(frm, text="Human-like variation (random pauses)",
                         variable=app.human_mode).grid(row=2, column=0, columnspan=2,
                                                        sticky="w", padx=10, pady=6)

        ttk.Checkbutton(frm, text="Repeat / loop",
                         variable=app.loop_mode).grid(row=3, column=0, columnspan=2,
                                                       sticky="w", padx=10, pady=6)

        ttk.Checkbutton(
            frm,
            text="Fix editor auto-indent (recommended for VS Code / IDEs)",
            variable=app.fix_indent
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=10, pady=6)

        ttk.Checkbutton(
            frm,
            text="Simulate typos (randomly misspell a word, then backspace + fix it)",
            variable=app.typo_mode
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(6, 0))

        ttk.Label(frm, text="Typo chance (%):").grid(row=6, column=0, sticky="w", padx=10, pady=(0, 6))
        ttk.Spinbox(frm, from_=0, to=100, increment=1, textvariable=app.typo_chance,
                    width=8).grid(row=6, column=1, sticky="w", pady=(0, 6))

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=7, column=0, columnspan=2, sticky="e", padx=10, pady=(10, 10))
        ttk.Button(btn_row, text="Close", command=self._on_close).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.apply_theme()

        # settings changes should save immediately, same as dark mode does
        for var in (app.start_delay, app.char_delay, app.human_mode, app.loop_mode,
                    app.fix_indent, app.typo_mode, app.typo_chance):
            var.trace_add("write", lambda *args: app.save_all_settings())

    def apply_theme(self):
        c = DARK if self.app.dark_mode.get() else LIGHT
        self.configure(bg=c["bg"])
        # ttk widgets pick up the shared style already configured on the app

    def _on_close(self):
        self.app.save_all_settings()
        self.destroy()
        self.app.settings_window = None


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        root.title("Auto Typer")
        # Startup size == minimum size, on purpose: this is the smallest
        # size that fits the top bar, text box, status lines, and the
        # Start/Stop/Clear row without clipping anything. The window can
        # still be resized larger, just never smaller than this.
        MIN_WIDTH, MIN_HEIGHT = 700, 700
        root.geometry(f"{MIN_WIDTH}x{MIN_HEIGHT}")
        root.minsize(MIN_WIDTH, MIN_HEIGHT)

        self.typing_thread = None
        self.stop_flag = threading.Event()
        self.settings_window = None

        settings = load_settings()

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        pad = {"padx": 10, "pady": 6}

        # --- All settings live as Variables on the app, regardless of
        # whether the Settings window is currently open ---
        self.dark_mode = tk.BooleanVar(value=settings["dark_mode"])
        self.start_delay = tk.DoubleVar(value=settings["start_delay"])
        self.char_delay = tk.DoubleVar(value=settings["char_delay"])
        self.human_mode = tk.BooleanVar(value=settings["human_mode"])
        self.loop_mode = tk.BooleanVar(value=settings["loop_mode"])
        self.fix_indent = tk.BooleanVar(value=settings["fix_indent"])
        self.typo_mode = tk.BooleanVar(value=settings["typo_mode"])
        self.typo_chance = tk.DoubleVar(value=settings["typo_chance"])

        # --- Top bar: label + Settings button + dark mode toggle ---
        top_bar = ttk.Frame(root)
        top_bar.pack(fill="x", padx=10, pady=(10, 0))
        self.label_text = ttk.Label(top_bar, text="Text to type:")
        self.label_text.pack(side="left")

        self.dark_check = ttk.Checkbutton(top_bar, text="Dark mode", variable=self.dark_mode,
                                           command=self.on_dark_mode_toggle)
        self.dark_check.pack(side="right")

        self.settings_btn = ttk.Button(top_bar, text="Settings", command=self.open_settings)
        self.settings_btn.pack(side="right", padx=(0, 10))

        # --- Text input with both scrollbars, no word-wrap ---
        text_frame = ttk.Frame(root)
        text_frame.pack(fill="both", expand=True, padx=10, pady=(4, 0))
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.text_box = tk.Text(text_frame, wrap="none", undo=True)
        self.text_box.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.text_box.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(text_frame, orient="horizontal", command=self.text_box.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")

        self.text_box.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(root, textvariable=self.status_var)
        self.status_label.pack(anchor="w", padx=10, pady=(8, 0))

        self.estimate_var = tk.StringVar(value="Estimated typing time: —")
        self.estimate_label = ttk.Label(root, textvariable=self.estimate_var)
        self.estimate_label.pack(anchor="w", padx=10, pady=(0, 0))

        # --- Buttons: Start / Stop / Clear ---
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="Start", command=self.start_typing)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop_typing, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.clear_btn = ttk.Button(btns, text="Clear", command=self.clear_text)
        self.clear_btn.pack(side="left")

        self.hint_label = ttk.Label(root, text="Tip: flick mouse to a screen corner anytime to abort.")
        self.hint_label.pack(anchor="w", padx=10, pady=(0, 8))

        self.apply_theme()
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # --- live time estimate: recalculate whenever text or settings change ---
        self.text_box.bind("<<Modified>>", self._on_text_modified)
        for var in (self.char_delay, self.human_mode, self.fix_indent,
                    self.typo_mode, self.typo_chance):
            var.trace_add("write", lambda *args: self.update_estimate())
        self.update_estimate()

        if pyautogui is None:
            messagebox.showwarning(
                "Missing dependency",
                "pyautogui isn't installed.\n\nRun this in a terminal:\n"
                "    pip install pyautogui\n\nthen restart this app."
            )

    def open_settings(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.settings_window = SettingsWindow(self)

    def clear_text(self):
        self.text_box.delete("1.0", "end")
        self.text_box.edit_modified(False)
        self.update_estimate()

    def _on_text_modified(self, event=None):
        self.text_box.edit_modified(False)  # reset flag so event fires again next edit
        self.update_estimate()

    def update_estimate(self):
        text = self.text_box.get("1.0", "end-1c")
        if not text:
            self.estimate_var.set("Estimated typing time: —")
            return

        try:
            base_delay = max(self.char_delay.get(), 0.0)
        except tk.TclError:
            base_delay = 0.05
        human = self.human_mode.get()
        fix_indent = self.fix_indent.get()
        typo_on = self.typo_mode.get()
        try:
            typo_chance = max(self.typo_chance.get(), 0.0)
        except tk.TclError:
            typo_chance = 0.0

        # average per-character delay, accounting for the occasional
        # longer "thinking" pause human mode adds (~3% chance, ~0.275s extra)
        avg_char_delay = base_delay + (0.03 * 0.275 if human else 0.0)

        n_chars = len(text.replace("\n", ""))
        n_lines = text.count("\n")

        base_seconds = n_chars * avg_char_delay
        # newline overhead: matches the pause after each Enter in the typing loop
        line_seconds = n_lines * (base_delay + (0.02 if fix_indent else 0.0))

        typo_seconds = 0.0
        if typo_on:
            words = re.findall(r"\S+", text)
            eligible = [w for w in words if len(w) >= 3]
            expected_typos = len(eligible) * (typo_chance / 100.0)
            # extra: one wrong char + noticing pause (~0.275s avg) + one backspace
            typo_seconds = expected_typos * (2 * avg_char_delay + 0.275)

        total = base_seconds + line_seconds + typo_seconds
        self.estimate_var.set(f"Estimated typing time: ~{format_duration(total)}")

    def on_dark_mode_toggle(self):
        self.apply_theme()
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.apply_theme()
        self.save_all_settings()

    def save_all_settings(self):
        save_settings({
            "dark_mode": self.dark_mode.get(),
            "start_delay": self.start_delay.get(),
            "char_delay": self.char_delay.get(),
            "human_mode": self.human_mode.get(),
            "loop_mode": self.loop_mode.get(),
            "fix_indent": self.fix_indent.get(),
            "typo_mode": self.typo_mode.get(),
            "typo_chance": self.typo_chance.get(),
        })

    def on_close(self):
        self.save_all_settings()
        self.root.destroy()

    def apply_theme(self):
        c = DARK if self.dark_mode.get() else LIGHT

        self.root.configure(bg=c["bg"])
        self.style.configure("TFrame", background=c["bg"])
        self.style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        self.style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
        self.style.configure("TButton", background=c["bg"], foreground=c["fg"])
        self.style.configure("TSpinbox", fieldbackground=c["text_bg"], foreground=c["text_fg"])

        self.text_box.configure(bg=c["text_bg"], fg=c["text_fg"], insertbackground=c["fg"])
        self.status_label.configure(foreground=c["status_fg"])
        self.hint_label.configure(foreground=c["hint_fg"])

    def start_typing(self):
        if pyautogui is None:
            messagebox.showerror("Missing dependency", "Install pyautogui first (pip install pyautogui).")
            return

        text = self.text_box.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Nothing to type", "Type or paste something in the box first.")
            return

        pyautogui.FAILSAFE = pyautogui_failsafe

        self.stop_flag.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        self.typing_thread = threading.Thread(
            target=self._type_worker, args=(text,), daemon=True
        )
        self.typing_thread.start()

    def stop_typing(self):
        self.stop_flag.set()
        self.status_var.set("Stopping...")

    def _char_delay_value(self, base_delay, human):
        d = base_delay
        if human:
            d = max(0.0, random.gauss(base_delay, base_delay * 0.5 + 0.01))
            if random.random() < 0.03:  # occasional longer "thinking" pause
                d += random.uniform(0.15, 0.4)
        return d

    def _type_word_with_possible_typo(self, word, base_delay, human, typo_on, typo_chance):
        """Types a word normally, or (occasionally) mistypes one character,
        pauses, backspaces it, then retypes it correctly - for realism."""
        make_typo = (
            typo_on
            and len(word) >= 3
            and random.random() < (typo_chance / 100.0)
        )

        if not make_typo:
            for ch in word:
                if self.stop_flag.is_set():
                    return False
                pyautogui.write(ch)
                time.sleep(self._char_delay_value(base_delay, human))
            return True

        # pick a position (not the very first char) to fumble
        typo_index = random.randint(1, len(word) - 1)

        # type the correct prefix
        for ch in word[:typo_index]:
            if self.stop_flag.is_set():
                return False
            pyautogui.write(ch)
            time.sleep(self._char_delay_value(base_delay, human))

        # type a wrong character
        wrong_char = random.choice(TYPO_CHARS)
        pyautogui.write(wrong_char)
        time.sleep(self._char_delay_value(base_delay, human))

        # brief pause, like noticing the mistake
        time.sleep(random.uniform(0.15, 0.4))

        # backspace it out
        pyautogui.press("backspace")
        time.sleep(self._char_delay_value(base_delay, human))

        # type the rest correctly, starting from the fumbled character
        for ch in word[typo_index:]:
            if self.stop_flag.is_set():
                return False
            pyautogui.write(ch)
            time.sleep(self._char_delay_value(base_delay, human))

        return True

    def _type_worker(self, text):
        try:
            delay = self.start_delay.get()
            for remaining in range(int(delay), 0, -1):
                if self.stop_flag.is_set():
                    self._finish("Stopped.")
                    return
                self.status_var.set(f"Starting in {remaining}s — click into your target window!")
                time.sleep(1)

            base_delay = max(self.char_delay.get(), 0.0)
            human = self.human_mode.get()
            fix_indent = self.fix_indent.get()
            typo_on = self.typo_mode.get()
            typo_chance = self.typo_chance.get()
            lines = text.split("\n")

            start_time = time.time()

            while True:
                self.status_var.set("Typing...")
                for i, line in enumerate(lines):
                    if self.stop_flag.is_set():
                        self._finish("Stopped.")
                        return

                    if i > 0:
                        # New line: press Enter, then strip whatever
                        # auto-indent the editor inserted before typing
                        # our own (correct) leading whitespace.
                        pyautogui.press("enter")
                        if fix_indent:
                            time.sleep(0.02)
                            pyautogui.hotkey("shift", "home")
                            pyautogui.press("delete")
                        time.sleep(base_delay)

                    # split line into words vs whitespace, preserving exact spacing
                    tokens = re.split(r"(\s+)", line)
                    for token in tokens:
                        if self.stop_flag.is_set():
                            self._finish("Stopped.")
                            return
                        if token == "":
                            continue
                        if token.isspace():
                            # whitespace runs typed plainly, no typo simulation
                            for ch in token:
                                pyautogui.write(ch)
                                time.sleep(self._char_delay_value(base_delay, human))
                        else:
                            ok = self._type_word_with_possible_typo(
                                token, base_delay, human, typo_on, typo_chance
                            )
                            if not ok:
                                return

                if not self.loop_mode.get() or self.stop_flag.is_set():
                    break
                time.sleep(1)

            elapsed = time.time() - start_time
            self._finish(f"Done in {format_duration(elapsed)}.")
        except pyautogui.FailSafeException:
            self._finish("Aborted (mouse hit screen corner).")
        except Exception as e:
            self._finish(f"Error: {e}")

    def _finish(self, msg):
        self.status_var.set(msg)
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = AutoTyperApp(root)
    root.mainloop()
