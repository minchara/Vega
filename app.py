"""Local Python service for the Vega JavaScript voice-assistant page."""

from __future__ import annotations

import hmac
import json
import re
import secrets
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import pyautogui
import pyperclip
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field


HOST = "127.0.0.1"
PORT = 8765
BASE_URL = f"http://{HOST}:{PORT}"
ROOT = Path(__file__).resolve().parent
API_TOKEN = secrets.token_urlsafe(32)
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class CommandRequest(BaseModel):
    command: str = Field(min_length=1, max_length=1000)


@app.get("/", response_class=HTMLResponse)
def home():
    page = (ROOT / "index.html").read_text(encoding="utf-8")
    page = page.replace("__VEGA_TOKEN__", json.dumps(API_TOKEN))
    return HTMLResponse(page)


@app.post("/api/command")
async def execute_command(body: CommandRequest, request: Request):
    origin = request.headers.get("origin", "")
    token = request.headers.get("x-vega-token", "")
    client_host = request.client.host if request.client else ""
    if origin != BASE_URL or client_host not in {"127.0.0.1", "::1"} or not hmac.compare_digest(token, API_TOKEN):
        raise HTTPException(status_code=403, detail="This local Vega page is not authorized to control the computer.")
    try:
        return run_command(body.command.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"The requested action failed: {exc}") from exc


def _in_previous_window(action, *, return_to_vega: bool = True):
    """Send input to the window behind the browser tab running Vega."""
    pyautogui.hotkey("alt", "tab")
    time.sleep(0.35)
    try:
        return action()
    finally:
        if return_to_vega:
            time.sleep(0.1)
            pyautogui.hotkey("alt", "tab")


def _type_text(text: str):
    previous_clipboard = pyperclip.paste()
    try:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
    finally:
        pyperclip.copy(previous_clipboard)


def run_command(command: str) -> dict[str, str]:
    text = command.strip()
    low = text.lower().strip(" .!?\n")

    if low in {"stop", "cancel", "stop listening", "cancel that", "never mind"}:
        return {"message": "Stopped listening."}

    open_match = re.match(r"^(?:please\s+)?(?:open|launch|start)\s+(.+?)\s*$", text, re.I)
    if open_match:
        target = open_match.group(1).strip(" .")
        known_sites = {
            "chatgpt": "https://chatgpt.com",
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
        }
        if target.lower() in known_sites:
            webbrowser.open(known_sites[target.lower()], new=2)
        elif re.match(r"^(?:https?://|www\.)", target, re.I):
            webbrowser.open(target if target.lower().startswith("http") else "https://" + target, new=2)
        else:
            webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(target), new=2)
        return {"message": f"Opening {target} in your browser."}

    search_match = re.match(r"^(?:please\s+)?(?:search(?:\s+the\s+web)?\s+for|google|look\s+up)\s+(.+)$", text, re.I)
    if search_match:
        query = search_match.group(1).strip()
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote(query), new=2)
        return {"message": f"Searching the web for {query}."}

    type_match = re.match(r"^(?:please\s+)?(?:type|write|enter|dictate)(?:\s*[:,-]?\s+)(.+)$", text, re.I | re.S)
    if type_match:
        content = type_match.group(1).strip()
        send = bool(re.search(r"\s+(?:and\s+)?send\s*$", content, re.I))
        if send:
            content = re.sub(r"\s+(?:and\s+)?send\s*$", "", content, flags=re.I).strip()

        def type_and_maybe_send():
            _type_text(content)
            if send:
                pyautogui.press("enter")

        _in_previous_window(type_and_maybe_send)
        if send:
            return {"message": "Pressed Enter. Check the active app to confirm the text was sent."}
        return {"message": "Typed the dictated text in the previously active window."}

    if low in {"send", "send it", "submit", "submit it"}:
        _in_previous_window(lambda: pyautogui.press("enter"))
        return {"message": "Pressed Enter. Check the active app to confirm it was sent."}

    if low in {"close", "close this", "close window", "close the window", "close app", "close the app"}:
        _in_previous_window(lambda: pyautogui.hotkey("alt", "f4"), return_to_vega=False)
        return {"message": "Pressed Alt+F4 for the previously active window."}

    actions = {
        "new tab": lambda: pyautogui.hotkey("ctrl", "t"),
        "open a new tab": lambda: pyautogui.hotkey("ctrl", "t"),
        "go back": lambda: pyautogui.hotkey("alt", "left"),
        "back": lambda: pyautogui.hotkey("alt", "left"),
        "scroll down": lambda: pyautogui.scroll(-5),
        "scroll up": lambda: pyautogui.scroll(5),
        "copy": lambda: pyautogui.hotkey("ctrl", "c"),
        "copy that": lambda: pyautogui.hotkey("ctrl", "c"),
        "paste": lambda: pyautogui.hotkey("ctrl", "v"),
    }
    if low in actions:
        _in_previous_window(actions[low])
        return {"message": f"Done: {low}."}

    if low in {"read this aloud", "read aloud"}:
        def copy_selection():
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.2)
            return pyperclip.paste().strip()

        selected = _in_previous_window(copy_selection)
        return {"message": "Reading the selected text." if selected else "I didn't find selected text to read.", "speak": selected}

    raise ValueError("I didn't recognize that command. Try open, search, type, send, close, or stop.")


if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open(BASE_URL)).start()
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning", access_log=False)
