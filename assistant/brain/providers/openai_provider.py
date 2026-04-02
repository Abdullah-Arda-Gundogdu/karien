"""
OpenAI LLM Provider.

Wraps the OpenAI Python SDK to provide cloud-based inference
via GPT-4o, GPT-4o-mini, and other OpenAI models.
"""

import time
from typing import Generator, Optional
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider, LLMResponse, StreamChunk


class OpenAIProvider(LLMProvider):
    """
    OpenAI cloud-based LLM provider.
    
    Supports streaming, function calling, and vision.
    Used as the default provider and as the Worker tier
    when maximum capability is needed.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: str = None,
                 base_url: str = None, temperature: float = 0.7):
        super().__init__(model, api_key, base_url, temperature)
        self._client = None
        
        if api_key:
            try:
                from openai import OpenAI
                kwargs = {"api_key": api_key}
                if base_url:
                    kwargs["base_url"] = base_url
                self._client = OpenAI(**kwargs)
                logger.info(f"OpenAI provider initialized: model={model}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    @property
    def supports_tools(self) -> bool:
        return True
    
    @property
    def supports_vision(self) -> bool:
        return "gpt-4o" in self._model or "gpt-4-vision" in self._model
    
    def is_available(self) -> bool:
        """Check if OpenAI API is reachable."""
        if not self._client:
            return False
        try:
            # Lightweight check — list models
            self._client.models.list()
            return True
        except Exception:
            return False
    
    def complete(self, messages: list[dict], tools: list[dict] = None,
                 stream: bool = False, max_tokens: int = None,
                 retry_count: int = 3, retry_delay: float = 1.0) -> LLMResponse | Generator[StreamChunk, None, None]:
        """
        Send completion request to OpenAI.
        
        Args:
            messages: Chat messages
            tools: Tool definitions (OpenAI function calling format)
            stream: Whether to stream the response
            max_tokens: Max response tokens
            retry_count: Number of retries on failure
            retry_delay: Delay between retries in seconds
        """
        if not self._client:
            if stream:
                def _error_stream():
                    yield StreamChunk(chunk_type="content", content="[neutral] OpenAI bağlantısı yok.")
                return _error_stream()
            return LLMResponse(content="[neutral] OpenAI bağlantısı yok.")
        
        # Build request kwargs
        kwargs = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
            "stream": stream,
        }
        
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        # Retry logic
        last_error = None
        for attempt in range(retry_count):
            try:
                if stream:
                    return self._stream_completion(kwargs)
                else:
                    return self._sync_completion(kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"OpenAI attempt {attempt+1}/{retry_count} failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(retry_delay)
        
        # All retries exhausted
        logger.error(f"OpenAI provider failed after {retry_count} attempts: {last_error}")
        if stream:
            def _error_stream():
                yield StreamChunk(chunk_type="content", content="[sad] Beynime bağlanamıyorum...")
            return _error_stream()
        return LLMResponse(content="[sad] Beynime bağlanamıyorum...")
    
    def _sync_completion(self, kwargs: dict) -> LLMResponse:
        """Non-streaming completion."""
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
        """Streaming completion — yields StreamChunks."""
        kwargs["stream"] = True
        stream = self._client.chat.completions.create(**kwargs)
        
        for chunk in stream:
            delta = chunk.choices[0].delta
            
            # Content chunks
            if delta.content:
                yield StreamChunk(
                    chunk_type="content",
                    content=delta.content,
                )
            
            # Tool call chunks
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    yield StreamChunk(
                        chunk_type="tool_call",
                        tool_call_index=tc.index,
                        tool_call_id=tc.id or "",
                        tool_call_name=tc.function.name or "" if tc.function else "",
                        tool_call_arguments=tc.function.arguments or "" if tc.function else "",
                    )
