"""
Auto Typer - types out text for you, human-style
--------------------------------------------------
Requires: pyautogui  (install with: pip install pyautogui)

How it works:
1. Paste/write the text you want typed into the box.
2. Set a "start delay" - time to click into the target window
   (browser, doc, chat box, whatever) before typing begins.
3. Set typing speed + how "human" it should look (random pauses,
   occasional typos that get backspaced and fixed).
4. Hit Start. Move your mouse to the top-left corner of the screen
   at ANY time to abort instantly (pyautogui failsafe).
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


def load_settings():
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass  # non-critical, just skip saving if it fails


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        root.title("Auto Typer")
        root.geometry("700x680")
        root.minsize(560, 560)

        self.typing_thread = None
        self.stop_flag = threading.Event()

        settings = load_settings()
        self.dark_mode = tk.BooleanVar(value=settings.get("dark_mode", False))

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass

        pad = {"padx": 10, "pady": 6}

        # --- Top bar: label + dark mode toggle ---
        top_bar = ttk.Frame(root)
        top_bar.pack(fill="x", padx=10, pady=(10, 0))
        self.label_text = ttk.Label(top_bar, text="Text to type:")
        self.label_text.pack(side="left")
        self.dark_check = ttk.Checkbutton(top_bar, text="Dark mode", variable=self.dark_mode,
                                           command=self.on_dark_mode_toggle)
        self.dark_check.pack(side="right")

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

        # --- Options frame ---
        opts = ttk.Frame(root)
        opts.pack(fill="x", **pad)

        ttk.Label(opts, text="Start delay (sec):").grid(row=0, column=0, sticky="w")
        self.start_delay = tk.DoubleVar(value=5.0)
        ttk.Spinbox(opts, from_=0, to=60, increment=0.5, textvariable=self.start_delay,
                    width=6).grid(row=0, column=1, padx=(4, 20))

        ttk.Label(opts, text="Base delay/char (sec):").grid(row=0, column=2, sticky="w")
        self.char_delay = tk.DoubleVar(value=0.05)
        ttk.Spinbox(opts, from_=0.0, to=1.0, increment=0.01, textvariable=self.char_delay,
                    width=6).grid(row=0, column=3, padx=4)

        self.human_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Human-like variation (random pauses)",
                         variable=self.human_mode).grid(row=1, column=0, columnspan=2,
                                                         sticky="w", pady=(8, 0))

        self.loop_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Repeat / loop", variable=self.loop_mode).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=(8, 0))

        self.fix_indent = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opts,
            text="Fix editor auto-indent (recommended for VS Code / IDEs)",
            variable=self.fix_indent
        ).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 0))

        self.typo_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opts,
            text="Simulate typos (randomly misspell a word, then backspace + fix it)",
            variable=self.typo_mode
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Label(opts, text="Typo chance (%):").grid(row=3, column=2, sticky="w", pady=(4, 0))
        self.typo_chance = tk.DoubleVar(value=6.0)
        ttk.Spinbox(opts, from_=0, to=100, increment=1, textvariable=self.typo_chance,
                    width=6).grid(row=3, column=3, padx=4, pady=(4, 0))

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready.")
        self.status_label = ttk.Label(root, textvariable=self.status_var)
        self.status_label.pack(anchor="w", padx=10, pady=(4, 0))

        self.estimate_var = tk.StringVar(value="Estimated typing time: —")
        self.estimate_label = ttk.Label(root, textvariable=self.estimate_var)
        self.estimate_label.pack(anchor="w", padx=10, pady=(0, 0))

        # --- Buttons ---
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="Start", command=self.start_typing)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop_typing, state="disabled")
        self.stop_btn.pack(side="left")

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
            typo_chance = self.typo_chance.get() / 100.0
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
            expected_typos = len(eligible) * typo_chance
            # extra: one wrong char + noticing pause (~0.275s avg) + one backspace
            typo_seconds = expected_typos * (2 * avg_char_delay + 0.275)

        total = base_seconds + line_seconds + typo_seconds

        if total < 60:
            self.estimate_var.set(f"Estimated typing time: ~{total:.1f}s")
        else:
            mins = int(total // 60)
            secs = total % 60
            self.estimate_var.set(f"Estimated typing time: ~{mins}m {secs:.0f}s")

    def on_dark_mode_toggle(self):
        self.apply_theme()
        save_settings({"dark_mode": self.dark_mode.get()})

    def on_close(self):
        save_settings({"dark_mode": self.dark_mode.get()})
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
            self._finish(f"Done in {elapsed:.1f}s.")
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