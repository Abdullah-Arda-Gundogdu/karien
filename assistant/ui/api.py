"""
Karien API Bridge — pywebview ↔ Frontend

Exposes Python methods to JavaScript via pywebview's js_api.
The frontend calls these methods to get/set dynamic data.
Also handles log interception and orchestrator text-mode integration.
"""

import json
import os
import re
import asyncio
import threading
import logging
from pathlib import Path
from assistant.core.logging_config import logger

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"


class UILogHandler(logging.Handler):
    """Intercepts Python logger output and pushes it to the UI console."""

    def __init__(self, api_instance):
        super().__init__()
        self._api = api_instance
        self.setFormatter(logging.Formatter('%(message)s'))

    def emit(self, record):
        try:
            msg = self.format(record)
            level_map = {
                'DEBUG': 'info',
                'INFO': 'info',
                'WARNING': 'tool',
                'ERROR': 'error',
                'CRITICAL': 'error'
            }
            level = level_map.get(record.levelname, 'info')
            self._api.emit_log(level, msg)
        except Exception:
            pass  # Don't let log handler errors crash the app


class KarienAPI:
    def __init__(self):
        self._window = None
        self._shutdown_event = threading.Event()
        self._loop = None  # asyncio loop for orchestrator
        self._orchestrator_thread = None

    def set_window(self, window):
        self._window = window
        # Attach log handler now that window is ready
        self._attach_log_handler()

    def _attach_log_handler(self):
        """Hook into Python's logging to mirror all logs to UI console."""
        handler = UILogHandler(self)
        handler.setLevel(logging.INFO)
        # Attach to root logger so it catches everything
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

    # ─── SETTINGS FILE HELPERS ───

    def _load_settings(self) -> dict:
        """Load settings.json."""
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Failed to load settings: {e}")
            return {}

    def _save_settings(self, data: dict):
        """Persist settings.json."""
        try:
            SETTINGS_PATH.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    # ═══════════════════════════════════════
    #  STATUS
    # ═══════════════════════════════════════

    def get_status(self):
        """Get overall app status."""
        return {
            "version": "v0.2.0",
            "state": "idle"
        }

    # ═══════════════════════════════════════
    #  LLM CONFIGURATION
    # ═══════════════════════════════════════

    def get_llm_config(self):
        """Return LLM settings (provider, model, temperature, available options)."""
        settings = self._load_settings()
        llm = settings.get("llm", {})
        return {
            "provider": llm.get("provider", "OpenAI"),
            "model": llm.get("model", "gpt-4o"),
            "temperature": llm.get("temperature", 0.7),
            "providers": llm.get("providers", ["OpenAI"]),
            "models": llm.get("models", {"OpenAI": ["gpt-4o"]})
        }

    def set_llm_config(self, data: dict):
        """Update LLM settings."""
        settings = self._load_settings()
        llm = settings.setdefault("llm", {})

        if "provider" in data:
            llm["provider"] = data["provider"]
        if "model" in data:
            llm["model"] = data["model"]
        if "temperature" in data:
            llm["temperature"] = data["temperature"]

        self._save_settings(settings)
        logger.info(f"LLM config updated: {data}")
        return {"success": True}

    # ═══════════════════════════════════════
    #  MCP SERVERS
    # ═══════════════════════════════════════

    def get_mcp_servers(self):
        """Return list of installed MCP servers from the registry."""
        try:
            from assistant.mcp.manager import mcp_manager
            mcp_manager._ensure_loaded()
            installed = mcp_manager.get_installed()
            return [
                {
                    "id": mcp.id,
                    "name": mcp.name,
                    "description": mcp.description,
                    "enabled": mcp.enabled,
                    "category": mcp.category
                }
                for mcp in installed
            ]
        except Exception as e:
            logger.error(f"Failed to get MCP servers: {e}")
            return []

    def get_mcp_catalog(self):
        """Return available (not-yet-installed) MCPs from catalog."""
        try:
            from assistant.mcp.manager import mcp_manager
            mcp_manager._ensure_loaded()
            available = mcp_manager.get_available_for_install()
            installed_ids = {m.id for m in mcp_manager.get_installed()}
            return [
                {
                    "id": mcp.id,
                    "name": mcp.name,
                    "description": mcp.description,
                    "category": mcp.category
                }
                for mcp in available if mcp.id not in installed_ids
            ]
        except Exception as e:
            logger.error(f"Failed to get MCP catalog: {e}")
            return []

    def toggle_mcp(self, mcp_id, enabled):
        """Toggle an MCP server on/off in the registry."""
        try:
            from assistant.mcp.manager import mcp_manager
            mcp_manager._ensure_loaded()
            if enabled:
                mcp_manager.registry.enable(mcp_id)
            else:
                mcp_manager.registry.disable(mcp_id)
            logger.info(f"MCP {mcp_id} toggled to {enabled}")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to toggle MCP {mcp_id}: {e}")
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════
    #  AUDIO CONFIGURATION
    # ═══════════════════════════════════════

    def get_audio_config(self):
        """Return audio settings."""
        settings = self._load_settings()
        audio = settings.get("audio", {})
        return {
            "currentDevice": audio.get("currentDevice", "Default"),
            "devices": audio.get("devices", ["Default"]),
            "currentWakeWord": audio.get("currentWakeWord", "Karien"),
            "wakeWords": audio.get("wakeWords", ["Karien", "Hey Karien"])
        }

    # ═══════════════════════════════════════
    #  VOICE / TTS CONFIGURATION
    # ═══════════════════════════════════════

    def get_voice_config(self):
        """Return voice/TTS settings."""
        settings = self._load_settings()
        voice = settings.get("voice", {})
        return {
            "currentEngine": voice.get("currentEngine", "Google Cloud TTS"),
            "engines": voice.get("engines", ["Google Cloud TTS"]),
            "currentVoice": voice.get("currentVoice", ""),
            "voices": voice.get("voices", []),
            "speed": voice.get("speed", 1.0)
        }

    # ═══════════════════════════════════════
    #  CONSOLE / COMMANDS (text-only mode)
    # ═══════════════════════════════════════

    def send_command(self, text):
        """User types in console → sends to LLM via brain.chat_stream()."""
        logger.info(f'User: "{text}"')

        # Run the LLM interaction on a background thread
        thread = threading.Thread(
            target=self._process_text_command,
            args=(text,),
            daemon=True
        )
        thread.start()
        return {"status": "processing"}

    def _process_text_command(self, text):
        """Process a text command through the LLM (runs on background thread)."""
        try:
            from assistant.brain.llm import brain

            self.update_status("thinking")

            full_response = ""
            mood_detected = False

            for chunk_type, chunk_data in brain.chat_stream(text):
                if chunk_type == "CONTENT":
                    token = chunk_data
                    full_response += token

                    # Detect mood tag at start of response
                    if not mood_detected:
                        mood_match = re.search(r"^\s*\[([a-zA-Z_]+)\]", full_response)
                        if mood_match:
                            mood = mood_match.group(1).lower()
                            self.set_mood(mood)
                            mood_detected = True

                elif chunk_type == "TOOL":
                    func_name, args_str = chunk_data
                    self.emit_log("tool", f"Calling: {func_name}({args_str})")

            # Clean mood tags from displayed response
            clean_response = re.sub(r"\[[a-zA-Z_]+\]", "", full_response).strip()
            if clean_response:
                self.emit_log("llm", clean_response)

            self.update_status("idle")

        except Exception as e:
            logger.error(f"LLM error: {e}")
            self.emit_log("error", f"LLM error: {str(e)}")
            self.update_status("idle")

    def log_message(self, message):
        """Called by JS to verify API works."""
        logger.info(f"[UI] Received from JS: {message}")
        return "Received!"

    # ═══════════════════════════════════════
    #  PYTHON → UI (push events)
    # ═══════════════════════════════════════

    def emit_log(self, level, message):
        """Send a log line to the UI console."""
        if self._window:
            # Escape for safe JS injection
            safe_msg = message.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace("\n", "\\n")
            self._window.evaluate_js(f"addLog('{level}', \"{safe_msg}\")")

    def update_status(self, status):
        """Update the orb status (Idle / Listening / etc.)."""
        if self._window:
            self._window.evaluate_js(f"updateStatus('{status}')")

    def set_mood(self, mood):
        """Update the orb face expression."""
        if self._window:
            self._window.evaluate_js(f"setMood('{mood}')")
