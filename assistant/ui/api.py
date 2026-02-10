import logging
import json
import threading
from assistant.core.logging_config import logger

class KarienAPI:
    def __init__(self):
        self._window = None
        self._shutdown_event = threading.Event()

    def set_window(self, window):
        self._window = window

    # --- Methods exposed to JavaScript ---

    def log_message(self, message):
        """Called by JS to verify API works"""
        logger.info(f"[UI] Received from JS: {message}")
        return "Received!"

    def send_command(self, text):
        """User types in console -> sends to LLM"""
        logger.info(f"User Command: {text}")
        # Here we will call orchestrator._handle_user_input(text)
        return {"status": "processing"}

    def toggle_mcp(self, mcp_name, enabled):
        """Toggle an MCP server on/off"""
        logger.info(f"Toggling MCP {mcp_name}: {enabled}")
        # Calls orchestrator.toggle_tool(mcp_name, enabled)
        return True

    # --- Methods called from Python to UI ---

    def emit_log(self, level, message):
        """Send a log line to the specialized UI console"""
        if self._window:
            self._window.evaluate_js(f"addLog('{level}', '{message}')")

    def update_status(self, status):
        """Update the 'Idle / Listening' text"""
        if self._window:
            self._window.evaluate_js(f"updateStatus('{status}')")
