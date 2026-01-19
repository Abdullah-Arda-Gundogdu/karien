import subprocess
import webbrowser
import platform
import os
from typing import List
from assistant.skills.base import Skill
from assistant.core.logging_config import logger

class LauncherSkill(Skill):
    @property
    def name(self) -> str:
        return "Launcher"

    @property
    def description(self) -> str:
        return "Opens and closes applications and URLs."

    @property
    def commands(self) -> List[str]:
        return ["open_app", "close_app", "open_url"]

    def execute(self, command: str, params: List[str]) -> bool:
        if not params:
            logger.warning("LauncherSkill: No parameters provided.")
            return False
            
        target = " ".join(params)
        
        try:
            if command == "open_app":
                return self._open_app(target)
            elif command == "close_app":
                return self._close_app(target)
            elif command == "open_url":
                return self._open_url(target)
        except Exception as e:
            logger.error(f"LauncherSkill Error: {e}")
            return False
        
        return False

    def _open_app(self, app_name: str) -> bool:
        """Opens an application by name (cross-platform)."""
        logger.info(f"Launching app: {app_name}")
        
        if platform.system() == "Darwin":  # macOS
            subprocess.run(["open", "-a", app_name], check=False)
            return True
        elif platform.system() == "Windows":
            try:
                os.startfile(app_name)
                return True
            except OSError:
                subprocess.run(["cmd", "/c", "start", "", app_name], check=False, shell=True)
                return True
        else:  # Linux
            subprocess.run(["xdg-open", app_name], check=False)
            return True

    def _close_app(self, app_name: str) -> bool:
        """Closes an application by name (cross-platform)."""
        logger.info(f"Closing app: {app_name}")
        
        try:
            if platform.system() == "Windows":
                subprocess.run(["taskkill", "/IM", f"{app_name}.exe", "/F"], 
                             check=False, capture_output=True)
            elif platform.system() == "Darwin":
                subprocess.run(["osascript", "-e", f'quit app "{app_name}"'], 
                             check=False, capture_output=True)
            else:  # Linux
                subprocess.run(["pkill", "-f", app_name], 
                             check=False, capture_output=True)
            return True
        except Exception as e:
            logger.error(f"Failed to close app {app_name}: {e}")
            return False

    def _open_url(self, url: str) -> bool:
        """Opens a URL in the default browser."""
        logger.info(f"Opening URL: {url}")
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return True
