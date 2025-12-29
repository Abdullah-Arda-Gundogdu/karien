import json
import logging
import websockets
from typing import Dict, Any, List, Optional
from assistant.core.config import config
from assistant.core.logging_config import logger

class VTSClient:
    def __init__(self):
        self.url = config.VTS_URL
        self.token = config.VTS_TOKEN
        self.plugin_name = "KarienAssistant"
        self.developer = "Abdullah Arda Gundogdu"
        
        # Load mood mapping
        self.moods = {}
        if config.MOODS_FILE_PATH.exists():
            try:
                self.moods = json.loads(config.MOODS_FILE_PATH.read_text())
                logger.info(f"Loaded {len(self.moods)} moods from config.")
            except Exception as e:
                logger.error(f"Failed to load moods.json: {e}")
        else:
            logger.warning(f"Moods file not found at {config.MOODS_FILE_PATH}")

    def _req(self, message_type: str, data: Optional[Dict[str, Any]] = None, request_id: str = "req") -> Dict[str, Any]:
        payload = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": request_id,
            "messageType": message_type,
        }
        if data is not None:
            payload["data"] = data
        return payload

    async def _send(self, ws, payload: Dict[str, Any]) -> Dict[str, Any]:
        await ws.send(json.dumps(payload))
        response = await ws.recv()
        return json.loads(response)


    async def authenticate(self, ws) -> bool:
        """
        Authenticates with VTS. Handles token requests if needed.
        """
        # 1. Authenticate
        auth_payload = self._req(
            "AuthenticationRequest",
            {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.developer,
                "authenticationToken": self.token,
            },
            request_id="auth",
        )
        auth_resp = await self._send(ws, auth_payload)
        
        if auth_resp.get("messageType") == "APIError" or not auth_resp.get("data", {}).get("authenticated"):
            logger.warning(f"VTS Auth Failed: {auth_resp.get('data', {}).get('message', 'Unknown Error')}")
            logger.info("Requesting new authentication token...")
            
            token_req_payload = self._req(
                "AuthenticationTokenRequest",
                {
                    "pluginName": self.plugin_name,
                    "pluginDeveloper": self.developer,
                },
                request_id="token_req"
            )
            token_resp = await self._send(ws, token_req_payload)
            
            if token_resp.get("messageType") == "AuthenticationTokenResponse":
                new_token = token_resp.get("data", {}).get("authenticationToken")
                if new_token:
                    logger.info("Successfully received new authentication token.")
                    self.token = new_token
                    
                    # Save to file
                    from assistant.core.config import SECRETS_DIR
                    token_path = SECRETS_DIR / "vts_token.json"
                    try:
                        token_path.write_text(json.dumps({"token": new_token}))
                        logger.info(f"Saved new token to {token_path}")
                    except Exception as save_err:
                        logger.error(f"Failed to save new token: {save_err}")
                    
                    # Retry Authentication
                    auth_payload["data"]["authenticationToken"] = self.token
                    auth_resp = await self._send(ws, auth_payload)
                    
                    if not auth_resp.get("data", {}).get("authenticated"):
                        logger.error("VTS Re-Auth Failed even with new token.")
                        return False
                else:
                    logger.error("Token response did not contain a token.")
                    return False
            else:
                logger.error(f"Failed to request new token: {token_resp}")
                return False
        
        return True


    async def trigger_hotkey(self, ws, hotkey_name: str):
        """
        Triggers a hotkey by name using the provided websocket connection.
        """
        # 2. Get Hotkeys
        hk_resp = await self._send(ws, self._req("HotkeysInCurrentModelRequest", request_id="hk_list"))
        hotkeys = hk_resp.get("data", {}).get("availableHotkeys", [])
        
        # 3. Find Hotkey ID
        match = next((hk for hk in hotkeys if hk.get("name") == hotkey_name), None)
        if not match:
            logger.error(f"Hotkey '{hotkey_name}' not found in current model.")
            return

        # 4. Trigger
        trig_resp = await self._send(ws, self._req("HotkeyTriggerRequest", {"hotkeyID": match["hotkeyID"]}, request_id="hk_trig"))
        if trig_resp.get("messageType") == "APIError":
            logger.error(f"VTS Trigger Failed: {trig_resp}")
        else:
            logger.debug("VTS Hotkey triggered successfully.")

    async def trigger_mood(self, mood_key: str):
        """
        Connects to VTS, authenticates, and triggers the hotkey associated with the mood.
        This is a one-off connection for MVP simplicity.
        """
        if mood_key not in self.moods:
            logger.warning(f"Mood '{mood_key}' not defined in moods.json.")
            return

        hotkey_name = self.moods[mood_key]
        logger.info(f"Triggering mood: {mood_key} -> {hotkey_name}")

        try:
            async with websockets.connect(self.url, open_timeout=2) as ws:
                if not await self.authenticate(ws):
                    return
                
                await self.trigger_hotkey(ws, hotkey_name)

        except Exception as e:
            logger.error(f"VTS Connection Error: {e}")



vts = VTSClient()
