"""
Auto Typer - types out text for you, human-style
--------------------------------------------------
Requires: pyautogui  (install with: pip install pyautogui)

How it works:
1. Paste/write the text you want typed into the box.
2. Set a "start delay" - time to click into the target window
   (browser, doc, chat box, whatever) before typing begins.
3. Set typing speed + how "human" it should look (random pauses,
   occasional slightly-varied timing).
4. Hit Start. Move your mouse to the top-left corner of the screen
   at ANY time to abort instantly (pyautogui failsafe).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random

try:
    import pyautogui
except ImportError:
    pyautogui = None

pyautogui_failsafe = True  # moving mouse to screen corner aborts typing


class AutoTyperApp:
    def __init__(self, root):
        self.root = root
        root.title("Auto Typer")
        root.geometry("520x480")
        root.resizable(False, False)

        self.typing_thread = None
        self.stop_flag = threading.Event()

        pad = {"padx": 10, "pady": 6}

        # --- Text input ---
        ttk.Label(root, text="Text to type:").pack(anchor="w", **pad)
        self.text_box = tk.Text(root, height=10, wrap="word")
        self.text_box.pack(fill="both", expand=True, padx=10)

        # --- Options frame ---
        opts = ttk.Frame(root)
        opts.pack(fill="x", **pad)

        # Start delay
        ttk.Label(opts, text="Start delay (sec):").grid(row=0, column=0, sticky="w")
        self.start_delay = tk.DoubleVar(value=5.0)
        ttk.Spinbox(opts, from_=0, to=60, increment=0.5, textvariable=self.start_delay,
                    width=6).grid(row=0, column=1, padx=(4, 20))

        # Typing speed
        ttk.Label(opts, text="Base delay/char (sec):").grid(row=0, column=2, sticky="w")
        self.char_delay = tk.DoubleVar(value=0.05)
        ttk.Spinbox(opts, from_=0.0, to=1.0, increment=0.01, textvariable=self.char_delay,
                    width=6).grid(row=0, column=3, padx=4)

        # Human-like variation
        self.human_mode = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Human-like variation (random pauses)",
                         variable=self.human_mode).grid(row=1, column=0, columnspan=2,
                                                         sticky="w", pady=(8, 0))

        # Loop
        self.loop_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Repeat / loop", variable=self.loop_mode).grid(
            row=1, column=2, columnspan=2, sticky="w", pady=(8, 0))

        # --- Status ---
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(root, textvariable=self.status_var, foreground="gray").pack(
            anchor="w", padx=10, pady=(4, 0))

        # --- Buttons ---
        btns = ttk.Frame(root)
        btns.pack(fill="x", **pad)
        self.start_btn = ttk.Button(btns, text="Start", command=self.start_typing)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop_typing, state="disabled")
        self.stop_btn.pack(side="left")

        ttk.Label(root, text="Tip: flick mouse to a screen corner anytime to abort.",
                  foreground="gray").pack(anchor="w", padx=10, pady=(0, 8))

        if pyautogui is None:
            messagebox.showwarning(
                "Missing dependency",
                "pyautogui isn't installed.\n\nRun this in a terminal:\n"
                "    pip install pyautogui\n\nthen restart this app."
            )

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

            while True:
                self.status_var.set("Typing...")
                for ch in text:
                    if self.stop_flag.is_set():
                        self._finish("Stopped.")
                        return

                    d = base_delay
                    if human:
                        d = max(0.0, random.gauss(base_delay, base_delay * 0.5 + 0.01))
                        if random.random() < 0.03:  # occasional longer "thinking" pause
                            d += random.uniform(0.15, 0.4)

                    pyautogui.write(ch)
                    time.sleep(d)

                if not self.loop_mode.get() or self.stop_flag.is_set():
                    break
                time.sleep(1)

            self._finish("Done.")
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
