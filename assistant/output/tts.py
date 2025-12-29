import pyttsx3
from assistant.core.logging_config import logger
from assistant.core.config import config

class TextToSpeech:
    def __init__(self):
        logger.info("Initializing TTS (OpenAI)...")
        if config.OPENAI_API_KEY:
             from openai import OpenAI
             self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        else:
            logger.error("Create OpenAI client for TTS failed: OPENAI_API_KEY missing")
            self.client = None

    def speak(self, text: str):
        """
        Speaks the given text using OpenAI TTS and plays it via afplay (macOS).
        """
        logger.info(f"Speaking: {text}")
        if not text:
            return
        
        if not self.client:
             logger.error("TTS failed: No OpenAI Client")
             return

        try:
            import subprocess
            from pathlib import Path
            
            # Use 'nova' for a more energetic/youthful voice
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="nova", 
                input=text
            )
            
            # Save to temp file
            temp_file = Path("response.mp3")
            response.stream_to_file(temp_file)
            
            # Play using native macOS player
            subprocess.run(["afplay", str(temp_file)])
            
            # Cleanup optionally, or keep for debugging
            # temp_file.unlink() 
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")

tts = TextToSpeech()
