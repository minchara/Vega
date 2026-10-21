"""Vega: a push-to-talk and optional wake-word Windows desktop assistant."""

from __future__ import annotations

import os
import queue
import re
import threading
import time
import tkinter as tk
import urllib.parse
import webbrowser
from tkinter import messagebox, ttk


APP_NAME = "Vega"


def optional_modules():
    missing = []
    for module in ("speech_recognition", "pyttsx3", "pyautogui", "pyperclip"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    return missing


class VegaAssistant:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vega Voice Assistant")
        self.root.geometry("620x540")
        self.root.minsize(540, 450)
        self.root.configure(bg="#f5f6fa")
        self.events: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.busy = False
        self.pending_command = False
        self.command_from_wake = False
        self.wake_enabled = False
        self.wake_stop_listening = None
        self.speech = None
        self.tts = None
        self.pyautogui = None
        self.pyperclip = None
        self._build_ui()
        self._load_optional_dependencies()
        self.root.after(100, self._poll_events)

    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 10), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=11)

        outer = tk.Frame(self.root, bg="#f5f6fa", padx=24, pady=20)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="Vega", font=("Segoe UI", 25, "bold"), fg="#252a40", bg="#f5f6fa").pack(anchor="w")
        tk.Label(outer, text="Your voice-controlled computer helper", font=("Segoe UI", 11), fg="#68708a", bg="#f5f6fa").pack(anchor="w", pady=(0, 16))

        self.status_var = tk.StringVar(value="Ready · press the microphone button to speak")
        tk.Label(outer, textvariable=self.status_var, font=("Segoe UI", 10), fg="#39415b", bg="#e8ebf5", padx=12, pady=10, anchor="w").pack(fill="x")

        buttons = tk.Frame(outer, bg="#f5f6fa")
        buttons.pack(fill="x", pady=12)
        self.listen_button = ttk.Button(buttons, text="🎙  Listen", style="Accent.TButton", command=self.start_listening)
        self.listen_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="■  Stop / cancel", command=self.stop_action, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))
        self.run_button = ttk.Button(buttons, text="Run command", command=self.run_command, state="disabled")
        self.run_button.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Mute voice", command=self.toggle_mute).pack(side="right")
        self.muted = False
        self.wake_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(outer, text='Hands-free wake word: “Hey Vega”', variable=self.wake_var, command=self._toggle_wake).pack(anchor="w", pady=(0, 10))

        tk.Label(outer, text="I heard", font=("Segoe UI", 10, "bold"), fg="#39415b", bg="#f5f6fa").pack(anchor="w", pady=(3, 5))
        self.transcript = tk.Text(outer, height=4, wrap="word", font=("Segoe UI", 11), relief="solid", bd=1, padx=10, pady=8)
        self.transcript.pack(fill="x")
        self.transcript.insert("1.0", "Your recognized command will appear here.")

        tk.Label(outer, text="Current action", font=("Segoe UI", 10, "bold"), fg="#39415b", bg="#f5f6fa").pack(anchor="w", pady=(14, 5))
        self.action_var = tk.StringVar(value="None")
        tk.Label(outer, textvariable=self.action_var, font=("Segoe UI", 10), fg="#39415b", bg="white", padx=10, pady=10, anchor="w", relief="solid", bd=1).pack(fill="x")

        tk.Label(outer, text="Try: “Open ChatGPT” · “Search for weather” · “Type hello there” · “Send” · “Stop”", font=("Segoe UI", 9), fg="#68708a", bg="#f5f6fa", wraplength=560, justify="left").pack(anchor="w", pady=(16, 0))

    def _load_optional_dependencies(self):
        missing = optional_modules()
        if missing:
            self._set_status("Setup needed · install the packages listed in requirements.txt")
            self._set_action("Speech and computer-control packages are not installed yet.")
            return
        import pyautogui
        import pyperclip
        import pyttsx3
        import speech_recognition as sr
        self.speech = sr
        self.pyautogui = pyautogui
        self.pyperclip = pyperclip
        try:
            self.tts = pyttsx3.init()
            self.tts.setProperty("rate", 175)
        except Exception:
            self.tts = None
        self._set_status("Ready · push-to-talk is active")
        self._set_action("Waiting for a voice command.")

    def start_listening(self):
        if self.busy:
            return
        if not self.speech:
            messagebox.showinfo("Setup needed", "Install the packages in requirements.txt, then restart Vega.")
            return
        self._pause_wake_listener()
        self.busy = True
        self.stop_event.clear()
        self.listen_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self._set_status("Listening · speak a command, then pause")
        self._set_action("Waiting for speech…")
        threading.Thread(target=self._recognize, daemon=True).start()

    def _recognize(self):
        recognizer = self.speech.Recognizer()
        try:
            with self.speech.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
            if self.stop_event.is_set():
                self.events.put(("done", "Cancelled."))
                return
            self.events.put(("status", "Transcribing speech…"))
            # Google Web Speech performs transcription online. Vega does not save audio locally.
            phrase = recognizer.recognize_google(audio)
            if self.stop_event.is_set():
                self.events.put(("done", "Cancelled."))
                return
            if phrase.lower().strip(" .!?") in {"stop", "cancel", "stop listening", "cancel that", "never mind"}:
                self.events.put(("command", phrase))
            else:
                self.events.put(("transcript", phrase))
        except self.speech.WaitTimeoutError:
            self.events.put(("error", "I didn’t hear a command. Press Listen and try again."))
        except self.speech.UnknownValueError:
            self.events.put(("error", "I couldn’t make that out. Please try again."))
        except self.speech.RequestError as exc:
            self.events.put(("error", f"Speech recognition is unavailable: {exc}"))
        except OSError as exc:
            self.events.put(("error", f"Microphone unavailable: {exc}"))
        except Exception as exc:
            self.events.put(("error", f"Could not listen: {exc}"))

    def _poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "status":
                    self._set_status(value)
                elif kind == "transcript":
                    self.transcript.delete("1.0", "end")
                    self.transcript.insert("1.0", value)
                    self.pending_command = True
                    self.run_button.configure(state="normal")
                    self._set_status("Review or edit the command, then choose Run command")
                    self._set_action("Waiting for your approval")
                    if self.command_from_wake:
                        self.command_from_wake = False
                        self._set_status("Hey Vega · carrying out the recognized command")
                        self.root.after(250, self.run_command)
                elif kind == "command":
                    self._handle_command(value)
                elif kind == "error":
                    self._finish(value, speak=True)
                elif kind == "done":
                    self._finish(value)
                elif kind == "wake_error":
                    self._set_status("Wake-word recognition needs an internet connection · wake listening remains on")
                elif kind == "wake":
                    self._wake_detected(value)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_command(self, raw: str):
        text = raw.strip()
        low = text.lower().strip(" .!?\n")
        if low in {"stop", "cancel", "stop listening", "cancel that", "never mind"}:
            self._finish("Cancelled.")
            return

        if low in {"close", "close this", "close window", "close the window", "close app", "close the app"}:
            self._set_action("Close the active window")
            if messagebox.askyesno("Close active window?", "Close the currently active window?"):
                self._run_in_target(lambda: self.pyautogui.hotkey("alt", "f4"), "Pressed Alt+F4 for the active window.")
            else:
                self._finish("Kept the window open.")
            return

        open_match = re.match(r"^(?:please\s+)?(?:open|launch|start)\s+(.+?)\s*$", text, re.I)
        if open_match:
            target = open_match.group(1).strip(" .")
            self._set_action(f"Opening {target}")
            urls = {"chatgpt": "https://chatgpt.com", "google": "https://www.google.com", "youtube": "https://www.youtube.com", "gmail": "https://mail.google.com"}
            if target.lower() in urls:
                webbrowser.open(urls[target.lower()])
                self._finish(f"Opened {target} in your browser.", speak=True)
            elif re.match(r"^(https?://|www\.)", target, re.I):
                webbrowser.open(target if target.lower().startswith("http") else "https://" + target)
                self._finish("Opened the website in your browser.", speak=True)
            else:
                try:
                    os.startfile(target)
                    self._finish(f"Opened {target}.", speak=True)
                except Exception:
                    webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(target))
                    self._finish(f"I couldn’t find an app named {target}, so I searched for it online.", speak=True)
            return

        search_match = re.match(r"^(?:please\s+)?(?:search(?:\s+the\s+web)?\s+for|google|look\s+up)\s+(.+)$", text, re.I)
        if search_match:
            query = search_match.group(1).strip()
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query))
            self._finish(f"Searching the web for {query}.", speak=True)
            return

        if low in {"new tab", "open a new tab"}:
            self._run_in_target(lambda: self.pyautogui.hotkey("ctrl", "t"), "Opened a new tab.")
            return
        if low in {"go back", "back"}:
            self._run_in_target(lambda: self.pyautogui.hotkey("alt", "left"), "Went back.")
            return
        if low in {"scroll down", "scroll up"}:
            self._run_in_target(lambda: self.pyautogui.scroll(-5 if low == "scroll down" else 5), "Scrolled " + low.removeprefix("scroll ") + ".")
            return
        if low in {"copy that", "copy"}:
            self._run_in_target(lambda: self.pyautogui.hotkey("ctrl", "c"), "Copied the selection.")
            return
        if low == "paste":
            self._run_in_target(lambda: self.pyautogui.hotkey("ctrl", "v"), "Pasted.")
            return

        if low == "send" or low in {"submit", "send it", "submit it"}:
            self._set_action("Send from the currently focused app")
            if messagebox.askyesno("Send now?", "Press Enter in the currently focused app? Check that the right destination and content are active."):
                self._run_in_target(lambda: self.pyautogui.press("enter"), "Pressed Enter. Check the active app to confirm it was sent.")
            else:
                self._finish("Nothing was sent.")
            return

        type_match = re.match(r"^(?:please\s+)?(?:type|write|enter|dictate)(?:\s*[:,-]?\s+)(.+)$", text, re.I | re.S)
        if type_match:
            content = type_match.group(1).strip()
            if re.search(r"\s+(?:and\s+)?send\s*$", content, re.I):
                content = re.sub(r"\s+(?:and\s+)?send\s*$", "", content, flags=re.I).strip()
                self._set_action("Type dictated text, then send")
                if messagebox.askyesno("Send dictated text?", f"Send this text in the active app?\n\n{content}"):
                    self._run_in_target(lambda: (self._type_text(content), self.pyautogui.press("enter")), "Pressed Enter. Check the active app to confirm the text was sent.")
                else:
                    self._run_in_target(lambda: self._type_text(content), "Text was typed but not sent.")
            else:
                self._run_in_target(lambda: self._type_text(content), "Typed your text in the active app.")
            return

        if low in {"read this aloud", "read aloud"}:
            self._set_action("Reading selected text aloud")
            self._read_selection()
            return
        self._finish("I’m not sure what action you want. Try “open ChatGPT,” “search for…,” or “type…” .", speak=True)

    def run_command(self):
        if not self.pending_command:
            return
        command = self.transcript.get("1.0", "end").strip()
        self.pending_command = False
        self.run_button.configure(state="disabled")
        self.busy = True
        self._handle_command(command)

    def _type_text(self, content: str):
        self._set_action("Typing in the currently focused app")
        old_clipboard = self.pyperclip.paste()
        self.pyperclip.copy(content)
        self.pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        self.pyperclip.copy(old_clipboard)

    def _run_in_target(self, action, result_message: str):
        """Temporarily minimize Mini so keyboard and mouse input reaches the prior app."""
        self.busy = True
        self.listen_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.root.iconify()

        def perform():
            try:
                action()
            except Exception as exc:
                result = f"The action failed: {exc}"
            else:
                result = result_message
            self.root.deiconify()
            self._finish(result, speak=True)

        self.root.after(350, perform)

    def _read_selection(self):
        self.busy = True
        self.listen_button.configure(state="disabled")
        self.stop_button.configure(state="disabled")
        self.root.iconify()

        def copy_selection():
            try:
                self.pyautogui.hotkey("ctrl", "c")
                self.root.after(250, finish_reading)
            except Exception as exc:
                self.root.deiconify()
                self._finish(f"Could not read selected text: {exc}", speak=True)

        def finish_reading():
            selected_text = self.pyperclip.paste().strip()
            self.root.deiconify()
            self._finish("Reading the selected text aloud." if selected_text else "I didn’t find any selected text to read.", speak=not bool(selected_text))
            if selected_text and not self.muted and self.tts:
                threading.Thread(target=self._speak, args=(selected_text,), daemon=True).start()

        self.root.after(350, copy_selection)

    def stop_action(self):
        self.stop_event.set()
        self._pause_wake_listener()
        if self.pending_command:
            self._finish("Cancelled.")
            return
        self._set_status("Stopping…")
        self._set_action("Cancel requested")
        # Recognition returns from its bounded microphone wait before the app is re-enabled.

    def toggle_mute(self):
        self.muted = not self.muted
        if self.tts:
            self.tts.stop()
        self._set_status("Voice replies muted" if self.muted else "Voice replies unmuted")

    def _finish(self, message: str, speak: bool = False):
        self.busy = False
        self.pending_command = False
        self.run_button.configure(state="disabled")
        self.listen_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._set_status(message)
        if speak and not self.muted and self.tts:
            threading.Thread(target=self._speak, args=(message,), daemon=True).start()
        if self.wake_enabled:
            self.root.after(500, self._start_wake_listener)

    def _toggle_wake(self):
        if self.wake_var.get():
            if not self.speech:
                self.wake_var.set(False)
                messagebox.showinfo("Setup needed", "Install the packages in requirements.txt, then restart Vega.")
                return
            accepted = messagebox.askyesno(
                "Enable Hey Vega?",
                "Hands-free wake listening sends short speech clips to Google for recognition so Vega can detect “Hey Vega.” Vega does not save recordings. Enable continuous microphone listening?",
            )
            if not accepted:
                self.wake_var.set(False)
                return
            self.wake_enabled = True
            self._start_wake_listener()
        else:
            self.wake_enabled = False
            self._pause_wake_listener()
            self._set_status("Wake word off · press Listen when you want to speak")

    def _start_wake_listener(self):
        if not self.wake_enabled or self.busy or self.pending_command or self.wake_stop_listening or not self.speech:
            return
        recognizer = self.speech.Recognizer()

        def on_phrase(recognizer_instance, audio):
            try:
                phrase = recognizer_instance.recognize_google(audio).strip()
            except self.speech.UnknownValueError:
                return
            except self.speech.RequestError:
                self.events.put(("wake_error", None))
                return
            match = re.match(r"^\s*hey\s+vega\b[\s,.:;!?—-]*(.*)$", phrase, re.I)
            if not match:
                return
            remainder = match.group(1).strip()
            stop = self.wake_stop_listening
            self.wake_stop_listening = None
            if stop:
                stop(wait_for_stop=False)
            self.events.put(("wake", remainder))

        try:
            source = self.speech.Microphone()
            self.wake_stop_listening = recognizer.listen_in_background(source, on_phrase, phrase_time_limit=5)
            self._set_status("Listening for “Hey Vega” · say it to wake me")
        except Exception as exc:
            self.wake_enabled = False
            self.wake_var.set(False)
            self._set_status(f"Wake listening unavailable: {exc}")

    def _pause_wake_listener(self):
        stop = self.wake_stop_listening
        self.wake_stop_listening = None
        if stop:
            try:
                stop(wait_for_stop=False)
            except Exception:
                pass

    def _wake_detected(self, remainder: str):
        if not self.wake_enabled:
            return
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(800, lambda: self.root.attributes("-topmost", False))
        if remainder:
            self.transcript.delete("1.0", "end")
            self.transcript.insert("1.0", remainder)
            self.pending_command = True
            self.run_button.configure(state="normal")
            self._set_status("Hey Vega · review or edit the command, then choose Run command")
            self._set_action("Command ready")
            self.command_from_wake = True
            self._set_status("Hey Vega · carrying out the recognized command")
            self.root.after(250, self.run_command)
        else:
            self._set_status("Hey Vega · what can I do for you?")
            self.command_from_wake = True
            self.root.after(500, self.start_listening)

    def _speak(self, message: str):
        try:
            self.tts.say(message)
            self.tts.runAndWait()
        except Exception:
            pass

    def _set_status(self, text: str):
        self.status_var.set(text)

    def _set_action(self, text: str):
        self.action_var.set(text)


def main():
    root = tk.Tk()
    VegaAssistant(root)
    root.mainloop()


if __name__ == "__main__":
    main()

