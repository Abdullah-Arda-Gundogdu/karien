import asyncio
import os
import json
from typing import Optional
from assistant.core.logging_config import logger
from assistant.core.config import config
import pyaudio

try:
    from deepgram import AsyncDeepgramClient
except ImportError:
    import deepgram
    AsyncDeepgramClient = deepgram.AsyncDeepgramClient

# Lazy load VAD to avoid startup delay
_vad = None

def _get_vad():
    global _vad
    if _vad is None:
        from assistant.input.vad import vad
        _vad = vad
    return _vad

class DeepgramSTT:
    def __init__(self):
        self.api_key = config.DEEPGRAM_API_KEY
        if not self.api_key:
            logger.error("DEEPGRAM_API_KEY is missing. STT will not work.")
        
        # Audio config
        self.rate = 16000
        self.channels = 1
        self.chunk = 1024
        
        self.audio = pyaudio.PyAudio()
        self.client = AsyncDeepgramClient(api_key=self.api_key) if self.api_key else None
        self.use_vad = True  # Enable VAD filtering
        
        # Stats for debugging
        self._vad_filtered_count = 0
        self._vad_passed_count = 0

    async def listen(self, timeout: int = 15) -> str:
        """
        Connects to Deepgram Live, streams microphone audio, and returns the transcript.
        """
        if not self.client:
            logger.error("Cannot listen: No API Key or Client")
            return ""

        # Print listening status for user visibility
        print("Listening...", end="", flush=True)
        
        # Open Microphone Stream
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        transcript_result = ""
        stop_event = asyncio.Event()
        
        # Get VAD for filtering
        vad = _get_vad() if self.use_vad else None
        
        # Reset stats
        self._vad_filtered_count = 0
        self._vad_passed_count = 0

        # Connect to Deepgram
        async with self.client.listen.v1.connect(
            model="nova-2", 
            language="tr",
            smart_format=True, 
            encoding="linear16", 
            sample_rate=self.rate,
            channels=self.channels,
            interim_results=True,
            vad_events=True,
            endpointing=600
        ) as socket:
            
            async def sender():
                try:
                    while not stop_event.is_set():
                        data = await asyncio.to_thread(stream.read, self.chunk, exception_on_overflow=False)
                        
                        # VAD filtering: only send audio chunks containing speech
                        if vad is not None:
                            if not vad.is_speech(data):
                                self._vad_filtered_count += 1
                                await asyncio.sleep(0.001)
                                continue  # Skip this chunk - it's background noise
                            self._vad_passed_count += 1
                        
                        await socket.send_media(data)
                        await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Sender error: {e}")

            async def receiver():
                nonlocal transcript_result
                try:
                    async for message in socket:
                        # Process Transcript/Metadata
                        if hasattr(message, 'channel'):
                             # message.channel seems to be a list in this SDK version
                             ch = message.channel
                             if isinstance(ch, list):
                                 ch = ch[0]
                             
                             if hasattr(ch, 'alternatives'):
                                 alternatives = ch.alternatives
                                 if alternatives:
                                     transcript = alternatives[0].transcript
                                     if transcript:
                                         if message.is_final:
                                             transcript_result += f" {transcript}"
                                             # Print final part of this utterance
                                             print(f"\rUser: {transcript_result.strip()}", end="", flush=True)
                                             stop_event.set()
                                             return
                                         else:
                                             # Print interim
                                             print(f"\rUser: {transcript_result.strip()} {transcript}...", end="", flush=True)
                        
                        # Process UtteranceEnd
                        msg_type = getattr(message, 'type', '')
                        if msg_type == 'UtteranceEnd':
                            stop_event.set()
                            return

                        if stop_event.is_set():
                            return

                except Exception as e:
                    logger.error(f"Receiver error: {e}")

            # Run both
            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())
            
            try:
                await asyncio.wait_for(receiver_task, timeout=timeout)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
            
            stop_event.set()
            try:
                await sender_task
            except Exception:
                pass  # Sender already stopped

        # Cleanup Stream
        stream.stop_stream()
        stream.close()
        
        # Log VAD stats
        if vad is not None:
            logger.debug(f"VAD stats: {self._vad_passed_count} passed, {self._vad_filtered_count} filtered")
        
        print("") # Newline after listening is done
        return transcript_result.strip()

    async def listen_with_prepend(self, prepend_audio: bytes, timeout: int = 15) -> str:
        """
        Listen for speech, but send prepended audio first.
        Used for interruption handling to capture words said during TTS.
        
        Args:
            prepend_audio: Audio bytes to send before live mic stream (from circular buffer)
            timeout: Maximum time to wait for speech
            
        Returns:
            Transcribed text
        """
        if not self.client:
            logger.error("Cannot listen: No API Key or Client")
            return ""

        logger.info(f"Listening with {len(prepend_audio)} bytes of prepended audio")
        print("Listening...", end="", flush=True)
        
        # Open Microphone Stream
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        transcript_result = ""
        stop_event = asyncio.Event()
        
        # Get VAD for filtering
        vad = _get_vad() if self.use_vad else None

        # Connect to Deepgram
        async with self.client.listen.v1.connect(
            model="nova-2", 
            language="tr",
            smart_format=True, 
            encoding="linear16", 
            sample_rate=self.rate,
            channels=self.channels,
            interim_results=True,
            vad_events=True,
            endpointing=600
        ) as socket:
            
            async def sender():
                try:
                    # First, send the prepended audio (buffered audio from interruption)
                    if prepend_audio:
                        # Send in chunks
                        chunk_size = self.chunk * 2  # 2048 bytes per chunk
                        for i in range(0, len(prepend_audio), chunk_size):
                            if stop_event.is_set():
                                break
                            chunk = prepend_audio[i:i + chunk_size]
                            await socket.send_media(chunk)
                            await asyncio.sleep(0.001)
                        logger.debug("Prepended audio sent to Deepgram")
                    
                    # Then continue with live mic
                    while not stop_event.is_set():
                        data = await asyncio.to_thread(stream.read, self.chunk, exception_on_overflow=False)
                        
                        # VAD filtering for live audio
                        if vad is not None:
                            if not vad.is_speech(data):
                                await asyncio.sleep(0.001)
                                continue
                        
                        await socket.send_media(data)
                        await asyncio.sleep(0.001)
                except Exception as e:
                    logger.error(f"Sender error: {e}")

            async def receiver():
                nonlocal transcript_result
                try:
                    async for message in socket:
                        if hasattr(message, 'channel'):
                             ch = message.channel
                             if isinstance(ch, list):
                                 ch = ch[0]
                             
                             if hasattr(ch, 'alternatives'):
                                 alternatives = ch.alternatives
                                 if alternatives:
                                     transcript = alternatives[0].transcript
                                     if transcript:
                                         if message.is_final:
                                             transcript_result += f" {transcript}"
                                             print(f"\rUser: {transcript_result.strip()}", end="", flush=True)
                                             stop_event.set()
                                             return
                                         else:
                                             print(f"\rUser: {transcript_result.strip()} {transcript}...", end="", flush=True)
                        
                        msg_type = getattr(message, 'type', '')
                        if msg_type == 'UtteranceEnd':
                            stop_event.set()
                            return

                        if stop_event.is_set():
                            return

                except Exception as e:
                    logger.error(f"Receiver error: {e}")

            # Run both
            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())
            
            try:
                await asyncio.wait_for(receiver_task, timeout=timeout)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error(f"Listen loop error: {e}")
            
            stop_event.set()
            try:
                await sender_task
            except Exception:
                pass  # Sender already stopped

        # Cleanup
        stream.stop_stream()
        stream.close()
        
        print("")
        return transcript_result.strip()

stt = DeepgramSTT()
