
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
        print("Connecting to VTube Studio...")
        await vts.connect()
        
        if not vts.connected:
            print("Failed to connect/authenticate.")
            return

        print("Connected and Authenticated.")

        for mood, hotkey in vts.moods.items():
            print(f"--- Triggering mood: {mood} ({hotkey}) ---")
            try:
                # Use high-level trigger_mood which now uses the persistent connection
                await vts.trigger_mood(mood)
                print(f"Successfully triggered {mood}")
            except Exception as e:
                print(f"Failed to trigger {mood}: {e}")
            
            print("Waiting 1s...")
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"Connection error: {e}")
    finally:
        await vts.close()

    print("Done testing all moods.")


if __name__ == "__main__":
    asyncio.run(test_all_moods())
