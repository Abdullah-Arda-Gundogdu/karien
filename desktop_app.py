import webview
import threading
import sys
import os
from assistant.ui.api import KarienAPI

# Get absolute path to the UI file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(BASE_DIR, "ui_mockup.html")

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
        frameless=False,  # Set to True later for custom title bar
        js_api=api
    )

    # 3. Start the App
    webview.start(debug=True)

if __name__ == "__main__":
    main()
