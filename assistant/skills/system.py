import subprocess
import datetime
import os
import platform
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
                return self._take_screenshot()
            elif command == "set_volume":
                if not params:
                    return False
                return self._set_volume(int(params[0]))
        except Exception as e:
            logger.error(f"SystemSkill Error: {e}")
            return False
        return False

    def _take_screenshot(self) -> bool:
        """Cross-platform screenshot using pyautogui."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        path = os.path.expanduser(f"~/Desktop/{filename}")
        logger.info(f"Taking screenshot: {path}")
        
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            logger.info(f"Screenshot saved to: {path}")
            return True
        except ImportError:
            # Fallback to platform-specific commands
            if platform.system() == "Darwin":
                subprocess.run(["screencapture", "-x", path], check=True)
                return True
            elif platform.system() == "Windows":
                logger.error("pyautogui not available for screenshot on Windows.")
                return False
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return False

    def _set_volume(self, volume: int) -> bool:
        """Cross-platform volume control. Volume should be 0-100."""
        volume = max(0, min(100, volume))  # Clamp to valid range
        logger.info(f"Setting volume to: {volume}")
        
        if platform.system() == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {volume}"], check=False)
            return True
        elif platform.system() == "Windows":
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
                
                # pycaw uses 0.0-1.0 range
                volume_interface.SetMasterVolumeLevelScalar(volume / 100.0, None)
                return True
            except ImportError:
                logger.error("pycaw not installed. Run `pip install pycaw` for Windows volume control.")
                return False
            except Exception as e:
                logger.error(f"Windows volume control failed: {e}")
                return False
        else:
            logger.warning(f"Volume control not supported on {platform.system()}.")
            return False
