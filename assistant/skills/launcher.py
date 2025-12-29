import subprocess
import webbrowser
import platform
from typing import List
from assistant.skills.base import Skill
from assistant.core.logging_config import logger

class LauncherSkill(Skill):
    @property
    def name(self) -> str:
        return "Launcher"

    @property
    def description(self) -> str:
        return "Opens applications and URLs."

    @property
    def commands(self) -> List[str]:
        return ["open_app", "open_url"]

    def execute(self, command: str, params: List[str]) -> bool:
        if not params:
            logger.warning("LauncherSkill: No parameters provided.")
            return False
            
        target = " ".join(params)
        
        try:
            if command == "open_app":
                logger.info(f"Launching app: {target}")
                if platform.system() == "Darwin": # macOS
                    subprocess.run(["open", "-a", target], check=False)
                    return True
                else:
                    logger.warning("App launching only supported on macOS.")
                    return False
                    
            elif command == "open_url":
                logger.info(f"Opening URL: {target}")
                if not target.startswith("http"):
                    target = "https://" + target
                webbrowser.open(target)
                return True
                
        except Exception as e:
            logger.error(f"LauncherSkill Error: {e}")
            return False
        
        return False
