import subprocess
import datetime
import os
from typing import List
from assistant.skills.base import Skill
from assistant.core.logging_config import logger

class SystemSkill(Skill):
    @property
    def name(self) -> str:
        return "System"

    @property
    def description(self) -> str:
        return "Controls system functions like screenshot and volume."

    @property
    def commands(self) -> List[str]:
        return ["take_screenshot", "set_volume"]

    def execute(self, command: str, params: List[str]) -> bool:
        try:
            if command == "take_screenshot":
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                # Save to desktop by default or current dir
                # Let's save to current dir for now to avoid permission spam if possible, or desktop is better for user visibility
                path = os.path.expanduser(f"~/Desktop/{filename}")
                logger.info(f"Taking screenshot: {path}")
                subprocess.run(["screencapture", "-x", path], check=True)
                return True

            elif command == "set_volume":
                if not params:
                    return False
                vol = params[0] # 0-100
                logger.info(f"Setting volume to: {vol}")
                subprocess.run(["osascript", "-e", f"set volume output volume {vol}"], check=False)
                return True
                
        except Exception as e:
            logger.error(f"SystemSkill Error: {e}")
            return False
            
        return False
