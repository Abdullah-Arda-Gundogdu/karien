#!/usr/bin/env python3
"""
VAD (Voice Activity Detection) Visualizer
==========================================
Real-time visualization of Silero VAD decisions.

Run this script to see:
- Live audio waveform
- VAD speech probability (0.0 to 1.0)  
- Current decision (SPEECH / SILENCE)

Usage:
    python scripts/vad_visualizer.py

Press Ctrl+C to stop.
"""

import sys
import time
import threading
import numpy as np

# Check for required dependencies
try:
    import torch
    import pyaudio
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install torch torchaudio pyaudio")
    sys.exit(1)

# Audio settings
SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # ~32ms chunks for responsive VAD
CHANNELS = 1
FORMAT = pyaudio.paInt16

# VAD settings
VAD_THRESHOLD = 0.5  # Adjust this to tune sensitivity

class VADVisualizer:
    def __init__(self):
        self.running = False
        self.speech_prob = 0.0
        self.is_speech = False
        self.audio_level = 0.0
        
        # Load Silero VAD
        print("Loading Silero VAD model...")
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
        (self.get_speech_timestamps,
         self.save_audio,
         self.read_audio,
         self.VADIterator,
         self.collect_chunks) = utils
        
        print("Model loaded!")
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
    def start(self):
        self.running = True
        
        # Open mic stream
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        # Start processing thread
        self.thread = threading.Thread(target=self._process_audio)
        self.thread.start()
        
        # Display loop (main thread)
        self._display_loop()
        
    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()
        
    def _process_audio(self):
        """Background thread that reads audio and runs VAD."""
        while self.running:
            try:
                # Read audio chunk
                data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # Convert to numpy then torch tensor
                audio_np = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_np)
                
                # Calculate audio level (RMS)
                self.audio_level = float(np.sqrt(np.mean(audio_np ** 2)))
                
                # Run VAD
                self.speech_prob = float(self.model(audio_tensor, SAMPLE_RATE).item())
                self.is_speech = self.speech_prob >= VAD_THRESHOLD
                
            except Exception as e:
                print(f"\nError: {e}")
                break
                
    def _display_loop(self):
        """Main thread display loop."""
        print("\n" + "=" * 60)
        print("  VAD VISUALIZER - Press Ctrl+C to stop")
        print("=" * 60)
        print(f"  Threshold: {VAD_THRESHOLD}")
        print("-" * 60)
        
        try:
            while self.running:
                # Build visualization bar
                bar_width = 40
                prob_bar = int(self.speech_prob * bar_width)
                threshold_pos = int(VAD_THRESHOLD * bar_width)
                
                # Create bar with threshold marker
                bar = ""
                for i in range(bar_width):
                    if i == threshold_pos:
                        bar += "|"  # Threshold marker
                    elif i < prob_bar:
                        bar += "█" if self.is_speech else "▒"
                    else:
                        bar += "░"
                
                # Status indicator
                status = "\033[92m SPEECH \033[0m" if self.is_speech else "\033[90m silence \033[0m"
                
                # Audio level indicator
                level_bar = "▁▂▃▄▅▆▇█"
                level_idx = min(int(self.audio_level * 50), len(level_bar) - 1)
                level_char = level_bar[level_idx]
                
                # Print line (carriage return to overwrite)
                print(f"\r  {level_char} [{bar}] {self.speech_prob:.2f} {status}", end="", flush=True)
                
                time.sleep(0.05)  # 50ms refresh rate
                
        except KeyboardInterrupt:
            print("\n\nStopping...")
            
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           Silero VAD Real-Time Visualizer                 ║
    ║                                                           ║
    ║  This tool helps you tune the VAD_THRESHOLD setting.      ║
    ║  Speak into your microphone and observe:                  ║
    ║    - The bar fills based on speech probability            ║
    ║    - | marks the threshold                                ║
    ║    - Green "SPEECH" when above threshold                  ║
    ║    - Gray "silence" when below                            ║
    ║                                                           ║
    ║  Goal: Find a threshold where:                            ║
    ║    - Your voice triggers SPEECH                           ║
    ║    - TV/background noise stays in silence                 ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    visualizer = VADVisualizer()
    try:
        visualizer.start()
    finally:
        visualizer.stop()

if __name__ == "__main__":
    main()
