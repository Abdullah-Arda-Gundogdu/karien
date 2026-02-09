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
ASSETS_DIR = BASE_DIR / "assets"

# Explicitly load .env from the project root
load_dotenv(BASE_DIR / ".env")

class Config:
    ASSETS_DIR = BASE_DIR / "assets"
    
    # OpenAI Settings
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    
    # ElevenLabs Settings
    ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") 
    ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID")
    
    # Deepgram Settings
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")


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
    SYSTEM_PROMPT_PATH = ASSETS_DIR / "system_prompt.txt"

    # LLM Settings
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "gpt-4o")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    
    # Conversation History Limits
    HISTORY_MAX_SIZE = int(os.getenv("HISTORY_MAX_SIZE", "20"))
    HISTORY_KEEP_RECENT = int(os.getenv("HISTORY_KEEP_RECENT", "10"))
    
    # Retry Settings
    LLM_RETRY_COUNT = int(os.getenv("LLM_RETRY_COUNT", "3"))
    LLM_RETRY_DELAY = float(os.getenv("LLM_RETRY_DELAY", "1.0"))
    
    # Audio
    # Audio
    _mic_env = os.getenv("MIC_INDEX")
    MIC_INDEX = int(_mic_env) if _mic_env is not None and _mic_env.strip() else None
    
    # VAD Settings
    VAD_THRESHOLD = float(os.getenv("VAD_THRESHOLD", "0.5"))
    VAD_SAMPLE_RATE = int(os.getenv("VAD_SAMPLE_RATE", "16000"))
    AUDIO_BUFFER_SECONDS = float(os.getenv("AUDIO_BUFFER_SECONDS", "2.0"))
    
    # MCP Settings
    MCP_REGISTRY_PATH = CONFIG_DIR / "mcp_registry.json"
    MCP_CATALOG_PATH = BASE_DIR / "assistant" / "mcp" / "catalog.json"
    MCP_STARTUP_TIMEOUT = float(os.getenv("MCP_STARTUP_TIMEOUT", "30.0"))
    MCP_TOOL_TIMEOUT = float(os.getenv("MCP_TOOL_TIMEOUT", "60.0"))
    
    @classmethod
    def validate(cls):
        """
        Validates critical configuration.
        """
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        if missing:
            print("WARNING: The following critical environment variables are missing:")
            for key in missing:
                print(f"  - {key}")
            print("Assistant may not function correctly (Brainless Mode).")
            
            # Raise error if strict mode is desired
            raise ValueError(f"Missing config: {missing}")

config = Config()
config.validate()
