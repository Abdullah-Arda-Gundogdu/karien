import asyncio
import re
from assistant.core.logging_config import logger
from assistant.input.stt import stt
from assistant.output.tts import tts
from assistant.output.vts import vts
from assistant.brain.llm import brain

class Orchestrator:
    def __init__(self):
        self.running = False


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

    async def run(self):
        # Register Skills
        from assistant.skills.launcher import LauncherSkill
        from assistant.skills.system import SystemSkill
        from assistant.skills.shortcuts import ShortcutsSkill
        
        self.skills = [LauncherSkill(), SystemSkill(), ShortcutsSkill()]
        
        self.running = True

        logger.info("Karien started. Say something...")
        
        # Connect to VTS
        await vts.connect()
        
        # Play startup sound if available to save costs
        from assistant.core.config import config
        import subprocess
        startup_file = config.ASSETS_DIR / "startup.mp3"
        
        if startup_file.exists():
            logger.info(f"Playing startup audio: {startup_file}")
            subprocess.run(["afplay", str(startup_file)])
        else:
            tts.speak("Selam! Ben Karien! Sana nasıl yardımcı olabilirim?")

        while self.running:
            # 1. Listen
            user_text = await stt.listen()
            
            if not user_text:
                continue
                
            if any(phrase in user_text.lower() for phrase in ["goodbye", "shut down", "kapat", "güle güle", "görüşürüz"]):
                tts.speak("Sonunda. Görüşürüz.")
                break

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
                        # We only remove it from sentence_buffer, full_response_buffer keeps it for history/debug
                        sentence_buffer = sentence_buffer.replace(mood_match.group(0), "", 1)

                # Check for sentence delimiters
                # We look for . ? ! followed by space or end of string
                # Note: This is a simple heuristic.
                if re.search(r"[.!?]\s", sentence_buffer):
                    # We have a sentence!
                    # Split by the delimiter to get the sentence and the remainder
                    parts = re.split(r"([.!?]\s)", sentence_buffer, 1)
                    if len(parts) >= 2:
                        sentence = parts[0] + parts[1] # "Hello." + " "
                        remainder = "".join(parts[2:]) # Rest
                        
                        # Clean up sentence (remove potential CMD tags if they appeared mid-stream, though unlikely given prompt instructions)
                        # Actually CMD tags specified to be at END.
                        # But simpler: just speak what we have if it's not a tag.
                        
                        # Filter out potential partial tags if any (basic safety)
                        if "[" not in sentence:
                            tts.speak_async(sentence.strip())
                            sentence_buffer = remainder
                        else:
                            # If we see a bracket, it might be a start of a command or mood (if late). 
                            # If it's a command, we don't speak it.
                            # So we wait until we are sure.
                            pass

            # End of stream.
            # 1. Speak any remaining text in buffer (if not a command)
            remaining_text = sentence_buffer.strip()
            # Remove Command tag if present
            cmd_match = re.search(r"\[CMD:.*?\]", remaining_text)
            if cmd_match:
                remaining_speakable = remaining_text[:cmd_match.start()].strip()
                if remaining_speakable:
                    tts.speak_async(remaining_speakable)
            else:
                if remaining_text:
                    tts.speak_async(remaining_text)

            # 3. Parse & Execute Command (using the full response)
            _, _, cmd_tuple = self.parse_response(full_response_buffer)
            
            if cmd_tuple:
                cmd, params = cmd_tuple
                logger.info(f"Executing command: {cmd} with params: {params}")
                executed = False
                for skill in self.skills:
                    if cmd in skill.commands:
                        skill.execute(cmd, params)
                        executed = True
                        break
                if not executed:
                    logger.warning(f"Unknown command: {cmd}")
            
            # Wait for TTS to finish speaking before listening again
            # This prevents the mic from picking up the assistant's own voice
            logger.debug("Waiting for TTS to finish...")
            tts.wait_for_idle()

        await vts.close()
        logger.info("Karien stopped.")


orchestrator = Orchestrator()
