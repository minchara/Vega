# Vega Voice Assistant

Vega is a Windows desktop assistant for voice-driven browser and keyboard tasks. Push-to-talk is available by default. To wake it by saying **“Hey Vega,”** turn on the hands-free wake-word checkbox and accept the microphone and privacy notice. When Vega hears the wake phrase, it brings its window to the front. Say the command with the wake phrase or say “Hey Vega” first and then give the command. Wake-word commands run automatically after recognition; sending and closing still show a confirmation.

Hands-free mode continuously listens for speech and sends short speech clips to Google's recognition service to identify the wake phrase. It is off until you enable it, and you can turn it off at any time by unchecking the option. The wake-word check is not offline in this version.

## Setup

### Portable Windows build

Download `Vega-Windows.zip`, extract it, and open `Vega.exe` from the extracted `Vega` folder. This build includes Python and the app dependencies, so Python does not need to be installed. Allow microphone access when Windows asks. Internet is needed for speech recognition, the wake word, and web searches. The executable is unsigned, so Windows may show its normal publisher warning.

1. Install Python 3.10 or newer and allow desktop apps to use your microphone in Windows Privacy settings.
2. Open PowerShell in this folder and install the packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Run `Run-Vega.bat`, or run `python vega_assistant.py` from PowerShell.

Vega uses Google Web Speech through the SpeechRecognition library for command transcription. Push-to-talk audio is sent to Google's recognition service when you speak; in hands-free mode, short clips are also sent continuously while wake listening is enabled. Vega does not save recordings or transcripts. Internet access is required for recognition and web searches. Spoken responses use the Windows voice installed through `pyttsx3`.

## Commands

- “Open ChatGPT”, “open Gmail”, “open YouTube”, or “open [website]”
- “Search for [query]”, “Google [query]”, or “look up [query]”
- “Type [dictated text]”
- “Read this aloud” reads the currently selected text
- “Type [dictated text] and send” (Mini shows the recognized text and asks before sending)
- “Send” or “submit” (asks before pressing Enter in the currently focused app)
- “Open a new tab”, “go back”, “scroll down”, “copy”, “paste”, and “close”
- “Stop” or “cancel” to cancel the current listening request

For safety, sending requires an on-screen confirmation. Closing the active window also requires confirmation. Keyboard actions operate on whichever app was active before Vega; check it before using type, paste, or send. Vega can press Enter but cannot confirm delivery, so check the target app afterward.

## Current limits

- Hands-free wake-word detection requires an internet connection and sends short clips to Google's recognition service; it is opt-in and can be switched off at any time.
- Speech recognition is online; offline recognition needs a separately installed model and engine.
- The recognized command appears in an editable box; choose **Run command** to execute it.
- Keyboard actions minimize Mini briefly so they reach the previously active app. Browser automation cannot verify that a message was delivered.
- The Stop button cancels speech recognition after its current microphone read returns (up to about 12 seconds); it does not interrupt a keyboard action already in progress.
- Credentials, logs, and persistent transcript storage are not implemented.

