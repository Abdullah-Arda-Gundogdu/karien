"""
Continuous Audio Stream with Circular Buffer
=============================================
Provides always-on audio capture for VAD and interruption detection.
"""

import threading
import pyaudio
import numpy as np
from collections import deque
from typing import Optional
from assistant.core.logging_config import logger
from assistant.core.config import config


class AudioStream:
    """
    Singleton audio capture service that maintains a circular buffer.
    Allows retrieving recent audio for VAD checks and interruption handling.
    """
    _instance: Optional["AudioStream"] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        # Audio config
        self.sample_rate = getattr(config, 'VAD_SAMPLE_RATE', 16000)
        self.chunk_size = 512  # ~32ms chunks
        self.channels = 1
        self.format = pyaudio.paInt16
        
        # Buffer config - store ~2 seconds of audio
        buffer_seconds = getattr(config, 'AUDIO_BUFFER_SECONDS', 2.0)
        self.buffer_size = int(self.sample_rate * buffer_seconds)
        
        # Circular buffer (thread-safe deque)
        self._buffer = deque(maxlen=self.buffer_size)
        self._buffer_lock = threading.Lock()
        
        # PyAudio instance
        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        
        # Control
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        logger.info(f"AudioStream initialized (buffer: {buffer_seconds}s, rate: {self.sample_rate}Hz)")
    
    def start(self):
        """Start continuous audio capture."""
        if self._running:
            logger.warning("AudioStream already running")
            return
            
        self._running = True
        self._audio = pyaudio.PyAudio()
        
        # Get mic index from config (None means use system default)
        mic_index = getattr(config, 'MIC_INDEX', None)
        
        self._stream = self._audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=mic_index,  # None = system default, 0+ = specific device
            frames_per_buffer=self.chunk_size
        )
        
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        
        logger.info("AudioStream started")
    
    def stop(self):
        """Stop audio capture."""
        self._running = False
        
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
            
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None
            
        if self._audio:
            self._audio.terminate()
            self._audio = None
            
        logger.info("AudioStream stopped")
    
    def _capture_loop(self):
        """Background thread that continuously captures audio."""
        while self._running:
            try:
                data = self._stream.read(self.chunk_size, exception_on_overflow=False)
                samples = np.frombuffer(data, dtype=np.int16)
                
                with self._buffer_lock:
                    self._buffer.extend(samples)
                    
            except Exception as e:
                if self._running:
                    logger.error(f"AudioStream capture error: {e}")
                break
    
    def get_buffer(self) -> bytes:
        """
        Get the entire circular buffer as bytes.
        Used when interruption is detected to capture all recent audio.
        """
        with self._buffer_lock:
            samples = np.array(self._buffer, dtype=np.int16)
        return samples.tobytes()
    
    def get_recent(self, duration_ms: int = 100) -> bytes:
        """
        Get the most recent audio samples.
        
        Args:
            duration_ms: How many milliseconds of audio to retrieve
            
        Returns:
            Audio data as bytes
        """
        num_samples = int(self.sample_rate * duration_ms / 1000)
        
        with self._buffer_lock:
            if len(self._buffer) < num_samples:
                samples = np.array(self._buffer, dtype=np.int16)
            else:
                # Get last N samples
                samples = np.array(
                    [self._buffer[i] for i in range(len(self._buffer) - num_samples, len(self._buffer))],
                    dtype=np.int16
                )
        return samples.tobytes()
    
    def get_recent_float(self, duration_ms: int = 100) -> np.ndarray:
        """
        Get recent audio as normalized float32 array (-1.0 to 1.0).
        Useful for VAD which expects float input.
        """
        data = self.get_recent(duration_ms)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        return samples
    
    @property
    def is_running(self) -> bool:
        return self._running


# Singleton instance
audio_stream = AudioStream()
