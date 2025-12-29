import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
# Adjust paths to match your actual secret locations relative to this file's execution context
# Typically main.py is run from karien/assistant or karien root.
# We will assume running from root or assistant/ works if we use absolute or smart relative paths
# For now, let's look for secrets in common places


BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRETS_DIR = BASE_DIR / ".secrets"
CONFIG_DIR = BASE_DIR / "config"

# Explicitly load .env from the project root
load_dotenv(BASE_DIR / ".env")

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


    # VTube Studio
    VTS_URL = "ws://127.0.0.1:8001"
    
    # Load token from JSON file
    _token_path = SECRETS_DIR / "vts_token.json"
    VTS_TOKEN = None
    if _token_path.exists():
        import json
        try:
            _data = json.loads(_token_path.read_text())
            VTS_TOKEN = _data.get("token")
        except Exception as e:
            print(f"Error loading VTS token: {e}")

    MOODS_FILE_PATH = CONFIG_DIR / "moods.json"

    
    # Audio
    MIC_INDEX = int(os.getenv("MIC_INDEX", 0))
    
    @classmethod
    def validate(cls):
        # Optional validation
        pass

config = Config()
