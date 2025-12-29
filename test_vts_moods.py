
import asyncio
import logging
import websockets
from assistant.output.vts import vts
from assistant.core.logging_config import logger

# Set logging
logging.getLogger().setLevel(logging.INFO)

async def test_all_moods():
    print("Loading VTS client...")
    
    if not vts.moods:
        print("No moods loaded! Check config/moods.json")
        return

    print(f"Found {len(vts.moods)} moods: {list(vts.moods.keys())}")
    
    try:
        print(f"Connecting to {vts.url}...")
        async with websockets.connect(vts.url, open_timeout=2) as ws:
            print("Connected. Authenticating...")
            if not await vts.authenticate(ws):
                print("Authentication failed.")
                return
            print("Authenticated.")

            for mood, hotkey in vts.moods.items():
                print(f"--- Triggering mood: {mood} ({hotkey}) ---")
                try:
                    await vts.trigger_hotkey(ws, hotkey)
                    print(f"Successfully triggered {mood}")
                except Exception as e:
                    print(f"Failed to trigger {mood}: {e}")
                
                print("Waiting 1s...")
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Connection error: {e}")

    print("Done testing all moods.")

if __name__ == "__main__":
    asyncio.run(test_all_moods())
