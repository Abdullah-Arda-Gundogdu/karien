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
        
        # Ensure minimum length for VAD (at least 512 samples)
        if len(samples) < 512:
            # Pad with zeros
            samples = np.pad(samples, (0, 512 - len(samples)), mode='constant')
        
        audio_tensor = torch.from_numpy(samples)
        
        try:
            with torch.no_grad():
                prob = model(audio_tensor, self.sample_rate).item()
            return float(prob)
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return 0.0
    
    def reset(self):
        """Reset model state (call between utterances if needed)."""
        if self._model is not None:
            try:
                self._model.reset_states()
            except Exception:
                pass  # Some model versions may not have this


# Singleton instance
vad = VAD()
