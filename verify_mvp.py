import asyncio
import sys
import logging
from assistant.core.logging_config import logger

# Helper to suppress noisy logs for the menu
logging.getLogger().setLevel(logging.ERROR)

async def test_stt():
    print("\n[STT Test] Speak now...")
    from assistant.input.stt import stt
    text = stt.listen(timeout=5)
    print(f"[Result]: {text}")

def test_tts():
    print("\n[TTS Test] Speaking...")
    from assistant.output.tts import tts
    tts.speak("Verification protocol initiated. Hello, User.")
    print("[Result]: Done.")

async def test_vts():
    print("\n[VTS Test] Triggering 'Happy' mood...")
    from assistant.output.vts import vts
    await vts.trigger_mood("happy")
    print("[Result]: Trigger sent.")

def test_brain():
    prompt = input("\n[Brain Test] Enter text for Karien: ")
    from assistant.brain.llm import brain
    response = brain.chat(prompt)
    print(f"[Result]: {response}")

def test_skill():
    print("\n[Skill Test] Attempting to open Calculator...")
    from assistant.skills.launcher import LauncherSkill
    skill = LauncherSkill()
    skill.execute("open_app", ["Calculator"])
    print("[Result]: Command executed.")

async def menu():
    while True:
        print("\n--- Karien MVP Verification ---")
        print("1. Test STT (Mic)")
        print("2. Test TTS (Speaker)")
        print("3. Test VTS (Mood)")
        print("4. Test Brain (LLM)")
        print("5. Test Skill (Launcher)")
        print("0. Exit")
        
        choice = input("Select option: ")
        
        try:
            if choice == "1":
                await test_stt()
            elif choice == "2":
                test_tts()
            elif choice == "3":
                await test_vts()
            elif choice == "4":
                test_brain()
            elif choice == "5":
                test_skill()
            elif choice == "0":
                break
            else:
                print("Invalid choice.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(menu())
    except KeyboardInterrupt:
        pass
