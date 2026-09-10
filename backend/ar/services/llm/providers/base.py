"""Base provider interface for LLM providers."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when LLM request times out."""
    def __init__(self, timeout: int, provider: str, model: str):
        self.timeout = timeout
        self.provider = provider
        self.model = model
        super().__init__(f"LLM request timed out after {timeout}s for {provider}/{model}")


class LLMProviderConnectionError(LLMProviderError):
    """Raised when LLM connection fails."""
    def __init__(self, provider: str, model: str, message: str):
        self.provider = provider
        self.model = model
        super().__init__(f"LLM connection error for {provider}/{model}: {message}")


class LLMProviderAuthenticationError(LLMProviderError):
    """Raised when authentication fails."""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"Authentication error for {provider}: {message}")


class LLMProviderRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""
    def __init__(self, provider: str, message: str):
        self.provider = provider
        super().__init__(f"Rate limit exceeded for {provider}: {message}")


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(
        self,
        model: str,
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize provider.
        
        Args:
            model: Model identifier
            timeout: Request timeout in seconds
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific configuration
        """
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.config = kwargs
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider configuration. Raise exception if invalid."""
        pass
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated text response
            
        Raises:
            LLMProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return provider identifier (e.g., 'ollama', 'openai', 'gemini')."""
        pass
    
    def get_model(self) -> str:
        """Return model identifier."""
        return self.model

