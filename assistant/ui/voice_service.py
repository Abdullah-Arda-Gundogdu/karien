"""
Karien Voice Service — runs the voice Orchestrator inside the desktop app.

Owns a daemon thread with its own asyncio loop running the EXISTING
Orchestrator (same one `python -m assistant.main` uses) and wires its UI
hooks to the KarienAPI overlay bridge, so the small avatar overlay reacts
to wake word / listening / thinking / speaking / standby.

Shutdown protocol (deterministic — this replaced the old "best-effort"
stop that let a new start() race a still-dying pipeline and double-open
the microphone, crashing the whole app with a native PortAudio SIGSEGV):
  stop(): orchestrator.running=False + vosk_stt.request_stop() (listener
  returns within ~300ms) + tts.stop_playback(), then JOIN the voice thread,
  then a defensive audio_stream.stop(). start() refuses to spawn while the
  previous thread is still alive.
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
        # Serializes start/stop — unlocked toggling was the crash trigger
        self._lock = threading.Lock()

    def start(self):
        """Start the voice pipeline. Raises if the old one is still dying."""
        with self._lock:
            old = self._thread
            if old and old.is_alive():
                if self.enabled:
                    return  # genuinely running — idempotent no-op
                # A stop is still draining; give it a bounded moment
                old.join(timeout=3.0)
                if old.is_alive():
                    raise RuntimeError(
                        "Ses servisi hâlâ kapanıyor — bir saniye sonra tekrar dene."
                    )

            # Import lazily so the desktop app can boot even if audio deps break
            from assistant.core.orchestrator import orchestrator
            from assistant.input.vosk_stt import vosk_stt

            # Clear the stop request ONLY after the old thread is confirmed
            # dead — clearing earlier would un-stop a draining listener.
            vosk_stt.reset_stop()

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

    def stop(self) -> bool:
        """Deterministic stop: signal, join, release the microphone."""
        with self._lock:
            self.enabled = False

            if self._orchestrator:
                self._orchestrator.running = False
                self._orchestrator.is_active = False

            # Wake the blocking Vosk listener so standby exits within ~300ms
            try:
                from assistant.input.vosk_stt import vosk_stt
                vosk_stt.request_stop()
            except Exception:
                pass

            # Mute should also cut any speech in progress
            try:
                from assistant.output.tts import tts
                tts.stop_playback()
            except Exception:
                pass

            t = self._thread
            if t and t.is_alive():
                # Budget: vosk exit ≤0.3s + MCP shutdown + audio join ≤2s
                t.join(timeout=4.0)
                if t.is_alive():
                    logger.warning(
                        "Ses iş parçacığı hâlâ kapanıyor; start() ölene "
                        "kadar yeni pipeline açmayı reddedecek."
                    )
                    return False
            self._thread = None

            # Defensive: release the mic even if run() crashed mid-cleanup
            try:
                from assistant.input.audio_stream import audio_stream
                audio_stream.stop()
            except Exception:
                pass

            logger.info("Sesli mod kapatıldı.")
            return True
