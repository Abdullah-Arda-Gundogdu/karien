import time
import json
import asyncio
from openai import OpenAI
from assistant.core.config import config
from assistant.core.logging_config import logger

class Brain:

    # Provider → OpenAI-compatible base URL mapping
    PROVIDER_CONFIGS = {
        'OpenAI': {'base_url': None},  # default
        'Groq': {'base_url': 'https://api.groq.com/openai/v1'},
        'Ollama (Local)': {'base_url': 'http://localhost:11434/v1'},
        'Anthropic': {'base_url': None},  # needs separate handling in future
    }

    def __init__(self):
        self.client = None
        self._provider = 'OpenAI'

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

        # Initialize History with the current date to help with calendar tasks
        current_date_context = f"\nCurrent Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.system_prompt += current_date_context

        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]

    def reconfigure(self, provider: str, model: str = None, api_key: str = None, base_url: str = None):
        """
        Switch the LLM provider/model at runtime.
        Works for OpenAI-compatible APIs (OpenAI, Groq, Ollama).
        """
        try:
            provider_cfg = self.PROVIDER_CONFIGS.get(provider, {})
            effective_base_url = base_url or provider_cfg.get('base_url')

            # Determine API key
            if api_key:
                effective_key = api_key
            elif provider == 'Groq':
                effective_key = getattr(config, 'GROQ_API_KEY', None) or 'not-needed'
            elif provider == 'Ollama (Local)':
                effective_key = 'ollama'  # Ollama doesn't need a real key
            else:
                effective_key = config.OPENAI_API_KEY

            if not effective_key:
                logger.error(f"No API key available for provider {provider}")
                return False

            # Create new client
            client_kwargs = {'api_key': effective_key}
            if effective_base_url:
                client_kwargs['base_url'] = effective_base_url

            self.client = OpenAI(**client_kwargs)
            self._provider = provider

            # Update model in config
            if model:
                config.LLM_MODEL = model

            logger.info(f"Brain reconfigured: provider={provider}, model={model or config.LLM_MODEL}")
            return True

        except Exception as e:
            logger.error(f"Brain reconfigure failed: {e}")
            return False

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
    
    def _get_all_tools(self) -> list[dict]:
        """
        Get all available tools: MCP tools + internal Karien-only tools.
        """
        # Karien-specific tools that need special handling in Brain/Orchestrator
        karien_tools = [
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
        ]

        # Get all tools from MCP manager (includes MCP servers + internal tools like Google)
        try:
            from assistant.mcp.manager import mcp_manager
            mcp_tools = mcp_manager.get_all_tools()
            logger.debug(f"Got {len(mcp_tools)} tools from MCP manager")
        except Exception as e:
            logger.warning(f"Could not get MCP tools: {e}")
            mcp_tools = []
        
        # MCP tools first, then Karien-specific tools
        return mcp_tools + karien_tools

    def chat_stream(self, user_text: str):
        """
        Sends user text to LLM and yields chunks of response.
        Handles Tool Calls (both MCP and Internal).
        """
        if not self.client:
            yield ("CONTENT", "[NEUTRAL] I have no brain (API Key missing). I can't think!")
            return

        self.history.append({"role": "user", "content": user_text})
        
        # Build tools list
        tools = self._get_all_tools()

        # Inner loop to handle tool outputs (Assistant -> Tool -> Assistant -> User)
        # We allow up to 3 turns of tool usage per user message to prevent infinite loops
        MAX_TOOL_TURNS = 3
        
        for turn in range(MAX_TOOL_TURNS + 1):
            
            full_response = ""
            tool_calls = [] # Accumulate tool calls for this turn
            
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
                        break 
                    except Exception as e:
                        logger.warning(f"LLM Connection failed (Attempt {attempt+1}/{config.LLM_RETRY_COUNT}): {e}")
                        if attempt == config.LLM_RETRY_COUNT - 1:
                            raise e
                        time.sleep(config.LLM_RETRY_DELAY)

                # Stream Processing
                for chunk in stream:
                    # 1. Handle Content
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield ("CONTENT", content)
                    
                    # 2. Handle Tool Calls
                    if chunk.choices[0].delta.tool_calls:
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            if len(tool_calls) <= tool_call.index:
                                tool_calls.append({"id": "", "name": "", "arguments": ""})
                            
                            if tool_call.id:
                                tool_calls[tool_call.index]["id"] = tool_call.id
                            
                            if tool_call.function.name:
                                tool_calls[tool_call.index]["name"] += tool_call.function.name
                            
                            if tool_call.function.arguments:
                                tool_calls[tool_call.index]["arguments"] += tool_call.function.arguments

                # End of stream for this turn
                
                # If no tool calls, we are done
                if not tool_calls:
                    # Save the assistant's final text reply to history
                    self.history.append({"role": "assistant", "content": full_response})
                    break 

                # If tool calls existed:
                # 1. Add the Assistant's "Call" message to history
                # Ensure we have IDs for all calls (some streamed chunks might miss it if logic above is imperfect, but usually fine)
                # We reconstruct the tool_calls object for history
                formatted_tool_calls = []
                for tc in tool_calls:
                    formatted_tool_calls.append({
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc["arguments"]
                        }
                    })
                
                self.history.append({
                    "role": "assistant",
                    "content": full_response or None, # Content can be null if only calling tools
                    "tool_calls": formatted_tool_calls
                })

                # 2. Execute Tools and Collect Outputs
                for tc in tool_calls:
                    tool_name = tc["name"]
                    try:
                        tool_args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                        logger.error(f"Failed to parse arguments for {tool_name}")

                    logger.info(f"Executing Tool: {tool_name} with args {tool_args}")
                    
                    # Tell frontend we are running a tool
                    yield ("TOOL", (tool_name, json.dumps(tool_args)))
                    
                    tool_output = "Tool execution failed."
                    
                    # --- DISPATCH LOGIC ---
                    
                    # A. Karien-specific tools (need Brain/Orchestrator context)
                    if tool_name == "stop_listening":
                        tool_output = "Stopping assistant."
                        
                    elif tool_name == "analyze_screen":
                        tool_output = "Screen analysis triggered."

                    # B. All other tools (MCP + internal like Google) → MCPManager
                    else:
                        try:
                            from assistant.mcp.manager import mcp_manager
                            if mcp_manager.has_tool(tool_name):
                                # Execute via manager (handles MCP tools + internal fallbacks)
                                handler = mcp_manager._internal_tools.get(tool_name)
                                if handler:
                                    # Sync internal tool (like Google)
                                    tool_output = handler(**tool_args)
                                else:
                                    # MCP tool - async, needs special handling
                                    tool_output = "MCP Execution Pending (Async Architecture Required)"
                            else:
                                tool_output = f"Unknown tool: {tool_name}"
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_output = f"Tool execution failed: {e}"

                    # Yield result (optional, if you want UI to see it)
                    # yield ("TOOL_RESULT", tool_output)
                    
                    # 3. Add Tool Output to History
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tool_name,
                        "content": str(tool_output)
                    })
                    
                # Loop continues to next turn to let LLM process the tool outputs
                
            except Exception as e:
                logger.error(f"LLM Stream Error: {e}")
                yield ("CONTENT", "[SAD] I can't connect to my brain right now.")
                break

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
