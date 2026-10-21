# Vega Voice Assistant

Vega is a Windows voice assistant with a JavaScript interface (index.html) and a local Python computer-control service (app.py). It supports “Hey Vega” wake listening, browser-based speech recognition, spoken replies, and a basic set of voice commands.

## Run Vega

1. Install Python 3.10+ and Chrome or Edge.
2. Double-click Run-Vega.bat. It installs the required Python packages and starts Vega in your browser.
3. Allow microphone access if prompted. Click **Listen**, speak, review/edit the transcript, then choose **Run command**. Or enable the optional “Hey Vega” wake listener.

The local service binds to 127.0.0.1:8765. Keep the Vega page open. Computer actions target the window that was active before you returned to Vega.

## Commands

- “Open ChatGPT”, “Open YouTube”, “Open Gmail”, or “Open [site or app name]”
- “Search for [query]”, “Google [query]”, or “Look up [query]”
- “Type [text]” / “Write [text]”
- “Type [text] and send” or “Send” (asks before pressing Enter)
- “Close” (asks before closing the previously active window)
- “Open a new tab”, “Go back”, “Scroll down/up”, “Copy”, “Paste”, “Read this aloud”, and “Stop”

This is a starter assistant with a built-in phrase matcher, not an AI model. Unknown “open” targets are searched on Google. The service does not run arbitrary shell commands.

## Speech and privacy

Speech recognition uses the browser Web Speech API, which may send audio to the browser vendor's recognition service. Wake listening is off by default and requires confirmation; while enabled, speech recognition remains active to detect “Hey Vega.” Vega does not save audio or transcripts. Stop/cancel ends voice listening. Spoken output uses the browser's speech synthesis.

“Send” presses Enter and cannot verify delivery. Confirm the destination and content before approving the action. “Close” uses Alt+F4 on the previous window.

## Files

- index.html: JavaScript interface, speech controls, and confirmation dialogs
- app.py: loopback-only Python service and supported computer actions
- requirements.txt: Python dependencies
- Run-Vega.bat: Windows setup and launcher
