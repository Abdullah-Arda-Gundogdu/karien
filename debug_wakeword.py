from assistant.input.vosk_stt import VoskSTT
import json
import pyaudio

def debug_listen():
    print("Initializing Vosk for debug...")
    stt = VoskSTT()
    
    if not stt.model:
        print("Model failed to load.")
        return

    print("Listening... Say 'Hey Karien' or other phrases. Press Ctrl+C to stop.")
    
    print("Listening... Say 'Hey Karien' or other phrases. Press Ctrl+C to stop.")
    
    # Manually initialize recognizer for this debug session WITH GRAMMAR
    from vosk import KaldiRecognizer
    # "Karien" is not in the dictionary. We use "Kariyer" (Career) and "Karin" as phonetic proxies.
    # We hope that saying "Hey Karien" will be recognized as "Hey Kariyer".
    grammar = '["hey kariyer", "hey karin", "merhaba kariyer", "merhaba karin", "hey", "merhaba", "[unk]"]'
    stt.recognizer = KaldiRecognizer(stt.model, 16000, grammar)
    
    stream = stt.audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
    stream.start_stream()
    
    try:
        while True:
            data = stream.read(4096, exception_on_overflow=False)
            if stt.recognizer.AcceptWaveform(data):
                result = json.loads(stt.recognizer.Result())
                text = result.get("text", "")
                if text:
                    print(f"Final: '{text}'")
            else:
                partial = json.loads(stt.recognizer.PartialResult())
                partial_text = partial.get("partial", "")
                if partial_text:
                    print(f"\rPartial: {partial_text}", end="", flush=True)
                    
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        stream.stop_stream()
        stream.close()

if __name__ == "__main__":
    debug_listen()
