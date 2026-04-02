"""
Ollama LLM Provider.

Provides locally deployed LLM inference via Ollama's OpenAI-compatible API.
Supports models like Llama 3, Mistral, Qwen 2.5, and others running
on the user's machine without any cloud dependency.

Key design decisions:
- Uses Ollama's OpenAI-compatible endpoint (/v1/chat/completions)
  so we can reuse the OpenAI SDK instead of adding another dependency.
- Tool calling is supported natively by Ollama for compatible models.
- Falls back to prompt-injection-based tool selection for models
  that don't support native function calling.
"""

import json
from typing import Generator, Optional
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider, LLMResponse, StreamChunk


class OllamaProvider(LLMProvider):
    """
    Locally deployed LLM provider via Ollama.
    
    Connects to Ollama's local server (default: http://localhost:11434)
    using its OpenAI-compatible API layer. This means we get tool calling,
    streaming, and structured outputs without adding custom HTTP logic.
    
    Optimized for:
    - Router tier: Fast intent classification with small models (llama3-8b, phi3)
    - Synthesizer tier: Personality formatting with medium models
    - Worker tier: Full task execution with large models (llama3-70b, mixtral)
    """
    
    def __init__(self, model: str = "llama3", api_key: str = None,
                 base_url: str = "http://localhost:11434", temperature: float = 0.7):
        super().__init__(model, api_key=api_key or "ollama", base_url=base_url, temperature=temperature)
        
        # Ollama's OpenAI-compatible endpoint
        self._openai_base_url = f"{base_url}/v1"
        self._client = None
        self._native_tool_support = True  # Assume true, verify on connect
        
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key="ollama",  # Ollama doesn't need a real key
                base_url=self._openai_base_url,
            )
            logger.info(f"Ollama provider initialized: model={model}, base_url={base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama provider: {e}")
    
    @property
    def provider_name(self) -> str:
        return "Ollama"
    
    @property
    def supports_tools(self) -> bool:
        return self._native_tool_support
    
    @property
    def supports_vision(self) -> bool:
        # Vision-capable local models
        vision_models = ["llava", "bakllava", "moondream", "llama3.2-vision"]
        return any(vm in self._model.lower() for vm in vision_models)
    
    @property
    def is_local(self) -> bool:
        return True
    
    def is_available(self) -> bool:
        """Check if Ollama server is running and the model is available."""
        if not self._client:
            return False
        try:
            import urllib.request
            import urllib.error
            
            # Quick health check on Ollama's native API
            req = urllib.request.Request(f"{self._base_url}/api/tags")
            req.add_header("Content-Type", "application/json")
            response = urllib.request.urlopen(req, timeout=3)
            
            if response.status == 200:
                data = json.loads(response.read().decode())
                available_models = [m["name"] for m in data.get("models", [])]
                
                # Check if our target model is available
                model_found = any(
                    self._model in m or m.startswith(self._model) 
                    for m in available_models
                )
                
                if not model_found:
                    logger.warning(
                        f"Ollama is running but model '{self._model}' not found. "
                        f"Available: {available_models}. Run: ollama pull {self._model}"
                    )
                    return False
                    
                return True
            return False
            
        except urllib.error.URLError:
            logger.warning("Ollama server not reachable. Is it running? (ollama serve)")
            return False
        except Exception as e:
            logger.warning(f"Ollama availability check failed: {e}")
            return False
    
    def complete(self, messages: list[dict], tools: list[dict] = None,
                 stream: bool = False, max_tokens: int = None) -> LLMResponse | Generator[StreamChunk, None, None]:
        """
        Send completion request to locally running Ollama.
        
        Uses Ollama's OpenAI-compatible API, so the interface is identical
        to the OpenAI provider. The key difference is zero network latency
        to the inference endpoint — all computation is local.
        """
        if not self._client:
            if stream:
                def _error_stream():
                    yield StreamChunk(chunk_type="content", content="[neutral] Ollama bağlantısı yok.")
                return _error_stream()
            return LLMResponse(content="[neutral] Ollama bağlantısı yok.")
        
        # Build request
        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": stream,
        }
        
        # Tool calling — try native first, fall back to prompt injection
        if tools and self._native_tool_support:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        elif tools and not self._native_tool_support:
            # Inject tool descriptions into the system prompt for models
            # that don't support native function calling
            messages = self._inject_tools_into_prompt(messages, tools)
            kwargs["messages"] = messages
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        try:
            if stream:
                return self._stream_completion(kwargs)
            else:
                return self._sync_completion(kwargs)
        except Exception as e:
            error_msg = str(e)
            
            # If tool calling failed, retry without tools (prompt injection fallback)
            if tools and "tool" in error_msg.lower():
                logger.warning(f"Ollama native tool calling failed, falling back to prompt injection: {e}")
                self._native_tool_support = False
                
                # Rebuild without tools kwarg
                kwargs.pop("tools", None)
                kwargs.pop("tool_choice", None)
                kwargs["messages"] = self._inject_tools_into_prompt(messages, tools)
                
                try:
                    if stream:
                        return self._stream_completion(kwargs)
                    else:
                        return self._sync_completion(kwargs)
                except Exception as e2:
                    logger.error(f"Ollama fallback also failed: {e2}")
            
            logger.error(f"Ollama provider error: {e}")
            if stream:
                def _error_stream():
                    yield StreamChunk(chunk_type="content", content="[sad] Yerel model çalışmıyor...")
                return _error_stream()
            return LLMResponse(content="[sad] Yerel model çalışmıyor...")
    
    def _sync_completion(self, kwargs: dict) -> LLMResponse:
        """Non-streaming completion via Ollama."""
        kwargs["stream"] = False
        response = self._client.chat.completions.create(**kwargs)
        
        choice = response.choices[0]
        tool_calls = []
        
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                })
        
        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "stop",
        )
    
    def _stream_completion(self, kwargs: dict) -> Generator[StreamChunk, None, None]:
        """Streaming completion via Ollama."""
        kwargs["stream"] = True
        stream = self._client.chat.completions.create(**kwargs)
        
        for chunk in stream:
            delta = chunk.choices[0].delta
            
            if delta.content:
                yield StreamChunk(
                    chunk_type="content",
                    content=delta.content,
                )
            
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield StreamChunk(
                        chunk_type="tool_call",
                        tool_call_index=tc.index,
                        tool_call_id=tc.id or "",
                        tool_call_name=tc.function.name or "" if tc.function else "",
                        tool_call_arguments=tc.function.arguments or "" if tc.function else "",
                    )
    
    def _inject_tools_into_prompt(self, messages: list[dict], tools: list[dict]) -> list[dict]:
        """
        For models without native tool calling, inject tool descriptions
        into the system prompt so the model can output structured JSON.
        
        This is the prompt-injection fallback strategy for smaller local models.
        """
        tool_descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            params = json.dumps(func.get("parameters", {}), indent=2)
            tool_descriptions.append(f"- {name}: {desc}\n  Parameters: {params}")
        
        injection = (
            "\n\n--- AVAILABLE TOOLS ---\n"
            "You have access to the following tools. To use a tool, respond with EXACTLY this JSON format:\n"
            '{"tool_call": {"name": "tool_name", "arguments": {"arg1": "value1"}}}\n\n'
            + "\n".join(tool_descriptions)
            + "\n--- END TOOLS ---\n"
            "If no tool is needed, respond normally without JSON."
        )
        
        # Inject into the first system message
        modified = []
        injected = False
        for msg in messages:
            if msg["role"] == "system" and not injected:
                modified.append({
                    "role": "system",
                    "content": msg["content"] + injection,
                })
                injected = True
            else:
                modified.append(msg)
        
        return modified
