# Vega Voice Assistant

Vega is a Windows desktop assistant for voice-driven browser and keyboard tasks. It supports push-to-talk and an optional **“Hey Vega”** wake word. When the wake phrase is detected, Vega brings its window forward and processes the recognized command. Sending and closing an active window require an on-screen confirmation.

## Run from source

1. Install Python 3.10 or newer and allow desktop apps to use your microphone in Windows Privacy settings.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Launch `Run-Vega.bat` or run `python vega_assistant.py`.

## Build a portable Windows app

Install PyInstaller with `python -m pip install pyinstaller`, then run:

```powershell
pyinstaller --noconfirm --clean --windowed --name Vega --hidden-import=speech_recognition --hidden-import=pyttsx3 --hidden-import=pyttsx3.drivers.sapi5 --hidden-import=pyautogui --hidden-import=pyperclip --hidden-import=pyaudio --collect-all=pyttsx3 --collect-all=comtypes vega_assistant.py
```

The runnable folder will be `dist/Vega`. Zip that folder to share the portable build. The receiver does not need Python installed.

## Speech and privacy

Vega uses Google Web Speech through SpeechRecognition for transcription. Push-to-talk audio is sent to Google's recognition service when you speak. Optional wake listening is off until enabled; when active, it continuously sends short speech clips to Google to detect “Hey Vega.” Vega does not save recordings or transcripts. Internet is required for speech recognition and web searches. Spoken responses use the installed Windows voice.

## Commands

- “Open ChatGPT”, “open Gmail”, “open YouTube”, or “open [website]”
- “Search for [query]”, “Google [query]”, or “look up [query]”
- “Type [dictated text]”
- “Read this aloud” reads the currently selected text
- “Type [dictated text] and send” (asks before sending)
- “Send” or “submit” (asks before pressing Enter in the active app)
- “Open a new tab”, “go back”, “scroll down”, “copy”, “paste”, and “close”
- “Stop” or “cancel” to cancel the current listening request

Push-to-talk shows the transcript for editing before you choose **Run command**. Wake-word commands run after recognition; send and close still show a confirmation. Keyboard actions minimize Vega briefly so they reach the previously active app. Check that app before using type, paste, or send; Vega cannot confirm message delivery.

## Current limits

- Wake-word detection requires internet and is opt-in; turn it off by unchecking its setting.
- Speech recognition is online; offline recognition needs a separate model and engine.
- The Stop button cancels speech recognition after its current microphone read returns (up to about 12 seconds); it does not interrupt a keyboard action already in progress.
- Credentials, logs, and persistent transcript storage are not implemented.

