"""
LLM Provider Factory.

Creates the appropriate LLMProvider instance based on configuration.
Supports dynamic provider selection per tier (Router, Worker, Synthesizer).
"""

from typing import Optional
from assistant.core.logging_config import logger
from assistant.brain.providers.base import LLMProvider


def create_provider(provider_type: str, model: str, 
                    api_key: Optional[str] = None,
                    base_url: Optional[str] = None,
                    temperature: float = 0.7) -> LLMProvider:
    """
    Factory function to create an LLM provider.
    
    Args:
        provider_type: Provider type ("openai", "ollama", "lmstudio")
        model: Model identifier (e.g. "gpt-4o-mini", "llama3")
        api_key: API key (required for cloud providers)
        base_url: Custom base URL (for Ollama, LM Studio, or proxy)
        temperature: Sampling temperature
        
    Returns:
        Configured LLMProvider instance
    """
    provider_type = provider_type.lower().strip()
    
    if provider_type == "openai":
        from assistant.brain.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
        )
    
    elif provider_type == "ollama":
        from assistant.brain.providers.ollama_provider import OllamaProvider
        return OllamaProvider(
            model=model,
            base_url=base_url or "http://localhost:11434",
            temperature=temperature,
        )
    
    elif provider_type == "lmstudio":
        # LM Studio also exposes an OpenAI-compatible API
        from assistant.brain.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model=model,
            api_key=api_key or "lm-studio",  # LM Studio doesn't need a real key
            base_url=base_url or "http://localhost:1234/v1",
            temperature=temperature,
        )
    
    else:
        logger.error(f"Unknown provider type: '{provider_type}'. Falling back to OpenAI.")
        from assistant.brain.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            model=model,
            api_key=api_key,
            temperature=temperature,
        )


def create_tier_providers() -> dict:
    """
    Create provider instances for each tier of the three-tier architecture.
    
    Reads configuration from Config to determine which provider/model
    to use for Router, Worker, and Synthesizer tiers.
    
    Returns:
        Dict with keys 'router', 'worker', 'synthesizer' → LLMProvider
    """
    from assistant.core.config import config
    
    providers = {}
    
    # Router Tier — fast, lightweight model for intent classification
    providers["router"] = create_provider(
        provider_type=config.ROUTER_PROVIDER,
        model=config.ROUTER_MODEL,
        api_key=config.OPENAI_API_KEY if config.ROUTER_PROVIDER == "openai" else None,
        base_url=config.OLLAMA_BASE_URL if config.ROUTER_PROVIDER == "ollama" else None,
        temperature=0.3,  # Low temperature for deterministic routing
    )
    logger.info(f"Router tier: {providers['router']}")
    
    # Worker Tier — capable model for task execution
    providers["worker"] = create_provider(
        provider_type=config.WORKER_PROVIDER,
        model=config.WORKER_MODEL,
        api_key=config.OPENAI_API_KEY if config.WORKER_PROVIDER == "openai" else None,
        base_url=config.OLLAMA_BASE_URL if config.WORKER_PROVIDER == "ollama" else None,
        temperature=config.LLM_TEMPERATURE,
    )
    logger.info(f"Worker tier: {providers['worker']}")
    
    # Synthesizer Tier — personality formatting
    providers["synthesizer"] = create_provider(
        provider_type=config.SYNTHESIZER_PROVIDER,
        model=config.SYNTHESIZER_MODEL,
        api_key=config.OPENAI_API_KEY if config.SYNTHESIZER_PROVIDER == "openai" else None,
        base_url=config.OLLAMA_BASE_URL if config.SYNTHESIZER_PROVIDER == "ollama" else None,
        temperature=0.8,  # Slightly creative for personality
    )
    logger.info(f"Synthesizer tier: {providers['synthesizer']}")
    
    return providers
