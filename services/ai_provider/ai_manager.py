import logging
from typing import Dict, Any, Optional
from .base import BaseLLMProvider, BaseTTSProvider, BaseImageProvider
from .adapters.default_llm import DefaultLLMProvider
from .adapters.pollinations_image import PollinationsImageProvider
from .adapters.default_tts import DefaultTTSProvider

logger = logging.getLogger(__name__)

class AIProviderManager:
    """
    Central Manager & Factory for AI Providers (Provider-Agnostic Design).
    Integrates BYOK (Bring Your Own Key) resolution and dynamic fallback chains.
    """

    _llm_providers: Dict[str, BaseLLMProvider] = {}
    _image_providers: Dict[str, BaseImageProvider] = {}
    _tts_providers: Dict[str, BaseTTSProvider] = {}

    @classmethod
    def register_llm(cls, provider: BaseLLMProvider):
        cls._llm_providers[provider.provider_name] = provider

    @classmethod
    def register_image(cls, provider: BaseImageProvider):
        cls._image_providers[provider.provider_name] = provider

    @classmethod
    def register_tts(cls, provider: BaseTTSProvider):
        cls._tts_providers[provider.provider_name] = provider

    @classmethod
    def get_llm(cls, name: str = "default_llm") -> BaseLLMProvider:
        return cls._llm_providers.get(name, DefaultLLMProvider())

    @classmethod
    def get_image(cls, name: str = "pollinations") -> BaseImageProvider:
        return cls._image_providers.get(name, PollinationsImageProvider())

    @classmethod
    def get_tts(cls, name: str = "default_tts") -> BaseTTSProvider:
        return cls._tts_providers.get(name, DefaultTTSProvider())

    @classmethod
    def resolve_llm_for_user(cls, user_profile: Optional[Any] = None) -> tuple[BaseLLMProvider, Optional[str]]:
        """
        Resolves the appropriate LLM provider and API key based on BYOK settings.
        Returns: (BaseLLMProvider, user_api_key_or_None)
        """
        if user_profile and user_profile.openai_api_key:
            logger.info(f"Using BYOK key for user {user_profile.user.username}")
            return cls.get_llm("default_llm"), user_profile.openai_api_key

        logger.info("Using default freemium fallback LLM engine.")
        return cls.get_llm("default_llm"), None

    @classmethod
    def list_available_providers(cls) -> Dict[str, list]:
        """Returns lists of registered provider names across categories."""
        return {
            "llm": list(cls._llm_providers.keys()),
            "image": list(cls._image_providers.keys()),
            "tts": list(cls._tts_providers.keys()),
        }

# Pre-register default freemium providers
AIProviderManager.register_llm(DefaultLLMProvider())
AIProviderManager.register_image(PollinationsImageProvider())
AIProviderManager.register_tts(DefaultTTSProvider())
