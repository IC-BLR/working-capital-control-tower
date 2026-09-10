"""Ollama LLM provider implementation."""
import subprocess
import logging
from typing import Optional
from .base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMProviderTimeoutError,
    LLMProviderConnectionError
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Ollama provider using local subprocess execution."""
    
    def __init__(
        self,
        model: str = "llama3.2:latest",
        timeout: int = 120,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        base_url: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Ollama provider.
        
        Args:
            model: Ollama model name (e.g., "llama3.2:latest")
            timeout: Request timeout in seconds
            temperature: Sampling temperature
            max_tokens: Maximum tokens (not used by Ollama CLI)
            base_url: Ollama API base URL (for future API support)
            **kwargs: Additional Ollama-specific config
        """
        self.base_url = base_url
        super().__init__(model, timeout, temperature, max_tokens, **kwargs)
    
    def _validate_config(self) -> None:
        """Validate Ollama configuration."""
        if not self.model:
            raise ValueError("Ollama model name is required")
        
        # Check if ollama command is available
        try:
            result = subprocess.run(
                ["ollama", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning("Ollama command may not be available")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("Ollama command not found. Ensure Ollama is installed and in PATH")
    
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate text using Ollama CLI.
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (context, stream, etc.)
            
        Returns:
            Generated text response
        """
        try:
            logger.info(f"Ollama generating with model: {self.model}")
            
            # Build ollama command
            cmd = ["ollama", "run", self.model]
            
            # Execute with timeout
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else "Unknown error"
                logger.error(f"Ollama command failed. Return code: {result.returncode}, Error: {error_msg}")
                raise LLMProviderConnectionError(
                    "ollama",
                    self.model,
                    f"Command failed with return code {result.returncode}. Error: {error_msg}"
                )
            
            output = result.stdout.strip()
            logger.info(f"Ollama returned output (length: {len(output)})")
            return output
            
        except subprocess.TimeoutExpired:
            raise LLMProviderTimeoutError(self.timeout, "ollama", self.model)
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderConnectionError("ollama", self.model, str(e))
    
    def get_provider_name(self) -> str:
        """Return provider identifier."""
        return "ollama"

