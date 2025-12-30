import json
import os
import pyaudio
import sys
from assistant.core.logging_config import logger
from vosk import Model, KaldiRecognizer

class VoskSTT:
    def __init__(self, model_path="assistant/input/model"):
        self.model_path = model_path
        self.model = None
        self.recognizer = None
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
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

    def listen_for_wakeword(self, keywords: list[str], timeout: int = None) -> bool:
        """
        Listens for any of the keywords.
        Returns True if detected, False if timeout or error.
        keywords: list of lowercase strings e.g. ["hey karien"]
        """
        if not self.model:
            logger.error("Vosk model not loaded. Cannot listen.")
            return False

        # Construct grammar from keywords to force detection
        # Format: '["word one", "word two", "[unk]"]'
        # We append [unk] to handle background noise/other speech
        import json
        grammar_list = keywords + ["[unk]"]
        grammar_str = json.dumps(grammar_list)
        
        try:
            self.recognizer = KaldiRecognizer(self.model, 16000, grammar_str)
        except Exception as e:
            logger.error(f"Failed to initialize recognizer with grammar: {e}")
            # Fallback to standard recognizer if grammar fails (though unlikely)
            self.recognizer = KaldiRecognizer(self.model, 16000)

        # Open stream
        try:
            self.stream = self.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
            self.stream.start_stream()
        except Exception as e:
            logger.error(f"Failed to open audio stream: {e}")
            return False

        logger.info(f"Listening for wake word: {keywords} (Local)")
        
        try:
            while True:
                data = self.stream.read(4096, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        # Check keywords
                        for keyword in keywords:
                            if keyword in text:
                                logger.info(f"Wake word detected: '{keyword}' in '{text}'")
                                return True
                else:
                    # Partial result (faster detection)
                    partial = json.loads(self.recognizer.PartialResult())
                    partial_text = partial.get("partial", "")
                    if partial_text:
                         for keyword in keywords:
                            if keyword in partial_text:
                                logger.info(f"Wake word detected (partial): '{keyword}'")
                                return True
                                
        except KeyboardInterrupt:
            return False
        except Exception as e:
            logger.error(f"Error in Vosk listen: {e}")
            return False
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None

vosk_stt = VoskSTT()
