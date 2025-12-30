from assistant.core.config import config
import os

def generate_goodbye():
    text = "İyi gecelerrr!"
    output_path = "assets/goodbye.mp3"
    
    # Ensure assets directory exists
    os.makedirs("assets", exist_ok=True)
    
    if config.ELEVENLABS_API_KEY:
        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
            print("Generating with ElevenLabs...")
            
            audio_stream = client.text_to_speech.convert(
                text=text,
                voice_id=config.ELEVENLABS_VOICE_ID,
                model_id=config.ELEVENLABS_MODEL_ID
            )
            
            with open(output_path, "wb") as f:
                for chunk in audio_stream:
                    f.write(chunk)
            print(f"Saved to {output_path}")
            return
        except Exception as e:
            print(f"ElevenLabs failed: {e}")
    
    if config.OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("Generating with OpenAI...")
            
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text
            )
            response.stream_to_file(output_path)
            print(f"Saved to {output_path}")
            return
        except Exception as e:
            print(f"OpenAI failed: {e}")

if __name__ == "__main__":
    generate_goodbye()
