"""Provider factory for LLM providers."""
import os
import logging
from typing import Dict, Type, Optional, Any
from .providers.base import BaseLLMProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Factory for creating LLM provider instances."""
    
    # Registry of available providers
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]) -> None:
        logger.info(f"Inside the register_provider method of LLMProviderFactory with name: {name}")
        """
        Register a new provider.
        
        Args:
            name: Provider identifier
            provider_class: Provider class implementing BaseLLMProvider
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(f"Provider class must inherit from BaseLLMProvider")
        cls._providers[name.lower()] = provider_class
        logger.info(f"Registered LLM provider: {name}")
    
    @classmethod
    def get_available_providers(cls) -> list:
        logger.info(f"List of available providers requested. {list(cls._providers.keys())}")
        """Get list of available provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    def create_provider(
        cls,
        provider_name: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        logger.info(f"Creating provider: {provider_name} with model: {model} ")
        """
        Create a provider instance based on configuration.
        
        Args:
            provider_name: Provider name (defaults to LLM_PROVIDER env var or "ollama")
            model: Model name (defaults to LLM_MODEL env var or provider default)
            **kwargs: Additional provider-specific configuration
            
        Returns:
            Provider instance
            
        Raises:
            ValueError: If provider is not found or configuration is invalid
        """
        # Get provider name from parameter or environment
        provider_name = (provider_name or os.getenv("LLM_PROVIDER", "ollama")).lower()
        
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown LLM provider: {provider_name}. "
                f"Available providers: {available}"
            )
        
        provider_class = cls._providers[provider_name]
        
        # Get model from parameter or environment or use provider default
        if not model:
            # Check provider-specific model env var first (e.g., GEMINI_MODEL, OPENAI_MODEL)
            provider_model_env = {
                "ollama": "OLLAMA_MODEL",
                "openai": "OPENAI_MODEL",
                "gemini": "GEMINI_MODEL",
            }
            model_env_var = provider_model_env.get(provider_name)
            if model_env_var:
                model = os.getenv(model_env_var)
            
            # Fallback to generic LLM_MODEL if provider-specific not set
            if not model:
                model = os.getenv("LLM_MODEL")
            
            # Use provider-specific defaults if still not set
            if not model:
                defaults = {
                    "ollama": "llama3.2:latest",
                    "openai": "gpt-4",
                    "gemini": "gemini-pro",
                }
                model = defaults.get(provider_name, "llama3.2:latest")
        logger.info(f"Using model: {model} for provider: {provider_name}")
        
        # Get timeout from environment or use default
        timeout = int(os.getenv("LLM_TIMEOUT", "600"))
        
        # Get temperature from environment or use default
        temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        
        # Get max_tokens from environment if provided
        max_tokens = None
        if os.getenv("LLM_MAX_TOKENS"):
            max_tokens = int(os.getenv("LLM_MAX_TOKENS"))
        
        # Provider-specific configuration from environment
        provider_config = {}
        
        if provider_name == "openai":
            provider_config["api_key"] = os.getenv("OPENAI_API_KEY")
            provider_config["organization"] = os.getenv("OPENAI_ORG_ID")
        elif provider_name == "gemini":
            provider_config["api_key"] = os.getenv("GEMINI_API_KEY")
        elif provider_name == "ollama":
            provider_config["base_url"] = os.getenv("OLLAMA_BASE_URL")
        
        # Merge kwargs (explicit parameters override env vars)
        provider_config.update(kwargs)
        
        try:
            logger.info(f"Creating {provider_name} provider with model: {model}")
            provider = provider_class(
                model=model,
                timeout=timeout,
                temperature=temperature,
                max_tokens=max_tokens,
                **provider_config
            )
            logger.info(f"Successfully created {provider_name} provider")
            return provider
        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {str(e)}")
            raise ValueError(f"Failed to create {provider_name} provider: {str(e)}")

