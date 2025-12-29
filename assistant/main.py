import asyncio
import sys
from assistant.core.orchestrator import orchestrator
from assistant.core.logging_config import logger

def main():
    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
