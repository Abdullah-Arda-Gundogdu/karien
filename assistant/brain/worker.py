"""
Tier 2: Task Worker

The second layer of Karien's three-tier cognitive architecture.
Executes the actual task based on the Router's intent classification.

Design rationale:
- Receives a narrowly-scoped task from the Router, reducing hallucination risk
- Uses the most capable model available (cloud or large local)
- Handles tool calling, conversation, and vision as separate execution paths
- Outputs raw content (no personality formatting — that's Tier 3's job)
"""

import json
import time
from typing import Generator, Optional
from dataclasses import dataclass
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider, StreamChunk
from assistant.brain.router import Intent, RouterResult


def safe_history_tail(messages: list, n: int) -> list:
    """
    Take the last n non-system messages WITHOUT breaking OpenAI's tool
    message pairing rules. A naive [-n:] slice can start the window on a
    role:"tool" message (its assistant/tool_calls parent excluded) or keep
    an assistant tool_calls message whose results fell outside the window —
    both are rejected by the API with a 400.
    """
    non_system = [m for m in messages if m.get("role") != "system"]
    start = max(0, len(non_system) - n)
    # Never start the window on a tool result — pull its parent in
    while start > 0 and non_system[start].get("role") == "tool":
        start -= 1
    tail = non_system[start:]

    # Strip tool_calls whose results are not fully inside the window
    # (e.g. a turn that crashed mid-execution)
    result_ids = {m.get("tool_call_id") for m in tail if m.get("role") == "tool"}
    cleaned = []
    for m in tail:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            ids = {tc.get("id") for tc in m["tool_calls"]}
            if not ids.issubset(result_ids):
                m = {k: v for k, v in m.items() if k != "tool_calls"}
                if not m.get("content"):
                    continue
        cleaned.append(m)

    # Drop tool results whose parent assistant message got stripped
    valid_ids = set()
    final = []
    for m in cleaned:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            valid_ids.update(tc.get("id") for tc in m["tool_calls"])
        if m.get("role") == "tool" and m.get("tool_call_id") not in valid_ids:
            continue
        final.append(m)
    return final


@dataclass
class WorkerResult:
    """Output from the Worker tier."""
    content: str                        # Raw text output
    tool_calls: list = None             # Tool calls to execute
    requires_synthesis: bool = True     # Whether Tier 3 should process this
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


# Worker system prompt — focused on task execution, NOT personality
WORKER_SYSTEM_PROMPT_CONVERSATION = """You are the task execution engine for an AI assistant.
Your job is to provide accurate, helpful answers to the user's question.
Keep responses concise and factual. Do NOT add personality, emotions, or mood tags.
The personality layer will be added by another module.
Respond in the same language as the user (typically Turkish).
"""

WORKER_SYSTEM_PROMPT_TOOL = """You are the tool execution engine for an AI assistant.
The user wants to perform an action on their computer. Your job is to select 
the appropriate tool and provide the correct arguments.
Use the available tools to fulfill the user's request.
If the user's request doesn't match any tool, respond with a brief explanation.
Respond in the same language as the user (typically Turkish).
"""


class Worker:
    """
    Tier 2 — Task Worker.
    
    Executes the classified intent using the most capable model.
    Each intent type has a specialized execution path:
    
    - CONVERSATION: Full chat completion with history
    - TOOL_CALL: Function calling with tool selection
    - VISION: Image analysis (delegated to vision model)
    - SYSTEM: Internal command handling
    - GREETING: Quick greeting response
    """
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        logger.info(f"Worker initialized with {provider}")
    
    def execute(self, user_text: str, router_result: RouterResult,
                history: list[dict], tools: list[dict] = None) -> WorkerResult:
        """
        Execute the task based on Router classification.
        
        Args:
            user_text: Original user message
            router_result: Classification from Router tier
            history: Conversation history
            tools: Available tool definitions
            
        Returns:
            WorkerResult with raw content and/or tool calls
        """
        intent = router_result.intent
        
        if intent == Intent.SYSTEM:
            return self._handle_system(user_text, router_result)
        
        elif intent == Intent.GREETING:
            return self._handle_greeting(user_text, history)
        
        elif intent == Intent.VISION:
            # Vision is handled externally by the orchestrator
            return WorkerResult(
                content="analyze_screen",
                tool_calls=[{"name": "analyze_screen", "arguments": "{}"}],
                requires_synthesis=False,
            )
        
        elif intent == Intent.TOOL_CALL:
            return self._handle_tool_call(user_text, history, tools)
        
        else:  # CONVERSATION
            return self._handle_conversation(user_text, history)
    
    def execute_stream(self, user_text: str, router_result: RouterResult,
                       history: list[dict], tools: list[dict] = None) -> Generator:
        """
        Streaming version of execute for real-time TTS pipelining.
        
        Yields (chunk_type, data) tuples:
        - ("CONTENT", text_chunk)
        - ("TOOL", (tool_name, args_json))
        """
        intent = router_result.intent
        
        if intent in (Intent.SYSTEM, Intent.GREETING, Intent.VISION):
            # Non-streaming intents — execute and yield result
            result = self.execute(user_text, router_result, history, tools)
            if result.content:
                yield ("CONTENT", result.content)
            for tc in result.tool_calls:
                yield ("TOOL", (tc["name"], json.dumps(tc.get("arguments", {})) if isinstance(tc.get("arguments"), dict) else tc.get("arguments", "{}")))
            return
        
        elif intent == Intent.TOOL_CALL:
            # Tool calls need full response to parse tool calls properly
            result = self._handle_tool_call(user_text, history, tools)
            if result.content:
                yield ("CONTENT", result.content)
            for tc in result.tool_calls:
                args = tc.get("arguments", "{}")
                if isinstance(args, dict):
                    args = json.dumps(args)
                yield ("TOOL", (tc["name"], args))
            return
        
        # CONVERSATION — stream for real-time TTS
        messages = self._build_conversation_messages(user_text, history)
        
        stream = self.provider.complete(
            messages=messages,
            stream=True,
        )
        
        for chunk in stream:
            if chunk.chunk_type == "content" and chunk.content:
                yield ("CONTENT", chunk.content)
    
    def _handle_conversation(self, user_text: str, history: list[dict]) -> WorkerResult:
        """Handle general conversation intent."""
        messages = self._build_conversation_messages(user_text, history)
        
        response = self.provider.complete(
            messages=messages,
            stream=False,
        )
        
        return WorkerResult(
            content=response.content,
            requires_synthesis=True,
        )
    
    def _handle_tool_call(self, user_text: str, history: list[dict],
                          tools: list[dict] = None) -> WorkerResult:
        """Handle tool calling intent with function calling."""
        # Use tool-focused system prompt
        messages = [{"role": "system", "content": WORKER_SYSTEM_PROMPT_TOOL}]
        
        # Add recent history for context (last few turns only)
        messages.extend(safe_history_tail(history, 6))
        
        # Add current user message
        messages.append({"role": "user", "content": user_text})
        
        response = self.provider.complete(
            messages=messages,
            tools=tools,
            stream=False,
        )
        
        formatted_tool_calls = []
        for tc in response.tool_calls:
            formatted_tool_calls.append({
                "id": tc.get("id", ""),
                "name": tc.get("name", ""),
                "arguments": tc.get("arguments", "{}"),
            })
        
        return WorkerResult(
            content=response.content,
            tool_calls=formatted_tool_calls,
            requires_synthesis=bool(response.content) and not formatted_tool_calls,
        )
    
    def _handle_system(self, user_text: str, router_result: RouterResult) -> WorkerResult:
        """Handle system commands (stop, sleep, etc.)."""
        text_lower = user_text.lower()
        
        goodbye_keywords = ["bye", "goodbye", "görüşürüz", "hoşçakal", "kapat", "dur", "kapan"]
        if any(kw in text_lower for kw in goodbye_keywords):
            return WorkerResult(
                content="Goodbye triggered",
                tool_calls=[{"name": "stop_listening", "arguments": "{}"}],
                requires_synthesis=False,
            )
        
        return WorkerResult(
            content="System command received but not recognized.",
            requires_synthesis=True,
        )
    
    def _handle_greeting(self, user_text: str, history: list[dict]) -> WorkerResult:
        """Handle greetings — quick response, minimal processing."""
        messages = self._build_conversation_messages(user_text, history)
        
        response = self.provider.complete(
            messages=messages,
            stream=False,
            max_tokens=100,  # Greetings should be short
        )
        
        return WorkerResult(
            content=response.content,
            requires_synthesis=True,
        )
    
    def _build_conversation_messages(self, user_text: str, history: list[dict]) -> list[dict]:
        """Build message list for conversation, using history context."""
        messages = [{"role": "system", "content": WORKER_SYSTEM_PROMPT_CONVERSATION}]
        
        # Add conversation history (exclude old system messages)
        messages.extend(safe_history_tail(history, 10))
        
        # Add current message
        messages.append({"role": "user", "content": user_text})
        
        return messages
