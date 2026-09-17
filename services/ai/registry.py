import logging
from typing import Dict, Any, Optional
from services.ai.base import BaseAIProvider
from services.ai.providers.local import LocalFallbackAdapter
from services.ai.providers.google import GoogleAIAdapter
from services.ai.providers.openai import OpenAIAdapter
from services.ai.providers.runway import RunwayAdapter

logger = logging.getLogger(__name__)

class ProviderRegistry:
    """
    Registry for managing available CreatorOS AI provider adapters.
    """
    _registry: Dict[str, BaseAIProvider] = {}

    @classmethod
    def register_defaults(cls):
        """Registers default built-in AI provider adapters."""
        cls.register(LocalFallbackAdapter())
        cls.register(GoogleAIAdapter())
        cls.register(OpenAIAdapter())
        cls.register(RunwayAdapter())

    @classmethod
    def register(cls, provider: BaseAIProvider):
        cls._registry[provider.provider_id] = provider
        logger.info(f"Registered AI Provider: {provider.name} ({provider.provider_id})")

    @classmethod
    def get(cls, provider_id: str) -> Optional[BaseAIProvider]:
        if not cls._registry:
            cls.register_defaults()
        return cls._registry.get(provider_id)

    @classmethod
    def list_all(cls) -> Dict[str, BaseAIProvider]:
        if not cls._registry:
            cls.register_defaults()
        return dict(cls._registry)

# Initialize defaults
ProviderRegistry.register_defaults()
