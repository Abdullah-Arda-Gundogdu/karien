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
            endpointing=300
        ) as socket:
            
            async def sender():
                try:
                    while not stop_event.is_set():
                        data = await asyncio.to_thread(stream.read, self.chunk, exception_on_overflow=False)
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
            except:
                pass

        # Cleanup Stream
        stream.stop_stream()
        stream.close()
        
        print("") # Newline after listening is done
        return transcript_result.strip()

stt = DeepgramSTT()
