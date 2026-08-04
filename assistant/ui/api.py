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
AVATAR_MANIFEST_PATH = BASE_DIR / "ui" / "avatars" / "manifest.json"


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
        self._overlay_window = None  # small always-on-top avatar window
        self._voice_service = None   # assistant.ui.voice_service.VoiceService
        self._shutdown_event = threading.Event()

    def set_window(self, window):
        self._window = window
        # Attach log handler now that window is ready
        self._attach_log_handler()

    def set_overlay_window(self, window):
        """Register the overlay avatar window (called from desktop_app)."""
        self._overlay_window = window

    def set_voice_service(self, service):
        """Register the VoiceService so the UI can toggle voice mode."""
        self._voice_service = service

    def _attach_log_handler(self):
        """Hook into Python's logging to mirror all logs to UI console."""
        root_logger = logging.getLogger()
        # 'loaded' fires on every page navigation (wizard → main app);
        # attaching more than once duplicates every UI console line.
        for existing in root_logger.handlers:
            if isinstance(existing, UILogHandler):
                existing._api = self
                return
        handler = UILogHandler(self)
        handler.setLevel(logging.INFO)
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
    # The engine reads LLM settings from .env via assistant.core.config at
    # startup — settings.json plays no role here. get_llm_config reports the
    # values the RUNNING engine actually uses; set_llm_config writes the new
    # values to .env, which take effect after a restart (the UI shows an
    # honest "yeniden başlatınca geçerli" chip for this).

    _LLM_PROVIDERS = ["openai", "ollama"]

    def get_llm_config(self):
        """Return the live LLM settings the engine was started with."""
        from assistant.core.config import config
        return {
            "provider": config.LLM_PROVIDER,
            "model": config.LLM_MODEL,
            "temperature": config.LLM_TEMPERATURE,
            "providers": list(self._LLM_PROVIDERS),
        }

    def set_llm_config(self, data: dict):
        """Write LLM settings to .env (effective after restart)."""
        try:
            if "provider" in data:
                provider = str(data["provider"]).lower().strip()
                if provider not in self._LLM_PROVIDERS:
                    return {"success": False,
                            "error": f"Bilinmeyen sağlayıcı: {provider}"}
                self._write_env_key("LLM_PROVIDER", provider)
            if "model" in data:
                model = str(data["model"]).strip()
                if model:
                    self._write_env_key("LLM_MODEL", model)
            if "temperature" in data:
                temperature = max(0.0, min(2.0, float(data["temperature"])))
                self._write_env_key("LLM_TEMPERATURE", f"{temperature:.2f}")

            logger.info(f"LLM ayarları .env'e yazıldı: {data}")
            return {"success": True, "restart_required": True}
        except Exception as e:
            logger.error(f"LLM ayarları yazılamadı: {e}")
            return {"success": False, "error": str(e)}

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
    #  AUDIO INPUT (microphone devices)
    # ═══════════════════════════════════════
    # PyAudio is lazy-imported: it must stay out of module import time
    # (CI runs in a slim environment without portaudio).

    def get_audio_devices(self):
        """Enumerate microphone input devices (graceful [] on failure)."""
        devices = []
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            try:
                for i in range(pa.get_device_count()):
                    info = pa.get_device_info_by_index(i)
                    if int(info.get("maxInputChannels", 0)) > 0:
                        devices.append({
                            "index": i,
                            "name": str(info.get("name", f"Cihaz {i}"))
                        })
            finally:
                pa.terminate()
        except Exception as e:
            logger.error(f"Ses giriş cihazları listelenemedi: {e}")

        current = None
        try:
            from assistant.core.config import config
            current = config.MIC_INDEX
        except Exception:
            pass
        return {"devices": devices, "current": current}

    def set_audio_device(self, index):
        """Persist the chosen mic as MIC_INDEX in .env (effective after restart)."""
        try:
            self._write_env_key("MIC_INDEX", str(int(index)))
            logger.info(f"Mikrofon cihazı .env'e yazıldı: MIC_INDEX={int(index)}")
            return {"success": True, "restart_required": True}
        except Exception as e:
            logger.error(f"Mikrofon cihazı yazılamadı: {e}")
            return {"success": False, "error": str(e)}

    # ═══════════════════════════════════════
    #  AUDIO OUTPUT (TTS engine — read-only)
    # ═══════════════════════════════════════

    def get_tts_status(self):
        """Report which TTS engine the singleton auto-selected (read-only).

        Lazy import: the tts singleton pulls in pygame/audio at first use,
        which must stay out of module import time for CI.
        """
        try:
            from assistant.output.tts import tts
            available = bool(tts.client)
            return {
                "available": available,
                "provider": tts.provider if available else None
            }
        except Exception as e:
            logger.error(f"TTS durumu okunamadı: {e}")
            return {"available": False, "provider": None}

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
        """Get all API keys from .env, masked for display.

        Only keys the engine actually reads are listed (GROQ/ANTHROPIC/
        GOOGLE rows were dead — no runtime consumer).
        """
        env_path = BASE_DIR / ".env"
        keys = {}
        key_names = [
            'OPENAI_API_KEY', 'DEEPGRAM_API_KEY', 'ELEVENLABS_API_KEY',
            'ELEVENLABS_VOICE_ID', 'ELEVENLABS_MODEL_ID',
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

    def _write_env_key(self, key_name, value):
        """Set a single KEY=value in .env, preserving comments and unknown
        lines exactly as they are (comment-preserving merge).

        Shared by set_api_key, set_llm_config and set_audio_device.
        Raises on I/O failure — callers wrap with their own error handling.
        """
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

    def set_api_key(self, key_name, value):
        """Update a single API key in .env."""
        try:
            self._write_env_key(key_name, value)
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

    # ═══════════════════════════════════════
    #  OVERLAY AVATAR BRIDGE
    # ═══════════════════════════════════════
    # Thread-safe: callable from the voice service thread. Every JS call is
    # guarded so a missing/closed overlay window can never crash voice flow.
    # JS globals expected in ui/overlay.html (implemented by the skin layer):
    #   overlaySlideIn(), overlaySlideOut(), overlaySetState(s), overlaySetMood(m)

    _SAFE_TOKEN = re.compile(r"^[a-z_]+$")

    def _overlay_js(self, code):
        """Run JS on the overlay window; never raises."""
        try:
            if self._overlay_window:
                self._overlay_window.evaluate_js(code)
        except Exception as e:
            logger.debug(f"Overlay JS failed (ignored): {e}")

    def overlay_show(self):
        """Show the overlay window and trigger the slide-in animation."""
        try:
            # A rapid sleep→wake could leave a stale hide-timer that would
            # hide the freshly shown window — cancel it first.
            pending = getattr(self, "_overlay_hide_timer", None)
            if pending:
                pending.cancel()
                self._overlay_hide_timer = None
            if self._overlay_window:
                self._overlay_window.show()
                # Give the window a moment to appear before animating
                threading.Timer(0.05, lambda: self._overlay_js("overlaySlideIn()")).start()
        except Exception as e:
            logger.debug(f"overlay_show failed (ignored): {e}")

    def overlay_hide(self):
        """Slide the overlay out, then hide the window after the transition."""
        try:
            self._overlay_js("overlaySlideOut()")

            def _hide():
                try:
                    if self._overlay_window:
                        self._overlay_window.hide()
                except Exception:
                    pass

            timer = threading.Timer(0.8, _hide)
            self._overlay_hide_timer = timer
            timer.start()
        except Exception as e:
            logger.debug(f"overlay_hide failed (ignored): {e}")

    def overlay_state(self, state):
        """Set the overlay state: hidden / listen / think / speak."""
        if isinstance(state, str) and self._SAFE_TOKEN.match(state):
            self._overlay_js(f"overlaySetState('{state}')")

    def overlay_mood(self, mood):
        """Set the overlay mood (one of the 9 [mood] tags)."""
        if isinstance(mood, str) and self._SAFE_TOKEN.match(mood):
            self._overlay_js(f"overlaySetMood('{mood}')")

    # ═══════════════════════════════════════
    #  AVATAR SKIN
    # ═══════════════════════════════════════
    # Skins live in ui/avatars/<id>/skin.css and are listed in
    # ui/avatars/manifest.json. The chosen skin id is stored in
    # settings.json under "avatar".

    _SKIN_ID = re.compile(r"^[a-zA-Z0-9_-]+$")

    def _load_avatar_manifest(self):
        """Load the skin list from ui/avatars/manifest.json."""
        try:
            skins = json.loads(AVATAR_MANIFEST_PATH.read_text(encoding="utf-8"))
            if isinstance(skins, list) and skins:
                return skins
        except Exception as e:
            logger.error(f"Failed to load avatar manifest: {e}")
        return [{"id": "orb", "name": "Orb", "file": "orb/skin.css"}]

    def get_avatar(self):
        """Return the chosen avatar skin id plus all available skins."""
        skins = self._load_avatar_manifest()
        settings = self._load_settings()
        avatar = settings.get("avatar", "orb")
        if avatar not in {s.get("id") for s in skins}:
            avatar = skins[0].get("id", "orb")
        return {"avatar": avatar, "skins": skins}

    def set_avatar(self, avatar_id):
        """Persist the avatar skin and apply it to the overlay immediately."""
        skins = self._load_avatar_manifest()
        valid_ids = {s.get("id") for s in skins}
        if (not isinstance(avatar_id, str)
                or not self._SKIN_ID.match(avatar_id)
                or avatar_id not in valid_ids):
            return {"success": False, "error": f"Unknown avatar skin: {avatar_id}"}

        settings = self._load_settings()
        settings["avatar"] = avatar_id
        self._save_settings(settings)

        # Live-apply on the overlay window (guarded — never crashes)
        self._overlay_js(f"overlaySetSkin('{avatar_id}')")
        logger.info(f"Avatar skin set to: {avatar_id}")
        return {"success": True, "avatar": avatar_id}

    # --- JS-callable demo helpers (no microphone needed) ---

    def simulate_wake(self):
        """Demo: drive the same path as a real wake word (slide-in + listen)."""
        self.overlay_show()
        self.overlay_state("listen")
        return {"success": True}

    def simulate_sleep(self):
        """Demo: drive the same path as a goodbye (slide-out + hide)."""
        self.overlay_hide()
        return {"success": True}

    # ═══════════════════════════════════════
    #  VOICE SERVICE (wake word pipeline)
    # ═══════════════════════════════════════

    def get_voice_status(self):
        """Return whether the voice pipeline is currently enabled."""
        return {"enabled": bool(self._voice_service and self._voice_service.enabled)}

    def toggle_voice(self):
        """Start/stop the voice pipeline from the UI (stop is best-effort)."""
        if not self._voice_service:
            return {"success": False, "enabled": False,
                    "error": "Ses servisi bu oturumda mevcut değil."}
        try:
            if self._voice_service.enabled:
                self._voice_service.stop()
            else:
                self._voice_service.start()
            return {"success": True, "enabled": self._voice_service.enabled}
        except Exception as e:
            logger.error(f"Ses modu değiştirilemedi: {e}")
            return {"success": False, "enabled": self._voice_service.enabled,
                    "error": str(e)}

    # ═══════════════════════════════════════
    #  BOTTOM BAR ACTIONS (Durdur / Ekran Görüntüsü)
    # ═══════════════════════════════════════

    def stop_speaking(self):
        """Immediately stop TTS playback (UI 'Durdur' button).

        Import is lazy: the tts singleton pulls in pygame/audio, which must
        stay out of module import time (CI runs in a slim environment).
        """
        try:
            from assistant.output.tts import tts
            tts.stop_playback()
            return {"success": True}
        except Exception as e:
            logger.error(f"Konuşma durdurulamadı: {e}")
            return {"success": False, "error": str(e)}

    def take_screenshot(self):
        """Take a screenshot to the Desktop (UI 'Ekran Görüntüsü' button).

        Reuses SystemSkill's cross-platform implementation via lazy import
        (pyautogui is imported inside the skill method itself).
        """
        try:
            from assistant.skills.system import SystemSkill
            ok = SystemSkill()._take_screenshot()
            return {"success": bool(ok)}
        except Exception as e:
            logger.error(f"Ekran görüntüsü alınamadı: {e}")
            return {"success": False, "error": str(e)}

