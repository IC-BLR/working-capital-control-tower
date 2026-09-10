"""OpenAI LLM provider implementation."""
import logging
from typing import Optional
import os
from .base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderConnectionError,
    LLMProviderAuthenticationError,
    LLMProviderRateLimitError
)

logger = logging.getLogger(__name__)

# Try to import OpenAI, but make it optional
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. Install with: pip install openai")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider using OpenAI API."""
    
    def __init__(
        self,
        model: str = "gpt-4",
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            model: OpenAI model name (e.g., "gpt-4", "gpt-3.5-turbo")
            timeout: Request timeout in seconds
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            organization: OpenAI organization ID (optional)
            **kwargs: Additional OpenAI-specific config
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI library not installed. Install with: pip install openai"
            )
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.organization = organization or os.getenv("OPENAI_ORG_ID")
        super().__init__(model, timeout, temperature, max_tokens, **kwargs)
        
        # Initialize OpenAI client
        self.client = openai.OpenAI(
            api_key=self.api_key,
            organization=self.organization,
            timeout=self.timeout
        )
    
    def _validate_config(self) -> None:
        """Validate OpenAI configuration."""
        if not self.model:
            raise ValueError("OpenAI model name is required")
        
        if not self.api_key:
            raise LLMProviderAuthenticationError(
                "openai",
                "API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using OpenAI API.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (functions, function_call, etc.)
            
        Returns:
            Generated text response
        """
        try:
            logger.info(f"OpenAI generating with model: {self.model}")
            
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": kwargs.get("temperature", self.temperature),
            }
            
            if self.max_tokens:
                request_params["max_tokens"] = self.max_tokens
            elif "max_tokens" in kwargs:
                request_params["max_tokens"] = kwargs["max_tokens"]
            
            # Add provider-specific parameters
            for key in ["functions", "function_call", "logprobs", "top_p", "frequency_penalty", "presence_penalty"]:
                if key in kwargs:
                    request_params[key] = kwargs[key]
            
            # Make API call
            response = self.client.chat.completions.create(**request_params)
            
            # Extract text from response
            if not response.choices or len(response.choices) == 0:
                raise LLMProviderError("OpenAI returned empty response")
            
            output = response.choices[0].message.content
            if not output:
                raise LLMProviderError("OpenAI returned empty content")
            
            logger.info(f"OpenAI returned output (length: {len(output)})")
            return output.strip()
            
        except openai.AuthenticationError as e:
            raise LLMProviderAuthenticationError("openai", str(e))
        except openai.RateLimitError as e:
            raise LLMProviderRateLimitError("openai", str(e))
        except openai.APITimeoutError as e:
            raise LLMProviderTimeoutError(self.timeout, "openai", self.model)
        except openai.APIConnectionError as e:
            raise LLMProviderConnectionError("openai", self.model, str(e))
        except LLMProviderError:
            raise
        except Exception as e:
            logger.error(f"Unexpected OpenAI error: {str(e)}")
            raise LLMProviderConnectionError("openai", self.model, str(e))
    
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        return "openai"

