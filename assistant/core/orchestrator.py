import asyncio
import re
from assistant.core.logging_config import logger
from assistant.input.stt import stt
from assistant.input.vosk_stt import vosk_stt
from assistant.output.tts import tts
from assistant.output.vts import vts
from assistant.brain.llm import brain

class Orchestrator:
    def __init__(self):
        self.running = False
        self.is_active = False # Start in Standby

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
        from assistant.core.config import config
        import subprocess
        startup_file = config.ASSETS_DIR / "startup.mp3"
        
        if startup_file.exists():
            logger.info(f"Playing startup audio: {startup_file}")
            subprocess.run(["afplay", str(startup_file)])
        else:
            tts.speak("Selam! Ben Karien! Sana nasıl yardımcı olabilirim?")

    def play_goodbye_sound(self):
        from assistant.core.config import config
        import subprocess
        goodbye_file = config.ASSETS_DIR / "goodbye.mp3"
        
        if goodbye_file.exists():
            logger.info(f"Playing goodbye audio: {goodbye_file}")
            subprocess.run(["afplay", str(goodbye_file)])
        else:
            tts.speak("Görüşürüz.")

    def bring_vts_to_front(self):
        """Brings VTube Studio window to front using AppleScript."""
        import subprocess
        try:
            # AppleScript to activate the application (brings to front)
            subprocess.run(["osascript", "-e", 'tell application "VTube Studio" to activate'], check=True)
            logger.info("VTube Studio brought to front.")
        except Exception as e:
            logger.warning(f"Failed to bring VTS to front: {e}")

    def hide_vts(self):
        """Hides VTube Studio window using AppleScript."""
        import subprocess
        try:
            # AppleScript to hide the application process
            cmd = 'tell application "System Events" to set visible of process "VTube Studio" to false'
            subprocess.run(["osascript", "-e", cmd], check=True)
            logger.info("VTube Studio hidden.")
        except Exception as e:
            logger.warning(f"Failed to hide VTS: {e}")

    async def run(self):
        # Register Skills
        from assistant.skills.launcher import LauncherSkill
        from assistant.skills.system import SystemSkill
        from assistant.skills.shortcuts import ShortcutsSkill
        
        self.skills = [LauncherSkill(), SystemSkill(), ShortcutsSkill()]
        
        self.running = True
        
        # Connect to VTS
        await vts.connect()
        
        # NOTE: We don't play startup sound at very beginning anymore, 
        # we wait for "Hey Karien".
        # Or should we play it once to say "I'm ready"?
        # User said: "When I say hey karien the assistant should start running."
        # Assume silent start, waiting for wake word.
        logger.info("Karien started. (Standby)")
        
        # Ensure VTS is hidden at startup
        self.hide_vts()

        while self.running:
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
                    self.bring_vts_to_front()
                    self.play_startup_sound()
                else:
                    # If listen returned False (e.g. error), sleep briefly to avoid spin loop
                    await asyncio.sleep(1)
                    
            else:
                # --- ACTIVE MODE ---
                # 1. Listen (Deepgram)
                user_text = await stt.listen()
                
                if not user_text:
                    continue
                
                # Legacy keyword checks REMOVED to solve "Close YouTube" issue.
                # Now handled by LLM via [CMD: stop_listening, nan].
                
                # 2. Think & Act (Streaming)
                logger.info("Thinking...")
                
                # Reset state for new turn
                full_response_buffer = ""
                sentence_buffer = ""
                mood_detected = False
                
                # Start streaming
                stream = brain.chat_stream(user_text)
                
                for token in stream:
                    full_response_buffer += token
                    sentence_buffer += token
                    
                    # Check for Mood at the start (if not yet found)
                    if not mood_detected:
                        mood_match = re.search(r"^\s*\[([a-zA-Z_]+)\]", full_response_buffer)
                        if mood_match:
                            mood = mood_match.group(1).lower()
                            logger.info(f"Detected Mood: {mood}")
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
                            
                            if "[" not in sentence:
                                # Double check and clean any remaining mood tags
                                clean_sentence = re.sub(r"\[[a-zA-Z_]+\]", "", sentence).strip()
                                if clean_sentence:
                                    tts.speak_async(clean_sentence)
                                sentence_buffer = remainder
                            else:
                                # If sentence contains a bracket, it might be a split tag. 
                                # But we also want to catch tags inside the sentence.
                                # Let's clean it aggressively.
                                clean_sentence = re.sub(r"\[[a-zA-Z_]+\]", "", sentence).strip()
                                if clean_sentence and "[" not in clean_sentence: # confirm no partial tags
                                    tts.speak_async(clean_sentence)
                                    sentence_buffer = remainder
                                else:
                                    # wait for more data if partial tag
                                    pass

                # End of stream.
                remaining_text = sentence_buffer.strip()
                cmd_match = re.search(r"\[CMD:.*?\]", remaining_text)
                if cmd_match:
                    remaining_speakable = remaining_text[:cmd_match.start()].strip()
                    if remaining_speakable:
                        clean_remaining = re.sub(r"\[[a-zA-Z_]+\]", "", remaining_speakable).strip()
                        if clean_remaining:
                            tts.speak_async(clean_remaining)
                else:
                    if remaining_text:
                        clean_remaining = re.sub(r"\[[a-zA-Z_]+\]", "", remaining_text).strip()
                        if clean_remaining:
                            tts.speak_async(clean_remaining)

                # 3. Parse & Execute Command
                _, _, cmd_tuple = self.parse_response(full_response_buffer)
                
                if cmd_tuple:
                    cmd, params = cmd_tuple
                    logger.info(f"Executing command: {cmd} with params: {params}")
                    
                    # 1. Handle Core Orchestrator Commands (Termination)
                    if cmd == "stop_listening":
                        logger.info("LLM requested stop_listening. Switching to Standby.")
                        self.play_goodbye_sound()
                        tts.wait_for_idle() # Let her say goodbye
                        self.hide_vts()
                        self.is_active = False
                        # No continue needed here as loop ends after TTS
                    
                    elif cmd == "close_app":
                         # Quick implementation for close app
                         # params is a list, e.g. ['YouTube']
                         app_name = params[0] if params else ""
                         if app_name:
                             import subprocess
                             logger.info(f"Closing app: {app_name}")
                             try:
                                 # AppleScript to quit app
                                 script = f'tell application "{app_name}" to quit'
                                 subprocess.run(["osascript", "-e", script])
                             except Exception as e:
                                 logger.error(f"Failed to close app {app_name}: {e}")

                    # 2. Handle Skill Commands
                    else:
                        executed = False
                        for skill in self.skills:
                            if cmd in skill.commands:
                                skill.execute(cmd, params)
                                executed = True
                                break
                        if not executed:
                            logger.warning(f"Unknown command: {cmd}")
                
                logger.debug("Waiting for TTS to finish...")
                tts.wait_for_idle()

        await vts.close()
        logger.info("Karien stopped.")

orchestrator = Orchestrator()
