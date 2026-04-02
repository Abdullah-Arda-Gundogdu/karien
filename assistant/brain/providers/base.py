"""
Abstract base class for LLM providers.

Provides a unified interface for both cloud-based (OpenAI, Anthropic)
and locally deployed (Ollama, LM Studio) language models.
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Structured response from an LLM provider."""
    content: str
    tool_calls: list = None
    finish_reason: str = "stop"
    
    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class StreamChunk:
    """A single chunk from a streaming LLM response."""
    chunk_type: str  # "content", "tool_call"
    content: str = ""
    tool_call_index: int = 0
    tool_call_id: str = ""
    tool_call_name: str = ""
    tool_call_arguments: str = ""


class LLMProvider(ABC):
    """
    Abstract interface for language model providers.
    
    Supports both cloud APIs (OpenAI, Anthropic) and local inference
    servers (Ollama, LM Studio) through a unified interface.
    """
    
    def __init__(self, model: str, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None, temperature: float = 0.7):
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._temperature = temperature
    
    @property
    def model_name(self) -> str:
        """The model identifier being used."""
        return self._model
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'OpenAI', 'Ollama')."""
        pass
    
    @property
    @abstractmethod
    def supports_tools(self) -> bool:
        """Whether this provider supports native function/tool calling."""
        pass
    
    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """Whether this provider supports image/vision inputs."""
        pass
    
    @property
    def is_local(self) -> bool:
        """Whether this provider runs inference locally."""
        return False
    
    @abstractmethod
    def complete(self, messages: list[dict], tools: list[dict] = None,
                 stream: bool = False, max_tokens: int = None) -> LLMResponse | Generator[StreamChunk, None, None]:
        """
        Send a completion request to the LLM.
        
        Args:
            messages: Chat messages in OpenAI format [{role, content}, ...]
            tools: Tool definitions in OpenAI format (optional)
            stream: If True, returns a generator of StreamChunks
            max_tokens: Maximum response tokens (optional)
            
        Returns:
            LLMResponse if stream=False, Generator[StreamChunk] if stream=True
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is reachable and ready."""
        pass
    
    def __repr__(self) -> str:
        return f"{self.provider_name}({self._model})"
