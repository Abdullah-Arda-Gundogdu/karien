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
        
        tts.speak("Uyandım. Ne istiyorsun?")

        while self.running:
            # 1. Listen
            user_text = stt.listen()
            
            if not user_text:
                continue
                
            if any(phrase in user_text.lower() for phrase in ["goodbye", "shut down", "kapat", "güle güle", "görüşürüz"]):
                tts.speak("Sonunda. Görüşürüz.")
                break

            # 2. Think
            response_full = brain.chat(user_text)
            
            # 3. Parse
            mood, clean_response, cmd_tuple = self.parse_response(response_full)
            logger.info(f"Raw LLM Response: {response_full}")
            logger.info(f"Parsed Mood: {mood}")
            
            # 4. Act
            logger.info(f"Triggering mood: {mood} (awaiting...)")
            await vts.trigger_mood(mood)
            
            # Speak first, then act (or parallel? Serial is safer for now)
            tts.speak(clean_response)
            
            if cmd_tuple:
                cmd, params = cmd_tuple
                executed = False
                for skill in self.skills:
                    if cmd in skill.commands:
                        skill.execute(cmd, params)
                        executed = True
                        break
                if not executed:
                    logger.warning(f"Unknown command: {cmd}")

        await vts.close()
        logger.info("Karien stopped.")


orchestrator = Orchestrator()
