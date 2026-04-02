"""
Tier 1: Intent Router

The first layer of Karien's three-tier cognitive architecture.
Rapidly classifies user intent to route the request to the appropriate
Worker mode, reducing the cognitive load on downstream models.

Design rationale:
- Uses a small, fast model (local or cloud) to keep latency low
- Outputs structured JSON for reliable downstream parsing
- Reduces hallucinations by narrowing the Worker's task scope
- Inspired by Harmony framework's modular task distribution
"""

import json
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider


class Intent(Enum):
    """Classified user intent types."""
    CONVERSATION = "conversation"     # General chat, questions, advice
    TOOL_CALL = "tool_call"           # System commands, app control, MCP tools
    VISION = "vision"                 # Screen analysis, "look at this"
    SYSTEM = "system"                 # Stop, sleep, wake up, settings
    GREETING = "greeting"             # Hello, goodbye, casual opener


@dataclass
class RouterResult:
    """Output of the intent routing process."""
    intent: Intent
    confidence: float
    suggested_tool: Optional[str] = None
    reasoning: str = ""


# Router system prompt — minimal, focused, fast
ROUTER_SYSTEM_PROMPT = """You are an intent classifier for an AI assistant called Karien.
Your ONLY job is to classify the user's message into one of these intents:

- "conversation": General questions, chat, advice, knowledge, emotional support
- "tool_call": User wants to control the OS, open apps, manage files, send emails, calendar, any system action
- "vision": User wants you to look at their screen ("look at this", "what's on my screen", "read this error")
- "system": User says goodbye, wants to stop, or asks about settings/configuration
- "greeting": User says hello, casual opener, small talk

Respond with ONLY a JSON object, no other text:
{"intent": "<intent>", "confidence": <0.0-1.0>, "suggested_tool": "<tool_name_or_null>", "reasoning": "<brief_reason>"}

Available tools for reference (use these names in suggested_tool):
{tool_list}
"""


class Router:
    """
    Tier 1 — Intent Router.
    
    Quickly classifies user messages to determine the appropriate
    processing path. This distributes cognitive load by ensuring
    the Worker tier receives a narrowly-scoped task rather than
    an open-ended prompt.
    
    Performance target: < 200ms with local model, < 500ms with cloud.
    """
    
    def __init__(self, provider: LLMProvider):
        self.provider = provider
        logger.info(f"Router initialized with {provider}")
    
    def classify(self, user_text: str, available_tools: list[str] = None) -> RouterResult:
        """
        Classify user intent.
        
        Args:
            user_text: The user's message
            available_tools: List of available tool names for context
            
        Returns:
            RouterResult with classified intent and confidence
        """
        tool_list = ", ".join(available_tools) if available_tools else "open_app, analyze_screen, stop_listening"
        
        system_prompt = ROUTER_SYSTEM_PROMPT.format(tool_list=tool_list)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        
        try:
            response = self.provider.complete(
                messages=messages,
                stream=False,
                max_tokens=100,  # Router output should be very short
            )
            
            # Parse the JSON response
            result = self._parse_response(response.content)
            logger.info(f"Router: '{user_text[:50]}...' → {result.intent.value} (confidence: {result.confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Router classification failed: {e}")
            # Default to conversation on failure — safest fallback
            return RouterResult(
                intent=Intent.CONVERSATION,
                confidence=0.5,
                reasoning=f"Router failed: {e}, defaulting to conversation",
            )
    
    def _parse_response(self, content: str) -> RouterResult:
        """Parse the Router's JSON output into a RouterResult."""
        try:
            # Clean potential markdown code blocks
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content
                content = content.rsplit("```", 1)[0] if "```" in content else content
                content = content.strip()
            
            data = json.loads(content)
            
            intent_str = data.get("intent", "conversation").lower()
            try:
                intent = Intent(intent_str)
            except ValueError:
                intent = Intent.CONVERSATION
            
            return RouterResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.7)),
                suggested_tool=data.get("suggested_tool"),
                reasoning=data.get("reasoning", ""),
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Router JSON parse failed: {e}, raw: {content[:200]}")
            
            # Heuristic fallback: keyword-based classification
            return self._heuristic_classify(content)
    
    def _heuristic_classify(self, text: str) -> RouterResult:
        """
        Fallback keyword-based classification when JSON parsing fails.
        
        This ensures the Router never completely fails — even if the 
        local model outputs free-form text instead of JSON. 
        """
        text_lower = text.lower()
        
        # Vision keywords
        vision_keywords = ["screen", "look", "see", "ekran", "bak", "gör", "oku", "error"]
        if any(kw in text_lower for kw in vision_keywords):
            return RouterResult(intent=Intent.VISION, confidence=0.6, reasoning="heuristic: vision keyword")
        
        # System keywords
        system_keywords = ["stop", "bye", "goodbye", "dur", "kapat", "görüşürüz", "hoşçakal"]
        if any(kw in text_lower for kw in system_keywords):
            return RouterResult(intent=Intent.SYSTEM, confidence=0.6, reasoning="heuristic: system keyword")
        
        # Tool keywords
        tool_keywords = ["open", "launch", "run", "aç", "çalıştır", "kur", "volume", "ses", "brightness"]
        if any(kw in text_lower for kw in tool_keywords):
            return RouterResult(intent=Intent.TOOL_CALL, confidence=0.6, reasoning="heuristic: tool keyword")
        
        # Default to conversation
        return RouterResult(intent=Intent.CONVERSATION, confidence=0.5, reasoning="heuristic: default")
