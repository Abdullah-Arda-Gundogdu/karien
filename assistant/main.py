import asyncio
import sys
from assistant.core.orchestrator import orchestrator
from assistant.core.logging_config import logger

def main():
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
        # Optional: Try to say goodbye if not in critical state
        # tts.speak("Kapatılıyorum.") 
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Global Critical Error: {e}", exc_info=True)
        print(f"\n[FATAL] Karien crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
