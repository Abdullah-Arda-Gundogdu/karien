import asyncio
import json
import re
from typing import Optional
from assistant.core.logging_config import logger
from assistant.input.stt import stt
from assistant.input.vosk_stt import vosk_stt
from assistant.output.tts import tts
from assistant.output.vts import vts
from assistant.brain.llm import brain

# Lazy load audio components to avoid import delay
_audio_stream = None
_vad = None

def _get_audio_stream():
    global _audio_stream
    if _audio_stream is None:
        from assistant.input.audio_stream import audio_stream
        _audio_stream = audio_stream
    return _audio_stream

def _get_vad():
    global _vad
    if _vad is None:
        from assistant.input.vad import vad
        _vad = vad
    return _vad

class Orchestrator:
    def __init__(self, hooks=None):
        self.running = False
        self.is_active = False # Start in Standby
        self._interrupted = False  # Track if current turn was interrupted
        # Optional UI hooks object (e.g. assistant.ui.voice_service).
        # May define: on_wake(), on_listen(), on_think(), on_mood(mood),
        # on_speak(), on_standby(). All calls are fire-and-forget — a broken
        # or missing hook must never break the voice flow.
        self.hooks = hooks

    def _fire_hook(self, name, *args):
        """Call an optional UI hook without ever raising into the voice loop."""
        hooks = self.hooks
        if hooks is None:
            return
        try:
            fn = getattr(hooks, name, None)
            if fn:
                fn(*args)
        except Exception as e:
            logger.debug(f"UI hook '{name}' failed (ignored): {e}")

    def parse_response(self, text: str):
        """
        Extracts mood tag and command tag.
        Returns (mood, clean_text, (cmd, params))
        """
        mood = "neutral"
        cmd_tuple = None
        
        # Extract Mood
        mood_match = re.search(r"^\s*\[([a-zA-Z_]+)\]\s*", text)
        if mood_match:
            mood = mood_match.group(1).lower()
            text = text[mood_match.end():]

        # Extract Command
        cmd_match = re.search(r"\s*\[CMD:\s*(\w+),\s*(.*?)\]\s*$", text)
        if cmd_match:
            cmd = cmd_match.group(1)
            param = cmd_match.group(2)
            cmd_tuple = (cmd, [param])
            text = text[:cmd_match.start()]
            
        return mood, text.strip(), cmd_tuple

    def play_startup_sound(self):
        """Play startup sound or fallback to TTS."""
        tts.play_sound("startup")
        tts.wait_for_idle()  # Wait for sound to finish before STT starts

    def play_goodbye_sound(self):
        """Play goodbye sound or fallback to TTS."""
        tts.play_sound("goodbye")

    def bring_vts_to_front(self):
        """Brings VTube Studio window to front (Cross-Platform).

        Only acts when the VTS plugin API is actually connected. The old
        'tell application ... to activate' form LAUNCHED VTube Studio (via
        Steam!) when it wasn't running and blocked the event loop for the
        entire cold start (~30s of silence after the wake word).
        """
        if not vts.connected:
            logger.debug("VTS not connected; skipping bring-to-front")
            return

        import sys
        import subprocess

        try:
            if sys.platform == "darwin":
                # System Events targets a RUNNING process — it can never
                # launch the app (second safety net against a stale
                # vts.connected flag). frontmost also un-hides it.
                cmd = ('tell application "System Events" to '
                       'set frontmost of process "VTube Studio" to true')
                subprocess.run(["osascript", "-e", cmd],
                               check=True, timeout=3, capture_output=True)
                logger.info("VTube Studio brought to front (macOS).")
                
            elif sys.platform == "win32":
                # Windows (pywinauto)
                try:
                    from pywinauto import Desktop
                    
                    # Attempt to find window by title
                    # Note: Title might vary, usually "VTube Studio"
                    app = Desktop(backend="uia").windows(title_re=".*VTube Studio.*")
                    if app:
                        window = app[0]
                        if window.is_minimized():
                            window.restore()
                        window.set_focus()
                        logger.info("VTube Studio brought to front (Windows).")
                    else:
                         logger.warning("VTube Studio window not found.")
                except ImportError:
                    logger.error("pywinauto not installed. Cannot control window.")
                    
        except Exception as e:
            logger.warning(f"Failed to bring VTS to front: {e}")

    def hide_vts(self):
        """Hides/Minimizes VTube Studio window (Cross-Platform)."""
        if not vts.connected:
            logger.debug("VTS not connected; skipping hide")
            return

        import sys
        import subprocess

        try:
            if sys.platform == "darwin":
                # macOS (AppleScript)
                cmd = 'tell application "System Events" to set visible of process "VTube Studio" to false'
                subprocess.run(["osascript", "-e", cmd],
                               check=True, timeout=3, capture_output=True)
                logger.info("VTube Studio hidden (macOS).")
                
            elif sys.platform == "win32":
                # Windows (pywinauto) - Minimize
                try:
                    from pywinauto import Desktop
                    app = Desktop(backend="uia").windows(title_re=".*VTube Studio.*")
                    if app:
                        window = app[0]
                        window.minimize()
                        logger.info("VTube Studio minimized (Windows).")
                except ImportError:
                    pass # error logged in bring_to_front already
                    
        except Exception as e:
            logger.warning(f"Failed to hide VTS: {e}")

    async def run(self):
        # Quiet down harmless transport-cleanup noise: abruptly closed
        # websockets (Deepgram session end, VTS absent) surface as EOFError/
        # ConnectionResetError inside asyncio callbacks and would otherwise
        # print scary tracebacks into the UI console.
        loop = asyncio.get_running_loop()

        def _quiet_exception_handler(loop, context):
            exc = context.get("exception")
            if isinstance(exc, (EOFError, ConnectionResetError, BrokenPipeError)):
                logger.debug(f"Network cleanup noise ignored: {exc}")
                return
            loop.default_exception_handler(context)

        loop.set_exception_handler(_quiet_exception_handler)

        # Register Skills
        from assistant.skills import LauncherSkill, SystemSkill, ShortcutsSkill, VisionSkill
        
        self.skills = [LauncherSkill(), SystemSkill(), ShortcutsSkill(), VisionSkill()]
        
        self.running = True
        
        # Start continuous audio capture for VAD and interruption
        audio_stream = _get_audio_stream()
        audio_stream.start()
        logger.info("Audio stream started for VAD")
        
        # Connect to VTS
        await vts.connect()
        
        # Initialize MCP servers in background (non-blocking)
        from assistant.mcp.manager import mcp_manager
        mcp_manager.ensure_default_tools()  # Skills + Google as internal tools
        asyncio.create_task(mcp_manager.initialize())
        
        # NOTE: We don't play startup sound at very beginning anymore, 
        # we wait for "Hey Karien".
        # Or should we play it once to say "I'm ready"?
        # User said: "When I say hey karien the assistant should start running."
        # Assume silent start, waiting for wake word.
        logger.info("Karien started. (Standby)")
        
        # Ensure VTS is hidden at startup (off the loop thread — osascript
        # can block for seconds)
        await asyncio.to_thread(self.hide_vts)

        while self.running:
            try:
                if not self.is_active:
                    # --- STANDBY MODE ---
                    # Listen locally for wake word
                    logger.info("Status: Standby. Listening for 'Hey Karien'...")
                    # Run blocking vosk listener in thread to avoid freezing asyncio loop
                    # Turkish model keywords candidates - using "kariyer" as proxy for "karien"
                    detected = await asyncio.to_thread(vosk_stt.listen_for_wakeword, ["hey kariyer", "merhaba kariyer"])
                    
                    if detected:
                        logger.info("Wake Word Detected! Switching to Active Mode.")
                        self.is_active = True
                        self._fire_hook("on_wake")
                        # Chime FIRST (user feedback must be instant); VTS
                        # window juggling happens off the loop thread after.
                        self.play_startup_sound()
                        await asyncio.to_thread(self.bring_vts_to_front)
                    else:
                        # If listen returned False (e.g. error/timeout/interrupt), check if running
                        if not self.running: break
                        await asyncio.sleep(1)
                        
                else:
                    # --- ACTIVE MODE ---
                    await self._run_active_turn()
                    
            except Exception as e:
                logger.error(f"Critical Error in Orchestrator Loop: {e}", exc_info=True)
                tts.play_sound("error")  # Pre-recorded error message
                self.is_active = False # Fallback to standby
                await asyncio.sleep(3) # Breathe
        
        # Cleanup on exit
        audio_stream = _get_audio_stream()
        audio_stream.stop()
        
        # Shutdown MCP servers
        from assistant.mcp.manager import mcp_manager
        await mcp_manager.shutdown()
        
        await vts.close()
        logger.info("Karien stopped.")

    async def _run_active_turn(self):
        # 1. Listen (Deepgram)
        self._fire_hook("on_listen")
        user_text = await stt.listen()

        if not user_text:
            return

        # 2. Think & Act (Streaming)
        logger.info("Thinking...")
        self._fire_hook("on_think")

        # Reset state for new turn
        full_response_buffer = ""
        sentence_buffer = ""
        mood_detected = False
        speak_started = False
        pending_tool_calls = []
        
        # Start streaming
        stream = brain.chat_stream(user_text)
        
        for chunk_type, chunk_data in stream:
            if chunk_type == "CONTENT":
                # Handle Text/Speech
                token = chunk_data
                full_response_buffer += token
                sentence_buffer += token
                
                # Check for Mood at the start (if not yet found)
                if not mood_detected:
                    mood_match = re.search(r"^\s*\[([a-zA-Z_]+)\]", full_response_buffer)
                    if mood_match:
                        mood = mood_match.group(1).lower()
                        logger.info(f"Detected Mood: {mood}")
                        self._fire_hook("on_mood", mood)
                        await vts.trigger_mood(mood)
                        mood_detected = True

                        # Remove mood tag from sentence buffer so we don't speak it
                        sentence_buffer = sentence_buffer.replace(mood_match.group(0), "", 1)

                # Check for sentence delimiters
                if re.search(r"[.!?]\s", sentence_buffer):
                    parts = re.split(r"([.!?]\s)", sentence_buffer, 1)
                    if len(parts) >= 2:
                        sentence = parts[0] + parts[1]
                        remainder = "".join(parts[2:])

                        # Clean mood tags if any remain
                        clean_sentence = re.sub(r"\[[a-zA-Z_]+\]", "", sentence).strip()
                        if clean_sentence:
                            if not speak_started:
                                speak_started = True
                                self._fire_hook("on_speak")
                            tts.speak_async(clean_sentence)
                        sentence_buffer = remainder

            elif chunk_type == "TOOL":
                # Handle Tool Call (received at end of stream usually)
                func_name, args_str = chunk_data
                try:
                    args = json.loads(args_str) if args_str else {}
                    pending_tool_calls.append((func_name, args))
                    logger.info(f"Received Tool Call: {func_name} with {args}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode arguments for {func_name}: {args_str}")

        # End of stream.
        # Speak remaining text
        remaining_text = sentence_buffer.strip()
        if remaining_text:
            clean_remaining = re.sub(r"\[[a-zA-Z_]+\]", "", remaining_text).strip()
            if clean_remaining:
                if not speak_started:
                    speak_started = True
                    self._fire_hook("on_speak")
                tts.speak_async(clean_remaining)

        # 3. Monitor for interruption while TTS is playing
        # This runs concurrently and will stop TTS if user speaks
        interrupted_audio = await self._monitor_for_interruption()
        
        if interrupted_audio:
            # User interrupted! Process their speech immediately
            logger.info("Processing interrupted speech...")
            # Use buffered audio to capture what user said
            user_text = await stt.listen_with_prepend(interrupted_audio)
            if user_text:
                logger.info(f"Interrupted with: {user_text}")
                # Recursively handle this new input (skip tool execution)
                await self._handle_user_input(user_text)
            return  # Skip tool execution for interrupted turn

        # 4. Execute Tools (only if not interrupted)
        await self._execute_tools(pending_tool_calls)
        
        logger.debug("Waiting for TTS to finish...")
        tts.wait_for_idle()

    async def _execute_tools(self, pending_tool_calls: list):
        """
        Act on the orchestration signals collected from the brain's stream.

        NOTE: Data tools (open_app, Google, MCP servers, ...) are executed
        by the Brain itself inside chat_stream — it needs the results to
        continue the LLM loop. Executing them here again caused every
        side-effectful tool (e.g. add_calendar_event) to run TWICE.
        The orchestrator only handles the two host-level signals:
        stop_listening (state change) and analyze_screen (vision flow).
        """
        for func_name, args in pending_tool_calls:
            # === Host-level signals ===

            if func_name == "stop_listening":
                logger.info("LLM requested stop_listening. Switching to Standby.")
                tts.wait_for_idle()
                self.play_goodbye_sound()
                await asyncio.to_thread(self.hide_vts)
                self.is_active = False
                self._fire_hook("on_standby")
                continue

            if func_name == "analyze_screen":
                # Special Vision Handler - requires LLM callback
                logger.info("Vision Tool Triggered")
                
                # Talk while processing
                tts.play_sound("analyzing")  # Pre-recorded "Hmm, dur bakalım..."
                
                # Capture
                vision_skill = next((s for s in self.skills if s.name == "Vision"), None)
                if vision_skill:
                    b64_img = vision_skill.capture_screen()
                    if b64_img:
                        # Analyze
                        description = brain.analyze_image(b64_img)
                        # Speak Result
                        tts.speak_async(description)
                    else:
                        tts.play_sound("screenshot_error")  # Pre-recorded error
                else:
                    logger.error("Vision skill not found!")
                continue

            # === Data tools: already executed by the Brain — log only ===
            logger.debug(f"Tool {func_name} was executed by the Brain; no host action.")

    async def _monitor_for_interruption(self) -> Optional[bytes]:
        """
        Monitor for user speech while TTS is playing.
        Returns buffered audio if interruption detected, None otherwise.
        """
        vad = _get_vad()
        audio_stream = _get_audio_stream()
        
        consecutive_speech_frames = 0
        required_frames = 3  # Require 3 consecutive speech frames (~150ms) to confirm interruption
        
        while tts.is_playing():
            # Check VAD on recent audio
            try:
                recent_audio = audio_stream.get_recent(100)  # last 100ms
                if vad.is_speech(recent_audio):
                    consecutive_speech_frames += 1
                    if consecutive_speech_frames >= required_frames:
                        # Confirmed interruption!
                        logger.info("Interruption detected - stopping TTS")
                        tts.stop_playback()
                        # Return full buffer to capture the interruption words
                        return audio_stream.get_buffer()
                else:
                    consecutive_speech_frames = 0
            except Exception as e:
                logger.debug(f"Error during interruption check: {e}")
            
            await asyncio.sleep(0.05)  # Check every 50ms
        
        return None  # No interruption

    async def _handle_user_input(self, user_text: str):
        """
        Handle user input (used for both normal turns and interruption).
        This is the core LLM interaction without interruption monitoring.
        """
        logger.info("Thinking...")
        self._fire_hook("on_think")

        full_response_buffer = ""
        sentence_buffer = ""
        mood_detected = False
        speak_started = False
        pending_tool_calls = []

        stream = brain.chat_stream(user_text)

        for chunk_type, chunk_data in stream:
            if chunk_type == "CONTENT":
                token = chunk_data
                full_response_buffer += token
                sentence_buffer += token

                if not mood_detected:
                    mood_match = re.search(r"^\s*\[([a-zA-Z_]+)\]", full_response_buffer)
                    if mood_match:
                        mood = mood_match.group(1).lower()
                        logger.info(f"Detected Mood: {mood}")
                        self._fire_hook("on_mood", mood)
                        await vts.trigger_mood(mood)
                        mood_detected = True
                        sentence_buffer = sentence_buffer.replace(mood_match.group(0), "", 1)

                if re.search(r"[.!?]\s", sentence_buffer):
                    parts = re.split(r"([.!?]\s)", sentence_buffer, 1)
                    if len(parts) >= 2:
                        sentence = parts[0] + parts[1]
                        remainder = "".join(parts[2:])
                        clean_sentence = re.sub(r"\[[a-zA-Z_]+\]", "", sentence).strip()
                        if clean_sentence:
                            if not speak_started:
                                speak_started = True
                                self._fire_hook("on_speak")
                            tts.speak_async(clean_sentence)
                        sentence_buffer = remainder

            elif chunk_type == "TOOL":
                func_name, args_str = chunk_data
                try:
                    args = json.loads(args_str) if args_str else {}
                    pending_tool_calls.append((func_name, args))
                    logger.info(f"Received Tool Call: {func_name} with {args}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to decode arguments for {func_name}: {args_str}")

        # Speak remaining
        remaining_text = sentence_buffer.strip()
        if remaining_text:
            clean_remaining = re.sub(r"\[[a-zA-Z_]+\]", "", remaining_text).strip()
            if clean_remaining:
                if not speak_started:
                    speak_started = True
                    self._fire_hook("on_speak")
                tts.speak_async(clean_remaining)
        
        # Wait for TTS (no interruption monitoring here - it's a follow-up response)
        tts.wait_for_idle()
        
        # Execute Tools using shared helper
        await self._execute_tools(pending_tool_calls)
        
        # Wait for any additional TTS from tool execution
        tts.wait_for_idle()

orchestrator = Orchestrator()

