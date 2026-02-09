"""
Voice Activity Detection (VAD) Module
======================================
Uses Silero VAD for accurate speech detection.
Cross-platform compatible (Windows, macOS, Linux).
"""

import threading
from typing import Optional, Union
import numpy as np
from assistant.core.logging_config import logger
from assistant.core.config import config

# Lazy load torch to avoid import overhead
_torch = None
_model = None
_model_lock = threading.Lock()


def _get_torch():
    """Lazy load torch module."""
    global _torch
    if _torch is None:
        import torch
        _torch = torch
    return _torch


def _get_model():
    """Load Silero VAD model (singleton, thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                torch = _get_torch()
                logger.info("Loading Silero VAD model...")
                _model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False
                )
                logger.info("Silero VAD model loaded")
    return _model


class VAD:
    """
    Voice Activity Detection wrapper using Silero VAD.
    
    Usage:
        from assistant.input.vad import vad
        
        if vad.is_speech(audio_bytes):
            print("Speech detected!")
    """
    
    def __init__(self):
        self.sample_rate = getattr(config, 'VAD_SAMPLE_RATE', 16000)
        self.threshold = getattr(config, 'VAD_THRESHOLD', 0.5)
        self._model: Optional[object] = None
        
    def _ensure_model(self):
        """Ensure model is loaded."""
        if self._model is None:
            self._model = _get_model()
        return self._model
    
    def is_speech(self, audio_data: Union[bytes, np.ndarray]) -> bool:
        """
        Check if audio chunk contains speech.
        
        Args:
            audio_data: Either raw bytes (int16) or numpy float32 array
            
        Returns:
            True if speech is detected above threshold
        """
        prob = self.get_speech_probability(audio_data)
        return prob >= self.threshold
    
    def get_speech_probability(self, audio_data: Union[bytes, np.ndarray]) -> float:
        """
        Get speech probability for audio chunk.
        
        Args:
            audio_data: Either raw bytes (int16) or numpy float32 array
            
        Returns:
            Speech probability (0.0 to 1.0)
        """
        torch = _get_torch()
        model = self._ensure_model()
        
        # Convert to float tensor
        if isinstance(audio_data, bytes):
            samples = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
        elif isinstance(audio_data, np.ndarray):
            if audio_data.dtype == np.int16:
                samples = audio_data.astype(np.float32) / 32768.0
            else:
                samples = audio_data.astype(np.float32)
        else:
            raise ValueError(f"Unsupported audio data type: {type(audio_data)}")
        
        # The Silero VAD model (v4+) requires strict input sizes:
        # 512 samples for 16000Hz, 256 for 8000Hz.
        # We need to chunk the input if it's larger than the supported window.
        window_size = 512 if self.sample_rate == 16000 else 256
        
        # If input is smaller than window, pad it
        if len(samples) < window_size:
            samples = np.pad(samples, (0, window_size - len(samples)), mode='constant')
            
        probs = []
        # Process in chunks
        for i in range(0, len(samples), window_size):
            chunk = samples[i:i + window_size]
            
            # Pad last chunk if incomplete
            if len(chunk) < window_size:
                chunk = np.pad(chunk, (0, window_size - len(chunk)), mode='constant')
                
            audio_tensor = torch.from_numpy(chunk)
            
            try:
                with torch.no_grad():
                    # model(...) returns a tensor, use .item() to get float
                    out = model(audio_tensor, self.sample_rate)
                    probs.append(out.item())
            except Exception as e:
                logger.error(f"VAD inference error: {e}")
                
        # Return the maximum probability found in any chunk
        return float(max(probs)) if probs else 0.0
    
    def reset(self):
        """Reset model state (call between utterances if needed)."""
        if self._model is not None:
            try:
                self._model.reset_states()
            except Exception:
                pass  # Some model versions may not have this


# Singleton instance
vad = VAD()
