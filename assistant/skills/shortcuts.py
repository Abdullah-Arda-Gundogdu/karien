import subprocess
from typing import List
from assistant.skills.base import Skill
from assistant.core.logging_config import logger

class ShortcutsSkill(Skill):
    @property
    def name(self) -> str:
        return "Shortcuts"

    @property
    def description(self) -> str:
        return "Runs Apple Shortcuts."

    @property
    def commands(self) -> List[str]:
        return ["run_shortcut"]

    def execute(self, command: str, params: List[str]) -> bool:
        if not params:
            return False
            
        shortcut_name = " ".join(params)
        logger.info(f"Running Shortcut: {shortcut_name}")
        
        try:
            # shortcuts run "Name"
            subprocess.run(["shortcuts", "run", shortcut_name], check=False)
            return True
        except Exception as e:
            logger.error(f"ShortcutsSkill Error: {e}")
            return False
