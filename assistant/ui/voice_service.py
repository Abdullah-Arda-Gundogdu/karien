"""
Karien Voice Service — runs the voice Orchestrator inside the desktop app.

Owns a daemon thread with its own asyncio loop running the EXISTING
Orchestrator (same one `python -m assistant.main` uses) and wires its UI
hooks to the KarienAPI overlay bridge, so the small avatar overlay reacts
to wake word / listening / thinking / speaking / standby.

Limitations (documented, best-effort stop):
- stop() only sets orchestrator.running = False. The blocking Vosk
  wake-word listener returns on its own cadence, so the thread may take a
  few seconds to actually exit. Audio devices stay open until then.
- start() after a stop() creates a fresh thread over the same singleton
  orchestrator; state flags are reset before restart.
"""

import asyncio
import threading
from assistant.core.logging_config import logger


class OverlayHooks:
    """Maps orchestrator lifecycle events to the overlay avatar bridge."""

    def __init__(self, api):
        self._api = api

    def on_wake(self):
        self._api.overlay_show()
        self._api.overlay_state("listen")

    def on_listen(self):
        self._api.overlay_state("listen")

    def on_think(self):
        self._api.overlay_state("think")

    def on_mood(self, mood):
        self._api.overlay_mood(mood)

    def on_speak(self):
        self._api.overlay_state("speak")

    def on_standby(self):
        self._api.overlay_hide()


class VoiceService:
    """Runs the Orchestrator in a background daemon thread."""

    def __init__(self, api):
        self._api = api
        self._thread = None
        self._orchestrator = None
        self.enabled = False

    def start(self):
        """Start the voice pipeline (no-op if already running)."""
        if self._thread and self._thread.is_alive():
            self.enabled = True
            return

        # Import lazily so the desktop app can boot even if audio deps break
        from assistant.core.orchestrator import orchestrator

        orchestrator.hooks = OverlayHooks(self._api)
        orchestrator.running = False
        orchestrator.is_active = False
        self._orchestrator = orchestrator

        self._thread = threading.Thread(
            target=self._run,
            name="karien-voice",
            daemon=True
        )
        self._thread.start()
        self.enabled = True
        logger.info("Sesli mod başlatıldı. 'Hey Karien' demeni bekliyorum.")

    def _run(self):
        """Thread body: own asyncio loop running the orchestrator."""
        try:
            asyncio.run(self._orchestrator.run())
            logger.info("Sesli mod durdu.")
        except Exception as e:
            logger.error(
                f"Sesli mod başlatılamadı: {e}. "
                "Mikrofon iznini ve ses ayarlarını kontrol et — "
                "şimdilik sadece metin modunda devam ediyorum."
            )
        finally:
            self.enabled = False

    def stop(self):
        """Best-effort stop: signal the loop; Vosk listener exits on its own."""
        self.enabled = False
        if self._orchestrator:
            self._orchestrator.running = False
            self._orchestrator.is_active = False
        logger.info("Sesli mod kapatılıyor (dinleyici kendi döngüsünde duracak).")
