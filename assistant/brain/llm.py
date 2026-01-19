import time
from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

class Brain:
    def __init__(self):
        self.client = None
        if config.OPENAI_API_KEY:
            self.client = OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("Brain initialized with OpenAI.")
        else:
            logger.warning("OPENAI_API_KEY not found. Brain will be lobotomized (dummy mode).")

        # Load System Prompt
        try:
            prompt_path = config.SYSTEM_PROMPT_PATH
            if prompt_path.exists():
                self.system_prompt = prompt_path.read_text(encoding="utf-8")
                logger.info(f"Loaded system prompt from {prompt_path}")
            else:
                logger.warning(f"System prompt file not found at {prompt_path}. Using minimal fallback.")
                self.system_prompt = "You are a helpful assistant."
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            self.system_prompt = "You are a helpful assistant."

        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]

    def chat(self, user_text: str) -> str:
        """
        Sends user text to LLM and returns response.
        """
        if not self.client:
            return "[NEUTRAL] I have no brain (API Key missing). I can't think!"

        self.history.append({"role": "user", "content": user_text})
        
        try:
            response = self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=self.history,
            )
            
            reply = response.choices[0].message.content
            self.history.append({"role": "assistant", "content": reply})
            
            # Keep history manageable
            if len(self.history) > config.HISTORY_MAX_SIZE:
                self.history = [self.history[0]] + self.history[-config.HISTORY_KEEP_RECENT:]
                
            return reply
            
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "[SAD] Something went wrong in my head..."

    def chat_stream(self, user_text: str):
        """
        Sends user text to LLM and yields chunks of response.
        Yields:
            ("CONTENT", text_chunk)
            ("TOOL", (function_name, arguments_chunk))
            ("TOOL_END", None)
        """
        if not self.client:
            yield ("CONTENT", "[NEUTRAL] I have no brain (API Key missing). I can't think!")
            return

        self.history.append({"role": "user", "content": user_text})
        
        full_response = ""
        tool_calls = [] # Accumulate tool calls
        
        # Tools Definition
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "open_app",
                    "description": "Opens a desktop application.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "The name of the application to open (e.g. Spotify, Chrome)."},
                        },
                        "required": ["app_name"],
                    },
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "close_app",
                    "description": "Closes a desktop application.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {"type": "string", "description": "The name of the application to close."},
                        },
                        "required": ["app_name"],
                    },
                }
            },
             {
                "type": "function",
                "function": {
                    "name": "stop_listening",
                    "description": "Stops the assistant and says goodbye. Use ONLY when user explicitly says goodbye.",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_screen",
                    "description": "Takes a screenshot and analyzes what is on the user's screen. Use this when user asks 'Look at this', 'What is on my screen?', 'Read this error'.",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "Takes a screenshot and saves it to the desktop. Use when user wants to save what's on screen.",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_volume",
                    "description": "Sets the system volume level.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "volume": {"type": "integer", "description": "Volume level from 0 to 100."},
                        },
                        "required": ["volume"],
                    },
                }
            },
        ]

        try:
            # Simple Retry Logic
            stream = None
            
            for attempt in range(config.LLM_RETRY_COUNT):
                try:
                    stream = self.client.chat.completions.create(
                        model=config.LLM_MODEL,
                        messages=self.history,
                        tools=tools,
                        tool_choice="auto",
                        stream=True
                    )
                    break # Success
                except Exception as e:
                    logger.warning(f"LLM Connection failed (Attempt {attempt+1}/{config.LLM_RETRY_COUNT}): {e}")
                    if attempt == config.LLM_RETRY_COUNT - 1:
                        raise e
                    time.sleep(config.LLM_RETRY_DELAY) # Wait before retry

            for chunk in stream:
                # 1. Handle Content
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    logger.debug(f"Chunk received: {content!r}")
                    full_response += content
                    yield ("CONTENT", content)
                
                # 2. Handle Tool Calls
                if chunk.choices[0].delta.tool_calls:
                    for tool_call in chunk.choices[0].delta.tool_calls:
                        # If index is new, expand list
                        if len(tool_calls) <= tool_call.index:
                            tool_calls.append({"name": "", "arguments": ""})
                        
                        if tool_call.function.name:
                            tool_calls[tool_call.index]["name"] += tool_call.function.name
                        
                        if tool_call.function.arguments:
                             tool_calls[tool_call.index]["arguments"] += tool_call.function.arguments

            # Yield accumulated tools at the end
            for tool in tool_calls:
                yield ("TOOL", (tool["name"], tool["arguments"]))

            self.history.append({"role": "assistant", "content": full_response})
            
            # Keep history manageable
            if len(self.history) > 20:
                self.history = [self.history[0]] + self.history[-10:]
                
        except Exception as e:
            logger.error(f"LLM Stream Error: {e}")
            yield ("CONTENT", "[SAD] I can't connect to my brain right now. Please check your internet connection.")

    def analyze_image(self, base64_image: str):
        """
        Sends an image to GPT-4o for analysis.
        Returns the description text.
        """
        if not self.client:
            return "I can't see anything (Brain disconnected)."

        try:
            # We don't stream this for simplicity, just get the description
            logger.info("Sending image to Brain...")
            response = self.client.chat.completions.create(
                model=config.LLM_VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are Karien. You are looking at the user's screen. Describe what you see or answer the user's question about the image directly. Keep it conversational."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What is on my screen? If there's an error, explain it."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=300,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Vision Error: {e}")
            return "My eyes are blurry... I couldn't analyze the image."

brain = Brain()
