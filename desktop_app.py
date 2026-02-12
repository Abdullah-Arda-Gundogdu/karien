"""
Karien Desktop App — pywebview entry point.

Launches the UI window and connects the API bridge.
Text-only mode: no audio/VTS — only console text → LLM interaction.
"""

import webview
import sys
import os
from assistant.ui.api import KarienAPI

# Get absolute path to the UI file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(BASE_DIR, "ui", "index.html")


def on_loaded(window, api):
    """Called when pywebview finishes loading the page."""
    api.set_window(window)


def on_closed():
    print("App closed")
    sys.exit(0)


def main():
    # 1. Initialize the API Bridge
    api = KarienAPI()

    # 2. Create the Window
    window = webview.create_window(
        "Karien",
        url=f"file://{ui_path}",
        width=1200,
        height=800,
        resizable=True,
        frameless=False,
        js_api=api
    )

    # 3. Bind events
    window.events.loaded += lambda: on_loaded(window, api)
    window.events.closed += on_closed

    # 4. Start the App (storage_path avoids temp folder cleanup warnings on Windows)
    storage_path = os.path.join(BASE_DIR, ".webview_cache")
    webview.start(debug=True, storage_path=storage_path)


if __name__ == "__main__":
    main()
