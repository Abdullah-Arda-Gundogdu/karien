import speech_recognition as sr
from assistant.core.logging_config import logger
from assistant.core.config import config

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.mic_index = config.MIC_INDEX
        logger.info(f"Initializing STT with mic index: {self.mic_index}")
        if config.OPENAI_API_KEY:
             from openai import OpenAI
             self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        else:
            logger.error("Create OpenAI client for STT failed: OPENAI_API_KEY missing")
            self.client = None


    def listen(self, timeout: int = 5, time_limit: int = 10) -> str:
        """
        Listens to the microphone and returns the recognized text using OpenAI Whisper.
        """
        try:
            with sr.Microphone(device_index=self.mic_index) as source:
                logger.debug("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Listening (OpenAI Whisper)...")
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=time_limit)
            
            logger.debug("Processing audio with OpenAI...")
            
            if not self.client:
                 logger.error("OpenAI Client not available.")
                 return ""

            # We need to save the audio to a file or file-like object to send to OpenAI
            # SpeechRecognition audio data is raw PCM or WAV data.
            # We can get WAV data directly.
            wav_data = audio.get_wav_data()
            
            import io
            # Create a virtual file
            audio_file = io.BytesIO(wav_data)
            audio_file.name = "speech.wav" # OpenAI API requires a filename with extension
            
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                language="tr"
            )
            
            text = transcript.text
            logger.info(f"Heard: {text}")
            return text

        except sr.WaitTimeoutError:
            logger.debug("Listening timed out (silence).")
            return ""
        except sr.UnknownValueError:
            logger.debug("Could not understand audio.")
            return ""
        except sr.RequestError as e:
            logger.error(f"STT Service Error: {e}")
            return ""
        except Exception as e:
            logger.error(f"STT Unexpected Error: {e}")
            return ""

stt = SpeechToText()
