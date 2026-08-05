import json
import os
import threading
import pyaudio
import sys
from pathlib import Path
from assistant.core.logging_config import logger
from assistant.core.config import BASE_DIR
from vosk import Model, KaldiRecognizer

# Lazy import VAD to avoid circular imports and startup delay
_vad = None

def _get_vad():
    global _vad
    if _vad is None:
        from assistant.input.vad import vad
        _vad = vad
    return _vad

class VoskSTT:
    def __init__(self, model_path=None):
        # Use absolute path relative to project root
        self.model_path = model_path or str(BASE_DIR / "assistant" / "input" / "model")
        self.model = None
        self.recognizer = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.use_vad = True  # Enable VAD gating
        # Cooperative stop: listen_for_wakeword used to loop forever, which
        # made voice-service shutdown windows unbounded (crash enabler).
        self._stop_event = threading.Event()
        # Re-entrancy guard: two concurrent listeners would clobber the
        # shared stream/recognizer and close a stream under a blocked reader
        self._listen_lock = threading.Lock()

    def request_stop(self):
        """Ask a running listen_for_wakeword to return False promptly."""
        self._stop_event.set()

    def reset_stop(self):
        """Clear the stop request (call before starting a fresh listener)."""
        self._stop_event.clear()

    @property
    def stop_requested(self) -> bool:
        return self._stop_event.is_set()
        
        if not os.path.exists(self.model_path):
            logger.error(f"Vosk model not found at {self.model_path}. Please download it.")
        else:
            try:
                # Suppress Vosk logs (they are very verbose)
                null_fd = os.open(os.devnull, os.O_RDWR)
                save_stderr = os.dup(2)
                os.dup2(null_fd, 2)
                
                self.model = Model(self.model_path)
                
                # Restore stderr
                os.dup2(save_stderr, 2)
                os.close(null_fd)
            except Exception as e:
                logger.error(f"Failed to load Vosk model: {e}")

    def _cleanup_stream(self):
        """Properly close the audio stream."""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.debug(f"Error closing stream: {e}")
            self.stream = None

    def listen_for_wakeword(self, keywords: list[str]) -> bool:
        """
        Listens for any of the keywords.
        Runs until a wake word is detected OR request_stop() is called.
        Returns True if detected, False on stop/error.
        keywords: list of lowercase strings e.g. ["hey karien"]

        Stop latency: one stream.read(4096) at 16 kHz is ~256ms, so a stop
        request is honored within ~300ms.
        """
        if not self.model:
            logger.error("Vosk model not loaded. Cannot listen.")
            return False
        if self._stop_event.is_set():
            return False

        # Re-entrancy guard — a second concurrent listener would clobber
        # the shared stream/recognizer (native crash risk)
        if not self._listen_lock.acquire(blocking=False):
            logger.warning("Wake-word listener already active; refusing second entry")
            return False

        try:
            # Construct grammar from keywords to force detection
            # Format: '["word one", "word two", "[unk]"]'
            # We append [unk] to handle background noise/other speech
            grammar_list = keywords + ["[unk]"]
            grammar_str = json.dumps(grammar_list)

            try:
                self.recognizer = KaldiRecognizer(self.model, 16000, grammar_str)
            except Exception as e:
                logger.error(f"Failed to initialize recognizer with grammar: {e}")
                # Fallback to standard recognizer if grammar fails (though unlikely)
                self.recognizer = KaldiRecognizer(self.model, 16000)

            # Get VAD for gating
            vad = _get_vad() if self.use_vad else None
            consecutive_silence = 0  # Track consecutive silence frames

            while True: # Outer loop for reconnection
                if self._stop_event.is_set():
                    return False
                try:
                    # Open stream if not open
                    if not self.stream:
                        self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
                        self.stream.start_stream()
                        logger.info(f"Microphone stream started. Listening for: {keywords}")

                    while True: # Inner loop for reading
                        if self._stop_event.is_set():
                            return False

                        data = self.stream.read(4096, exception_on_overflow=False)

                        # VAD gating: skip processing if no speech detected
                        if vad is not None:
                            if not vad.is_speech(data):
                                consecutive_silence += 1
                                # Only log occasionally to avoid spam
                                if consecutive_silence % 50 == 0:
                                    logger.debug(f"VAD: Silence (consecutive: {consecutive_silence})")
                                continue
                            else:
                                if consecutive_silence > 0:
                                    logger.debug("VAD: Speech detected, processing...")
                                consecutive_silence = 0

                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get("text", "")
                            if text:
                                for keyword in keywords:
                                    if keyword in text:
                                        logger.info(f"Wake word detected: '{keyword}' in '{text}'")
                                        return True
                        else:
                            partial = json.loads(self.recognizer.PartialResult())
                            partial_text = partial.get("partial", "")
                            if partial_text:
                                for keyword in keywords:
                                    if keyword in partial_text:
                                        logger.info(f"Wake word detected (partial): '{keyword}'")
                                        return True

                except KeyboardInterrupt:
                    return False
                except KeyError as e:
                    # Specific pyaudio error?
                    logger.error(f"Audio Stream Error: {e}. Restarting stream...")
                    self._cleanup_stream()
                    # Interruptible backoff: a stop during recovery returns
                    if self._stop_event.wait(1):
                        return False
                except Exception as e:
                    logger.error(f"Critical Error in Vosk listen: {e}. Restarting listener...")
                    self._cleanup_stream()
                    if self._stop_event.wait(2):
                        return False
        finally:
            # Single cleanup point for every exit path (detected/stop/error)
            self._cleanup_stream()
            self._listen_lock.release()

vosk_stt = VoskSTT()
