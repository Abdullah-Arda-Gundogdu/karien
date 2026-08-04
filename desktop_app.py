"""
Karien Desktop App — pywebview entry point.

Launches the main UI window, the overlay avatar window and the voice
service, and connects the API bridge.
Main window: console text → LLM interaction (always available).
Overlay + voice: wake word pipeline drives the small avatar (best-effort —
falls back to text-only if audio init fails).
"""

import webview
import sys
import os
from assistant.ui.api import KarienAPI
from assistant.ui.voice_service import VoiceService
from assistant.core.logging_config import logger

# Get absolute path to the UI file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Overlay window geometry (top-right corner)
OVERLAY_WIDTH = 190
OVERLAY_HEIGHT = 230
OVERLAY_MARGIN_RIGHT = 12
OVERLAY_TOP = 36


def on_loaded(window, api, voice_service):
    """Called when pywebview finishes loading a page in the main window."""
    api.set_window(window)

    # Start voice AFTER the webview is ready. Skip during the first-run
    # wizard; when the wizard navigates to index.html this fires again.
    if not api.is_first_run():
        try:
            voice_service.start()
        except Exception as e:
            logger.error(
                f"Sesli mod başlatılamadı: {e}. "
                "Mikrofon iznini kontrol et — metin modunda devam ediyorum."
            )


def on_closed():
    print("App closed")
    sys.exit(0)


def create_overlay_window(api):
    """Create the small always-on-top avatar overlay (hidden until wake)."""
    overlay_file = os.path.join(BASE_DIR, "ui", "overlay.html")

    # Position near the top-right of the primary screen
    x, y = None, None
    try:
        screen = webview.screens[0]
        x = int(screen.width) - OVERLAY_WIDTH - OVERLAY_MARGIN_RIGHT
        y = OVERLAY_TOP
    except Exception as e:
        logger.warning(f"Could not read screen size, using default overlay position: {e}")

    overlay = webview.create_window(
        "Karien Avatar",
        url=f"file://{overlay_file}",
        width=OVERLAY_WIDTH,
        height=OVERLAY_HEIGHT,
        x=x,
        y=y,
        resizable=False,
        frameless=True,
        on_top=True,
        transparent=True,
        hidden=True,
        js_api=api
    )
    api.set_overlay_window(overlay)
    return overlay


def main():
    # 1. Initialize the API Bridge + Voice Service
    api = KarienAPI()
    voice_service = VoiceService(api)
    api.set_voice_service(voice_service)

    # 2. Determine which page to load
    if api.is_first_run():
        ui_file = os.path.join(BASE_DIR, "ui", "wizard.html")
    else:
        ui_file = os.path.join(BASE_DIR, "ui", "index.html")

    # 3. Create the Windows (main + overlay avatar)
    window = webview.create_window(
        "Karien",
        url=f"file://{ui_file}",
        width=1200,
        height=800,
        resizable=True,
        frameless=False,
        js_api=api
    )
    create_overlay_window(api)

    # 4. Bind events
    window.events.loaded += lambda: on_loaded(window, api, voice_service)
    window.events.closed += on_closed

    # 5. Start the App (storage_path avoids temp folder cleanup warnings on Windows)
    storage_path = os.path.join(BASE_DIR, ".webview_cache")
    webview.start(debug=True, storage_path=storage_path)


if __name__ == "__main__":
    main()
