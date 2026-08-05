from assistant.core.logging_config import logger
from assistant.core.config import config

import queue
import threading
import time
import os
import tempfile

class TextToSpeech:
    def __init__(self):
        logger.info("Initializing TTS...")
        self.client = None
        self.provider = "openai"

        # Initialize Pygame Mixer for Audio (Cross-Platform)
        try:
            import pygame
            pygame.mixer.init()
            logger.info("Pygame mixer initialized.")
        except ImportError:
            logger.error("Pygame not found. Run `pip install pygame`.")
        except Exception as e:
            logger.error(f"Failed to initialize Pygame mixer: {e}")

        # Check for ElevenLabs first (as requested for better quality)
        if config.ELEVENLABS_API_KEY:
            try:
                from elevenlabs.client import ElevenLabs
                self.client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
                self.provider = "elevenlabs"
                logger.info("TTS Provider: ElevenLabs")
            except ImportError:
                 logger.error("ElevenLabs configured but module not found. Run `pip install elevenlabs`.")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs: {e}")

        # Fallback to OpenAI if ElevenLabs is not set up or failed
        if not self.client and config.OPENAI_API_KEY:
             try:
                 from openai import OpenAI
                 self.client = OpenAI(api_key=config.OPENAI_API_KEY)
                 self.provider = "openai"
                 logger.info("TTS Provider: OpenAI")
             except Exception as e:
                 logger.error(f"Failed to initialize OpenAI TTS: {e}")
        
        if not self.client:
            logger.error("No TTS provider available (OpenAI or ElevenLabs).")

            
        self.queue = queue.Queue()
        self.is_running = True
        self.active_generations = 0
        self.lock = threading.Lock()
        # Playback epoch: stop_playback() bumps it, and every queued item is
        # stamped with the epoch it was created in. Items whose epoch is
        # stale are discarded instead of played — this is what makes "stop"
        # actually stop items that were ALREADY dequeued and mid-generation.
        self._epoch = 0
        
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()

    def _current_epoch(self) -> int:
        with self.lock:
            return self._epoch

    def _playback_worker(self):
        """
        Background thread that plays audio from the queue.
        """
        import pygame
        from pathlib import Path

        while self.is_running:
            try:
                # Get item from queue (blocking)
                # item is a tuple: (event, result_container, epoch)
                item = self.queue.get(timeout=1)

                if item is None:
                    continue

                completion_event, result_container, epoch = item

                # Wait for generation — but abandon within ~100ms if a stop
                # superseded this item (don't sleep out a slow TTS API call)
                while not completion_event.wait(timeout=0.1):
                    if self._current_epoch() != epoch:
                        break

                if self._current_epoch() != epoch:
                    # Stale: a stop happened after this item was dequeued.
                    # Never play it; clean its temp file if generation finished.
                    if completion_event.is_set():
                        stale_path = result_container.get('path')
                        if stale_path and result_container.get('is_temp', False):
                            Path(stale_path).unlink(missing_ok=True)
                    logger.debug("Discarded stale TTS item (stopped)")
                    self.queue.task_done()
                    continue

                audio_file_path = result_container.get('path')

                if audio_file_path and Path(audio_file_path).exists():
                    logger.info(f"Playing audio: {audio_file_path}")
                    try:
                        pygame.mixer.music.load(str(audio_file_path))
                        pygame.mixer.music.play()

                        while pygame.mixer.music.get_busy():
                            if self._current_epoch() != epoch:
                                # Stop arrived mid-playback
                                pygame.mixer.music.stop()
                                break
                            pygame.time.Clock().tick(10)

                        # Unload to release file lock
                        pygame.mixer.music.unload()

                        # Only delete temporary files (TTS-generated), not permanent sound assets
                        if result_container.get('is_temp', False):
                            try:
                                Path(audio_file_path).unlink(missing_ok=True)
                                logger.debug(f"Deleted temp audio: {audio_file_path}")
                            except Exception as e:
                                logger.warning(f"Failed to delete temp audio {audio_file_path}: {e}")
                            
                    except Exception as e:
                        logger.error(f"Pygame Playback Error: {e}")
                else:
                    logger.warning(f"Skipping playback (file not found or failed): {audio_file_path}")

                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Playback Thread Error: {e}")

    def play_file(self, file_path):
        """
        Directly play an existing audio file (blocking-ish or fire-and-forget logic).
        For simplicity in Orchestrator, we'll queue it as a dummy generation.
        """
        if not file_path: 
            return
            
        # Create a pre-filled result container
        completion_event = threading.Event()
        completion_event.set()
        result_container = {'path': file_path}

        # We don't increment active_generations because it's already "done"
        # But we do put it in the playback queue (stamped with the current
        # epoch so a stop also cancels queued chimes)
        self.queue.put((completion_event, result_container, self._current_epoch()))

    def play_sound(self, name: str):
        """
        Play a pre-recorded sound file by name.
        Looks for files in assets/sounds/ first, then assets/.
        
        Usage: tts.play_sound("error")  # plays error.mp3
               tts.play_sound("startup.mp3")  # also works with extension
        
        This avoids using TTS API tokens for hardcoded messages.
        """
        from pathlib import Path
        from assistant.core.config import ASSETS_DIR
        
        # Add .mp3 extension if not provided
        if not name.endswith('.mp3'):
            name = f"{name}.mp3"
        
        # Look in assets/sounds first, then assets
        sounds_dir = ASSETS_DIR / "sounds"
        candidates = [
            sounds_dir / name,
            ASSETS_DIR / name,
        ]
        
        for path in candidates:
            if path.exists():
                logger.info(f"Playing sound: {path}")
                self.play_file(str(path))
                return
        
        # File not found - log warning
        logger.warning(f"Sound file not found: {name} (searched: {[str(p) for p in candidates]})")

    def speak(self, text: str):
        """
        Legacy blocking speak.
        """
        self.speak_async(text)
        self.wait_for_idle()

    def speak_async(self, text: str):
        """
        Generates audio and puts it in the playback queue.
        Returns immediately (mostly).
        """
        logger.info(f"Queueing to speak: {text}")
        if not text:
            return
        
        if not self.client:
             logger.error("TTS failed: No TTS Client initialized")
             return

        # Create a placeholder for the result to preserve order
        completion_event = threading.Event()
        result_container = {} # Mutable dict to hold result

        # Stamp with the current epoch and put in queue IMMEDIATELY
        with self.lock:
            epoch = self._epoch
            self.active_generations += 1
        self.queue.put((completion_event, result_container, epoch))

        # Generate audio in a separate thread
        threading.Thread(target=self._generate_audio,
                         args=(text, completion_event, result_container, epoch)).start()

    def _generate_audio(self, text, completion_event, result_container, epoch):
        try:
            from pathlib import Path
            import uuid
            
            # Save to temp file with unique name in the system temp directory
            # We use a suffix to ensure it's treated as an mp3
            temp_dir = tempfile.gettempdir()
            filename = f"tts_{uuid.uuid4().hex}.mp3"
            temp_file = Path(os.path.join(temp_dir, filename))
            
            if self.provider == "elevenlabs":
                # ElevenLabs Generation
                # Ensure voice ID is set, or use a default
                voice_id = config.ELEVENLABS_VOICE_ID 
                logger.debug(f"Using ElevenLabs Voice ID: {voice_id}")
                
                # Use text_to_speech.convert (returns generator of bytes)
                # Updated for new ElevenLabs SDK
                audio_stream = self.client.text_to_speech.convert(
                    text=text,
                    voice_id=voice_id,
                    model_id=config.ELEVENLABS_MODEL_ID
                )
                
                # Write stream to file
                with open(temp_file, "wb") as f:
                    for chunk in audio_stream:
                        f.write(chunk)
                        
            elif self.provider == "openai":
                # OpenAI Generation
                response = self.client.audio.speech.create(
                    model="tts-1",
                    voice="nova", 
                    input=text
                )
                response.stream_to_file(temp_file)

            # Set result and mark as temporary (should be deleted after playback)
            result_container['path'] = temp_file
            result_container['is_temp'] = True
            
        except Exception as e:
            logger.error(f"TTS Generation Error ({self.provider}): {e}")
            result_container['path'] = None
        finally:
            # Signal completion
            completion_event.set()

            with self.lock:
                stale = (epoch != self._epoch)
                if not stale:
                    self.active_generations -= 1
                # if stale: stop_playback already reset the counter to 0

            if stale:
                # A stop superseded this generation — it will never play;
                # we own the temp file, clean it up ourselves.
                from pathlib import Path
                stale_path = result_container.get('path')
                if stale_path and result_container.get('is_temp', False):
                    Path(stale_path).unlink(missing_ok=True)

    def wait_for_idle(self):
        """
        Blocks until all generation threads are done AND the playback queue is empty.
        """
        # 1. Wait for generations to finish
        while True:
            with self.lock:
                if self.active_generations == 0:
                    break
            time.sleep(0.1)
        
        # 2. Wait for playback queue to empty
        self.queue.join()

    def stop_playback(self):
        """
        Immediately stop current playback, cancel in-flight generations and
        clear the queue. Used for interruption handling and the Stop button.
        """
        import pygame
        from pathlib import Path

        # 1. Bump the epoch FIRST: everything created before this instant is
        #    now stale — including items already dequeued by the worker and
        #    generations still waiting on the TTS API.
        with self.lock:
            self._epoch += 1
            self.active_generations = 0

        # 2. Stop current playback
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception as e:
            logger.debug(f"Error stopping playback: {e}")

        # 3. Clear pending items from queue (unlink finished temp files)
        cleared = 0
        while not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                if item:
                    ev, rc, _ = item
                    if ev.is_set() and rc.get('is_temp', False) and rc.get('path'):
                        Path(rc['path']).unlink(missing_ok=True)
                self.queue.task_done()
                cleared += 1
            except queue.Empty:
                break

        if cleared > 0:
            logger.info(f"TTS interrupted, cleared {cleared} queued items")
        else:
            logger.info("TTS playback stopped")

    def is_playing(self) -> bool:
        """
        Check if audio is currently playing or queued.
        Used to detect when to listen for interruption.
        """
        import pygame
        
        # Check if music is actively playing
        if pygame.mixer.music.get_busy():
            return True
        
        # Check if there are items in the queue
        if not self.queue.empty():
            return True
        
        # Check if there are active generations
        with self.lock:
            if self.active_generations > 0:
                return True
        
        return False

    def stop(self):
        self.is_running = False
        if self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1)

tts = TextToSpeech()
