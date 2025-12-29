import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import websockets

URL = "ws://127.0.0.1:8001"
PLUGIN_NAME = "KarienAssistant"
PLUGIN_DEV = "Abdullah Arda Gundogdu"
TOKEN_FILE = Path("../../.secrets/vts_token.json")
MOODS_FILE = Path("../../config/moods.json")


def req(message_type: str, data: Optional[Dict[str, Any]] = None, request_id: str = "req") -> Dict[str, Any]:
    payload = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": request_id,
        "messageType": message_type,
    }
    if data is not None:
        payload["data"] = data
    return payload


async def send(ws, payload: Dict[str, Any]) -> Dict[str, Any]:
    await ws.send(json.dumps(payload))
    return json.loads(await ws.recv())


def load_token() -> str:
    return json.loads(TOKEN_FILE.read_text()).get("token")


def load_moods() -> Dict[str, str]:
    return json.loads(MOODS_FILE.read_text())


async def ensure_auth(ws) -> None:
    token = load_token()
    r = await send(
        ws,
        req(
            "AuthenticationRequest",
            {
                "pluginName": PLUGIN_NAME,
                "pluginDeveloper": PLUGIN_DEV,
                "authenticationToken": token,
            },
            request_id="auth",
        ),
    )
    if r.get("messageType") == "APIError" or not r.get("data", {}).get("authenticated"):
        raise RuntimeError("Auth failed: %s" % r)


async def list_hotkeys(ws) -> List[Dict[str, Any]]:
    r = await send(ws, req("HotkeysInCurrentModelRequest", request_id="hk_list"))
    if r.get("messageType") == "APIError":
        raise RuntimeError("Hotkeys list failed: %s" % r)
    return r.get("data", {}).get("availableHotkeys", [])


async def trigger_hotkey(ws, hotkey_id: str) -> None:
    r = await send(ws, req("HotkeyTriggerRequest", {"hotkeyID": hotkey_id}, request_id="hk_trig"))
    if r.get("messageType") == "APIError":
        raise RuntimeError("Hotkey trigger failed: %s" % r)


async def set_mood(mood_key: str) -> None:
    moods = load_moods()
    if mood_key not in moods:
        raise ValueError("Unknown mood key: %s. Known: %s" % (mood_key, list(moods.keys())))

    target_hotkey_name = moods[mood_key]

    async with websockets.connect(URL, proxy=None, open_timeout=2) as ws:
        await ensure_auth(ws)
        hotkeys = await list_hotkeys(ws)

        match = next((hk for hk in hotkeys if hk.get("name") == target_hotkey_name), None)
        if not match:
            available_names = [hk.get("name") for hk in hotkeys]
            raise RuntimeError(
                "Hotkey not found by name: %s\nAvailable hotkeys: %s"
                % (target_hotkey_name, available_names)
            )

        await trigger_hotkey(ws, match["hotkeyID"])
        print("✅ Mood set:", mood_key, "->", target_hotkey_name)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python vts_mood.py <mood_key>")
        raise SystemExit(2)
    asyncio.run(set_mood(sys.argv[1]))
