"""Google Gemini LLM provider implementation."""
import warnings
import logging
import functools
from typing import Optional
import os
import ssl
from .base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderConnectionError,
    LLMProviderAuthenticationError
)

logger = logging.getLogger(__name__)

# Disable SSL verification for Gemini API (to avoid CERTIFICATE_VERIFY_FAILED errors)
# This is useful in corporate environments with proxy/certificate issues
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

# Disable SSL verification globally for this module
ssl._create_default_https_context = ssl._create_unverified_context

# Disable SSL warnings
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

# Patch httpx to disable SSL verification by default (google-genai uses httpx)
try:
    import httpx
    
    # Store original Client class init
    _original_httpx_client_init = httpx.Client.__init__
    
    @functools.wraps(_original_httpx_client_init)
    def _patched_httpx_client_init(self, *args, **kwargs):
        """Patched httpx.Client.__init__ to force verify=False"""
        # Force verify=False regardless of what's passed
        kwargs['verify'] = False
        return _original_httpx_client_init(self, *args, **kwargs)
    
    # Apply the patch
    httpx.Client.__init__ = _patched_httpx_client_init
    
    # Also patch AsyncClient if it exists
    if hasattr(httpx, 'AsyncClient'):
        _original_async_client_init = httpx.AsyncClient.__init__
        
        @functools.wraps(_original_async_client_init)
        def _patched_async_client_init(self, *args, **kwargs):
            """Patched httpx.AsyncClient.__init__ to force verify=False"""
            kwargs['verify'] = False
            return _original_async_client_init(self, *args, **kwargs)
        
        httpx.AsyncClient.__init__ = _patched_async_client_init
    
    logger.info("Patched httpx to disable SSL verification by default")
except (ImportError, AttributeError, TypeError) as e:
    logger.warning(f"Could not patch httpx for SSL verification: {e}")

# Try to import Google GenAI (new package), but make it optional
try:
    import google.genai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenAI library not installed. Install with: pip install google-genai")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider using GenAI API."""
    
    def __init__(
        self,
        model: str = "gemini-pro",
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Gemini provider.
        
        Args:
            model: Gemini model name (e.g., "gemini-pro", "gemini-1.5-pro")
            timeout: Request timeout in seconds
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            api_key: Google API key (defaults to GEMINI_API_KEY env var)
            **kwargs: Additional Gemini-specific config
        """
        if not GEMINI_AVAILABLE:
            raise ImportError(
                "Google GenAI library not installed. Install with: pip install google-genai"
            )
        
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # Configure Gemini client before validation
        self.client = None
        if self.api_key:
            # New API: Create client with API key
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = model
        
        # Now call super().__init__ which will call _validate_config()
        super().__init__(model, timeout, temperature, max_tokens, **kwargs)
    
    def _validate_config(self) -> None:
        """Validate Gemini configuration."""
        if not self.model:
            raise ValueError("Gemini model name is required")
        
        if not self.api_key:
            raise LLMProviderAuthenticationError(
                "gemini",
                "API key is required. Set GEMINI_API_KEY environment variable or pass api_key parameter."
            )
        
        if not self.client:
            raise LLMProviderConnectionError(
                "gemini",
                self.model,
                "Failed to initialize Gemini client"
            )
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Gemini API.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (safety_settings, generation_config, etc.)
            
        Returns:
            Generated text response
        """
        try:
            logger.info(f"Gemini generating with model: {self.model}")
            
            # New API: Generate content using client
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_output_tokens": self.max_tokens or kwargs.get("max_tokens"),
                }
            )
            
            # Extract text from response
            if not response:
                raise LLMProviderError("Gemini returned empty response")
            
            # Handle different response formats (new API structure may differ)
            if hasattr(response, 'text') and response.text:
                output = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                # Handle candidate-based responses
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    output = ''.join(part.text for part in candidate.content.parts if hasattr(part, 'text'))
                else:
                    output = str(candidate)
            else:
                output = str(response)
            
            if not output or not output.strip():
                raise LLMProviderError("Gemini returned empty response")
            
            logger.info(f"Gemini returned output (length: {len(output)}, first 200 chars: {output[:200]})")
            return output.strip()
            
        except Exception as e:
            error_msg = str(e)
            if "API_KEY" in error_msg or "authentication" in error_msg.lower():
                raise LLMProviderAuthenticationError("gemini", error_msg)
            elif "timeout" in error_msg.lower():
                raise LLMProviderTimeoutError(self.timeout, "gemini", self.model)
            elif "connection" in error_msg.lower() or "network" in error_msg.lower():
                raise LLMProviderConnectionError("gemini", self.model, error_msg)
            else:
                logger.error(f"Unexpected Gemini error: {error_msg}")
                raise LLMProviderConnectionError("gemini", self.model, error_msg)
    
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        return "gemini"