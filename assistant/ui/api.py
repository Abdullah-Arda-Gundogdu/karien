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
                mcp_manager._registry.enable(mcp_id)
            else:
                mcp_manager._registry.disable(mcp_id)
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
    #  SETUP WIZARD
    # ═══════════════════════════════════════

    def is_first_run(self):
        """Check if the wizard should be shown."""
        try:
            if not SETTINGS_PATH.exists():
                return True
            with open(SETTINGS_PATH, 'r') as f:
                settings = json.load(f)
            return not settings.get('wizard_completed', False)
        except Exception:
            return True

    def get_existing_keys(self):
        """Return existing API keys from .env (masked for display)."""
        env_path = BASE_DIR / ".env"
        keys = {}
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip()
                        if value:
                            keys[key] = value
        return keys

    def save_wizard_config(self, data):
        """Save wizard selections to .env and settings.json."""
        try:
            env_path = BASE_DIR / ".env"
            
            # 1. Collect all API keys / config values from wizard state
            env_updates = {}
            for pipeline in ['stt', 'llm', 'tts']:
                pipeline_data = data.get(pipeline, {})
                config = pipeline_data.get('config', {})
                for key, value in config.items():
                    if value and value.strip():
                        env_updates[key] = value.strip()

            # 2. Read existing .env, update keys
            existing_lines = []
            existing_keys = set()
            if env_path.exists():
                with open(env_path, 'r') as f:
                    existing_lines = f.readlines()

            new_lines = []
            for line in existing_lines:
                stripped = line.strip()
                if '=' in stripped and not stripped.startswith('#'):
                    key = stripped.split('=', 1)[0].strip()
                    if key in env_updates:
                        new_lines.append(f"{key}={env_updates[key]}\n")
                        existing_keys.add(key)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # Append new keys that weren't in .env
            for key, value in env_updates.items():
                if key not in existing_keys:
                    new_lines.append(f"\n{key}={value}\n")

            with open(env_path, 'w') as f:
                f.writelines(new_lines)

            # 3. Update settings.json
            settings = {}
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, 'r') as f:
                    settings = json.load(f)

            # Map wizard providers to settings
            provider_map = {
                'stt': {
                    'deepgram': 'Deepgram',
                    'whisper_openai': 'Whisper (OpenAI)',
                    'vosk': 'Vosk (Local)'
                },
                'llm': {
                    'openai': 'OpenAI',
                    'groq': 'Groq',
                    'anthropic': 'Anthropic',
                    'ollama': 'Ollama (Local)'
                },
                'tts': {
                    'openai_tts': 'OpenAI TTS',
                    'elevenlabs': 'ElevenLabs',
                    'google_tts': 'Google Cloud TTS',
                    'system_tts': 'System TTS'
                }
            }

            stt_data = data.get('stt', {})
            llm_data = data.get('llm', {})
            tts_data = data.get('tts', {})

            # STT settings
            if 'stt' not in settings:
                settings['stt'] = {}
            settings['stt']['provider'] = provider_map['stt'].get(stt_data.get('provider', ''), 'Deepgram')
            settings['stt']['providers'] = list(provider_map['stt'].values())

            # LLM settings
            if 'llm' not in settings:
                settings['llm'] = {}
            llm_provider_id = llm_data.get('provider', 'openai')
            settings['llm']['provider'] = provider_map['llm'].get(llm_provider_id, 'OpenAI')
            # Set default model for selected provider
            default_models = {
                'openai': 'gpt-4o',
                'groq': 'llama-3.3-70b-versatile',
                'anthropic': 'claude-sonnet-4-20250514',
                'ollama': 'llama3.2'
            }
            settings['llm']['model'] = default_models.get(llm_provider_id, 'gpt-4o')

            # TTS settings
            if 'tts' not in settings:
                settings['tts'] = {}
            settings['tts']['provider'] = provider_map['tts'].get(tts_data.get('provider', ''), 'OpenAI TTS')
            settings['tts']['providers'] = list(provider_map['tts'].values())

            settings['wizard_completed'] = True

            with open(SETTINGS_PATH, 'w') as f:
                json.dump(settings, f, indent=2)

            logger.info("Wizard config saved successfully")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to save wizard config: {e}")
            return {"success": False, "error": str(e)}

    def launch_main_app(self):
        """Navigate from wizard to main app."""
        if self._window:
            ui_path = BASE_DIR / "ui" / "index.html"
            self._window.load_url(f"file://{ui_path}")
        return {"success": True}

    # ═══════════════════════════════════════
    #  API KEY MANAGEMENT (Settings)
    # ═══════════════════════════════════════

    def get_api_keys(self):
        """Get all API keys from .env, masked for display."""
        env_path = BASE_DIR / ".env"
        keys = {}
        key_names = [
            'OPENAI_API_KEY', 'ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID',
            'ELEVENLABS_MODEL_ID', 'DEEPGRAM_API_KEY', 'GROQ_API_KEY',
            'ANTHROPIC_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS',
            'SPOTIFY_CLIENT_ID', 'SPOTIFY_CLIENT_SECRET'
        ]

        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip()
                        if key in key_names:
                            # Mask the value for display
                            if value and len(value) > 8:
                                masked = value[:4] + '•' * min(len(value) - 8, 20) + value[-4:]
                            elif value:
                                masked = '•' * len(value)
                            else:
                                masked = ''
                            keys[key] = {'masked': masked, 'has_value': bool(value)}

        # Add empty entries for keys not in .env
        for key_name in key_names:
            if key_name not in keys:
                keys[key_name] = {'masked': '', 'has_value': False}

        return keys

    def set_api_key(self, key_name, value):
        """Update a single API key in .env."""
        try:
            env_path = BASE_DIR / ".env"
            lines = []
            found = False

            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()

            new_lines = []
            for line in lines:
                stripped = line.strip()
                if '=' in stripped and not stripped.startswith('#'):
                    k = stripped.split('=', 1)[0].strip()
                    if k == key_name:
                        new_lines.append(f"{key_name}={value}\n")
                        found = True
                        continue
                new_lines.append(line)

            if not found:
                new_lines.append(f"\n{key_name}={value}\n")

            with open(env_path, 'w') as f:
                f.writelines(new_lines)

            logger.info(f"API key {key_name} updated")
            return {"success": True}
        except Exception as e:
            logger.error(f"Failed to update API key {key_name}: {e}")
            return {"success": False, "error": str(e)}

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

