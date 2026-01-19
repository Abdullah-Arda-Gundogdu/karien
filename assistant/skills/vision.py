import base64
import io
import os
import datetime
from typing import List, Optional
from assistant.skills.base import Skill
from assistant.core.logging_config import logger

try:
    import pyautogui
except ImportError:
    pyautogui = None

class VisionSkill(Skill):
    @property
    def name(self) -> str:
        return "Vision"

    @property
    def description(self) -> str:
        return "Allows the assistant to see and analyze the user's screen."

    @property
    def commands(self) -> List[str]:
        return ["analyze_screen"]

    def execute(self, command: str, params: List[str]) -> bool:
        # NOTE: This skill is special. It doesn't just "execute", 
        # it returns data (the image) that the Brain needs to process.
        # But for the standard 'execute' interface, we might just return True 
        # to indicate "I handled the command (by doing nothing here, Orchestrator handles flow)" 
        # or we use this method to actually capture and save a temp file.
        
        # However, for the 'analyze_screen' tool flow we designed:
        # The Orchestrator calls the LLM, LLM calls 'analyze_screen' tool.
        # The Orchestrator intercepts this tool call, sees it is 'analyze_screen',
        # and triggers the Vision flow directly.
        # So this execute method might be unused or just a placeholder.
        return True

    def capture_screen(self) -> Optional[str]:
        """
        Captures the screen and returns it as a base64 encoded string.
        Returns None if capture failed.
        """
        if not pyautogui:
            logger.error("pyautogui not installed.")
            return None

        try:
            # Create a temporary file buffer
            screenshot = pyautogui.screenshot()
            
            # Save to bytes
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format="PNG")
            img_bytes = img_buffer.getvalue()
            
            # Encode base64
            base64_str = base64.b64encode(img_bytes).decode('utf-8')
            
            # Optional: Save to debug folder
            # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # screenshot.save(f"debug_screen_{timestamp}.png")
            
            return base64_str
        except Exception as e:
            logger.error(f"Screen Capture Failed: {e}")
            # On Mac, this might be a permission error
            if "Permission denied" in str(e):
                logger.error("Check macOS Screen Recording permissions!")
            return None
