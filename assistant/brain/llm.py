"""
Brain Module — Central LLM Orchestration Layer

Implements Karien's three-tier cognitive architecture:
  Tier 1 (Router)      → Intent classification (fast, small model)
  Tier 2 (Worker)      → Task execution (capable model)
  Tier 3 (Synthesizer) → Personality formatting (lightweight model)

This modular design distributes the cognitive load across specialized
models, drastically reducing hallucinations in tool-calling scenarios
and stabilizing the overall response quality.

Also supports "classic" single-model mode for backward compatibility.

Inspired by the Harmony framework (Kawahara et al.) for modular,
human-aware assistant architectures.
"""

import time
import json
import re
from assistant.core.config import config
from assistant.core.logging_config import logger
from assistant.brain.providers.factory import create_provider, create_tier_providers
from assistant.brain.router import Router, Intent
from assistant.brain.worker import Worker
from assistant.brain.synthesizer import Synthesizer


class Brain:
    """
    Central cognitive coordinator for Karien.
    
    In three-tier mode:
      User → Router (intent) → Worker (execution) → Synthesizer (personality) → TTS
    
    In classic mode:
      User → Single LLM (everything) → TTS
    
    The mode is controlled by config.BRAIN_MODE ("three_tier" or "classic").
    """
    
    def __init__(self):
        self.mode = config.BRAIN_MODE  # "three_tier" or "classic"
        
        # Shared state
        self.history = []
        self._classic_client = None
        
        # Load System Prompt
        self.system_prompt = self._load_system_prompt()
        
        # Initialize History with date context
        current_date_context = f"\nCurrent Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        self.system_prompt += current_date_context
        
        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        # Initialize based on mode
        if self.mode == "three_tier":
            self._init_three_tier()
        else:
            self._init_classic()
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file."""
        try:
            prompt_path = config.SYSTEM_PROMPT_PATH
            if prompt_path.exists():
                prompt = prompt_path.read_text(encoding="utf-8")
                logger.info(f"Loaded system prompt from {prompt_path}")
                return prompt
            else:
                logger.warning(f"System prompt not found at {prompt_path}")
                return "You are a helpful assistant."
        except Exception as e:
            logger.error(f"Failed to load system prompt: {e}")
            return "You are a helpful assistant."
    
    # ===================== THREE-TIER INITIALIZATION =====================
    
    def _init_three_tier(self):
        """Initialize the three-tier cognitive architecture."""
        logger.info("Initializing Brain in THREE-TIER mode")
        
        try:
            providers = create_tier_providers()
            
            self.router = Router(providers["router"])
            self.worker = Worker(providers["worker"])
            self.synthesizer = Synthesizer(providers["synthesizer"])
            
            # Also keep a reference to the worker provider for vision
            self._worker_provider = providers["worker"]
            
            logger.info(
                f"Three-tier architecture ready: "
                f"Router({providers['router']}) → "
                f"Worker({providers['worker']}) → "
                f"Synthesizer({providers['synthesizer']})"
            )
        except Exception as e:
            logger.error(f"Three-tier initialization failed: {e}. Falling back to classic mode.")
            self.mode = "classic"
            self._init_classic()
    
    def _init_classic(self):
        """Initialize classic single-model mode (backward compatible)."""
        logger.info("Initializing Brain in CLASSIC mode")
        
        self.router = None
        self.worker = None
        self.synthesizer = None
        
        if config.OPENAI_API_KEY:
            from openai import OpenAI
            self._classic_client = OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("Classic Brain initialized with OpenAI.")
        else:
            logger.warning("No API key found. Brain will be in dummy mode.")
    
    # ===================== TOOL DISCOVERY =====================
    
    def _get_all_tools(self) -> list[dict]:
        """Get all available tools: MCP tools + internal Karien-only tools."""
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
                    "description": "Takes a screenshot and analyzes what is on the user's screen.",
                    "parameters": {"type": "object", "properties": {}},
                }
            },
        ]

        try:
            from assistant.mcp.manager import mcp_manager
            mcp_tools = mcp_manager.get_all_tools()
            logger.debug(f"Got {len(mcp_tools)} tools from MCP manager")
        except Exception as e:
            logger.warning(f"Could not get MCP tools: {e}")
            mcp_tools = []
        
        return mcp_tools + karien_tools
    
    def _get_tool_names(self) -> list[str]:
        """Get flat list of tool names for the Router."""
        tools = self._get_all_tools()
        return [t["function"]["name"] for t in tools if "function" in t]
    
    # ===================== THREE-TIER CHAT STREAM =====================
    
    def chat_stream(self, user_text: str):
        """
        Main entry point for processing user messages.
        
        Routes to three-tier or classic pipeline based on config.
        
        Yields: (chunk_type, chunk_data) tuples
            - ("CONTENT", text_chunk)
            - ("TOOL", (tool_name, args_json))
        """
        if self.mode == "three_tier" and self.router:
            yield from self._chat_stream_three_tier(user_text)
        else:
            yield from self._chat_stream_classic(user_text)
    
    def _chat_stream_three_tier(self, user_text: str):
        """
        Three-tier pipeline: Router → Worker → Synthesizer.
        
        Flow:
        1. Router classifies intent (~100ms local, ~300ms cloud)
        2. Worker executes the task based on intent
        3. Synthesizer adds personality (skipped for tool-only responses)
        """
        self.history.append({"role": "user", "content": user_text})
        
        # ── Tier 1: Route ──
        logger.info("── Tier 1: Router ──")
        tool_names = self._get_tool_names()
        router_result = self.router.classify(user_text, tool_names)
        
        # ── Tier 2: Work ──
        logger.info(f"── Tier 2: Worker (intent={router_result.intent.value}) ──")
        tools = self._get_all_tools()
        
        # For tool calls and non-streaming intents
        if router_result.intent in (Intent.TOOL_CALL, Intent.SYSTEM, Intent.VISION):
            worker_result = self.worker.execute(
                user_text, router_result, self.history, tools
            )
            
            # Handle tool calls
            if worker_result.tool_calls:
                # Format for history
                formatted_tool_calls = []
                for tc in worker_result.tool_calls:
                    tc_id = tc.get("id", f"call_{hash(tc['name'])}")
                    formatted_tool_calls.append({
                        "id": tc_id,
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": tc.get("arguments", "{}"),
                        }
                    })
                
                self.history.append({
                    "role": "assistant",
                    "content": worker_result.content or None,
                    "tool_calls": formatted_tool_calls,
                })
                
                # Yield tool calls
                for tc in worker_result.tool_calls:
                    args = tc.get("arguments", "{}")
                    yield ("TOOL", (tc["name"], args))
                
                # Execute tools and add results to history
                for tc in worker_result.tool_calls:
                    tool_name = tc["name"]
                    try:
                        tool_args = json.loads(tc.get("arguments", "{}")) if isinstance(tc.get("arguments"), str) else tc.get("arguments", {})
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    tool_output = self._execute_tool_internal(tool_name, tool_args)
                    
                    tc_id = tc.get("id", f"call_{hash(tool_name)}")
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": tool_name,
                        "content": str(tool_output),
                    })
                
                # If there's also content, synthesize and yield it
                if worker_result.content and worker_result.requires_synthesis:
                    logger.info("── Tier 3: Synthesizer (post-tool) ──")
                    synthesized = self.synthesizer.synthesize(worker_result.content, user_text)
                    self.history.append({"role": "assistant", "content": synthesized})
                    yield ("CONTENT", synthesized)
                
                self._trim_history()
                return
            
            # Non-tool result (system command gave text response)
            if worker_result.content and worker_result.requires_synthesis:
                logger.info("── Tier 3: Synthesizer ──")
                synthesized = self.synthesizer.synthesize(worker_result.content, user_text)
                self.history.append({"role": "assistant", "content": synthesized})
                yield ("CONTENT", synthesized)
                self._trim_history()
                return
        
        # For conversation and greeting — stream through Worker then Synthesize
        # Stream worker output first, collect it, then synthesize
        logger.info("── Tier 2: Worker (streaming conversation) ──")
        full_worker_output = ""
        
        for chunk_type, chunk_data in self.worker.execute_stream(
            user_text, router_result, self.history, tools
        ):
            if chunk_type == "CONTENT":
                full_worker_output += chunk_data
        
        # ── Tier 3: Synthesize ──
        if full_worker_output:
            logger.info("── Tier 3: Synthesizer ──")
            synthesized = self.synthesizer.synthesize(full_worker_output, user_text)
            self.history.append({"role": "assistant", "content": synthesized})
            yield ("CONTENT", synthesized)
        
        self._trim_history()
    
    # ===================== CLASSIC CHAT STREAM =====================
    
    def _chat_stream_classic(self, user_text: str):
        """
        Classic single-model pipeline (backward compatible).
        Handles tool calls with the original multi-turn approach.
        """
        if not self._classic_client:
            yield ("CONTENT", "[NEUTRAL] I have no brain (API Key missing). I can't think!")
            return

        self.history.append({"role": "user", "content": user_text})
        tools = self._get_all_tools()

        MAX_TOOL_TURNS = 3
        
        for turn in range(MAX_TOOL_TURNS + 1):
            full_response = ""
            tool_calls = []
            
            try:
                stream = None
                for attempt in range(config.LLM_RETRY_COUNT):
                    try:
                        stream = self._classic_client.chat.completions.create(
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

                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_response += content
                        yield ("CONTENT", content)
                    
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

                if not tool_calls:
                    self.history.append({"role": "assistant", "content": full_response})
                    break 

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
                    "content": full_response or None,
                    "tool_calls": formatted_tool_calls
                })

                for tc in tool_calls:
                    tool_name = tc["name"]
                    try:
                        tool_args = json.loads(tc["arguments"])
                    except json.JSONDecodeError:
                        tool_args = {}
                        logger.error(f"Failed to parse arguments for {tool_name}")

                    logger.info(f"Executing Tool: {tool_name} with args {tool_args}")
                    yield ("TOOL", (tool_name, json.dumps(tool_args)))
                    
                    tool_output = self._execute_tool_internal(tool_name, tool_args)
                    
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "name": tool_name,
                        "content": str(tool_output)
                    })
                    
            except Exception as e:
                logger.error(f"LLM Stream Error: {e}")
                yield ("CONTENT", "[SAD] I can't connect to my brain right now.")
                break
        
        self._trim_history()
    
    # ===================== TOOL EXECUTION =====================
    
    def _execute_tool_internal(self, tool_name: str, tool_args: dict) -> str:
        """
        Internal tool execution for Brain-level tool calls.
        Routes to MCP manager or handles Karien-specific tools.
        """
        if tool_name == "stop_listening":
            return "Stopping assistant."
        
        elif tool_name == "analyze_screen":
            return "Screen analysis triggered."
        
        else:
            try:
                from assistant.mcp.manager import mcp_manager
                if mcp_manager.has_tool(tool_name):
                    handler = mcp_manager._internal_tools.get(tool_name)
                    if handler:
                        return handler(**tool_args)
                    else:
                        return "MCP Execution Pending (Async Architecture Required)"
                else:
                    return f"Unknown tool: {tool_name}"
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return f"Tool execution failed: {e}"
    
    # ===================== VISION =====================
    
    def analyze_image(self, base64_image: str):
        """
        Sends an image to the vision model for analysis.
        Uses Worker tier's provider in three-tier mode, or classic client.
        """
        vision_messages = [
            {
                "role": "system",
                "content": "You are Karien. You are looking at the user's screen. "
                           "Describe what you see or answer the user's question about the image directly. "
                           "Keep it conversational."
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
        ]
        
        try:
            if self.mode == "three_tier" and self._worker_provider:
                # Use worker provider for vision
                response = self._worker_provider.complete(
                    messages=vision_messages,
                    stream=False,
                    max_tokens=300,
                )
                raw_description = response.content
                
                # Synthesize the description with personality
                if self.synthesizer:
                    return self.synthesizer.synthesize(raw_description, "Ekranıma bak")
                return raw_description
            
            elif self._classic_client:
                # Classic mode
                response = self._classic_client.chat.completions.create(
                    model=config.LLM_VISION_MODEL,
                    messages=vision_messages,
                    max_tokens=300,
                )
                return response.choices[0].message.content
            
            else:
                return "I can't see anything (Brain disconnected)."
                
        except Exception as e:
            logger.error(f"Vision Error: {e}")
            return "My eyes are blurry... I couldn't analyze the image."
    
    # ===================== HISTORY MANAGEMENT =====================
    
    def _trim_history(self):
        """Keep conversation history within size limits."""
        if len(self.history) > config.HISTORY_MAX_SIZE:
            self.history = [self.history[0]] + self.history[-config.HISTORY_KEEP_RECENT:]
    
    # ===================== LEGACY INTERFACE =====================
    
    def chat(self, user_text: str) -> str:
        """Legacy synchronous chat (collects full streaming response)."""
        full_response = ""
        for chunk_type, chunk_data in self.chat_stream(user_text):
            if chunk_type == "CONTENT":
                full_response += chunk_data
        return full_response or "[NEUTRAL] No response generated."


brain = Brain()
