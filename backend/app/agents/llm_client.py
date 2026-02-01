"""LLM client wrapper for agent nodes."""

from typing import List, Dict, Any, Optional
from openai import OpenAI
from sqlalchemy.orm import Session

from app.models import LLMConfig
from app.core.database import SessionLocal


from app.core.config import get_settings


class LLMClient:
    """Wrapper for LLM API calls."""

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize LLM client.

        Args:
            db: Database session (optional, will create if not provided)
        """
        self.db = db or SessionLocal()
        self._client: Optional[OpenAI] = None
        # We will use a mock object or simple dict for config to keep compatibility
        self._config = None
        self._load_active_config()

    def _load_active_config(self):
        """Load LLM configuration from environment variables (.env)."""
        settings = get_settings()

        # Create a simple object to mimic LLMConfig model interface
        class EnvConfig:
            api_endpoint = settings.OPENAI_API_BASE
            model_name = settings.OPENAI_MODEL_NAME
            temperature = int(
                settings.OPENAI_TEMPERATURE * 100
            )  # Maintain int * 100 convention
            max_tokens = settings.OPENAI_MAX_TOKENS
            top_p = 100  # Default
            frequency_penalty = 0
            presence_penalty = 0

        self._config = EnvConfig()

        # Initialize OpenAI client with env vars
        self._client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        Send chat completion request to LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens

        Returns:
            LLM response content
        """
        if not self._client or not self._config:
            # Fallback response when LLM is not configured
            return "LLM not configured. Please configure LLM settings first."

        try:
            # Use config values or overrides
            temp = (
                temperature
                if temperature is not None
                else (self._config.temperature / 100.0)
            )
            tokens = max_tokens if max_tokens is not None else self._config.max_tokens

            response = self._client.chat.completions.create(
                model=self._config.model_name,
                messages=messages,
                temperature=temp,
                max_tokens=tokens,
                top_p=self._config.top_p / 100.0,
                frequency_penalty=self._config.frequency_penalty / 100.0,
                presence_penalty=self._config.presence_penalty / 100.0,
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def generate_prompt(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, str]]:
        """
        Generate messages list for chat completion.

        Args:
            system_prompt: System prompt defining agent behavior
            user_message: User's message
            context: Additional context to include

        Returns:
            Messages list for API call
        """
        messages = [{"role": "system", "content": system_prompt}]

        if context:
            context_str = "\n\nContext:\n"
            for key, value in context.items():
                context_str += f"{key}: {value}\n"
            messages.append({"role": "system", "content": context_str})

        messages.append({"role": "user", "content": user_message})

        return messages

    def close(self):
        """Close database session if we created it."""
        if self.db:
            self.db.close()
