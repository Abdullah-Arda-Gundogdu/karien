import sys
import os
import shutil
from pathlib import Path

# Ensure project root is in path
sys.path.append(os.getcwd())

from assistant.output.tts import tts
from assistant.core.config import config

def generate_startup():
    text = "Selam! Ben Karien! Sana nasıl yardımcı olabilirim?"
    print(f"Generating startup audio for: '{text}'")
    
    # We need to access the client directly or use a modified speak method that returns the path
    # But tts.speak_async puts it in a queue and plays it.
    # We want to intercept the generation.
    
    # Let's use the internal client logic directly for this script
    if tts.provider == "elevenlabs":
        voice_id = config.ELEVENLABS_VOICE_ID
        print(f"Using Voice ID: {voice_id}")
        
        audio_stream = tts.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=config.ELEVENLABS_MODEL_ID
        )
        
        output_path = config.ASSETS_DIR / "startup.mp3"
        with open(output_path, "wb") as f:
            for chunk in audio_stream:
                f.write(chunk)
        
        print(f"Saved to {output_path}")

    elif tts.provider == "openai":
        response = tts.client.audio.speech.create(
            model="tts-1",
            voice="nova", 
            input=text
        )
        output_path = config.ASSETS_DIR / "startup.mp3"
        response.stream_to_file(output_path)
        print(f"Saved to {output_path}")
    else:
        print("No TTS provider configured.")

if __name__ == "__main__":
    generate_startup()
