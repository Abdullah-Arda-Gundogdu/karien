import pyttsx3
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
        
        self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        self.playback_thread.start()

    def _playback_worker(self):
        """
        Background thread that plays audio from the queue.
        """
        import pygame
        from pathlib import Path
        
        while self.is_running:
            try:
                # Get item from queue (blocking)
                # item is now a tuple: (event, result_container)
                item = self.queue.get(timeout=1)
                
                if item is None:
                    continue
                    
                completion_event, result_container = item
                
                # Wait for generation to complete
                completion_event.wait()
                
                audio_file_path = result_container.get('path')
                
                if audio_file_path and Path(audio_file_path).exists():
                    logger.info(f"Playing audio: {audio_file_path}")
                    try:
                        pygame.mixer.music.load(str(audio_file_path))
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                            
                        # Unload to release file lock so we can delete it
                        pygame.mixer.music.unload()

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
        # But we do put it in the playback queue
        self.queue.put((completion_event, result_container))

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
        
        # Put placeholder in queue IMMEDIATELY
        self.queue.put((completion_event, result_container))

        # Generate audio in a separate thread
        with self.lock:
            self.active_generations += 1
        threading.Thread(target=self._generate_audio, args=(text, completion_event, result_container)).start()

    def _generate_audio(self, text, completion_event, result_container):
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

            # Set result
            result_container['path'] = temp_file
            
        except Exception as e:
            logger.error(f"TTS Generation Error ({self.provider}): {e}")
            result_container['path'] = None
        finally:
            # Signal completion
            completion_event.set()
            
            with self.lock:
                self.active_generations -= 1

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
        Immediately stop current playback and clear the queue.
        Used for interruption handling.
        """
        import pygame
        
        # Stop current playback
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception as e:
            logger.debug(f"Error stopping playback: {e}")
        
        # Clear pending items from queue
        cleared = 0
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
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
