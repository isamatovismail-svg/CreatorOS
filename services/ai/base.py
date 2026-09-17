from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseAIProvider(ABC):
    """
    Abstract Base Class for all CreatorOS AI Providers.
    Defines common status, health check, and quota inquiry contracts.
    """
    name: str = "Base Provider"
    provider_id: str = "base"
    is_paid: bool = False

    @abstractmethod
    def is_configured(self, user_profile=None) -> bool:
        """Returns True if provider has valid environment keys or user BYOK keys."""
        pass

    @abstractmethod
    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        """
        Queries actual provider API for quota status.
        Returns dict: {'status': 'AVAILABLE' | 'EXHAUSTED', 'reset_at': Optional[datetime], 'error': Optional[str]}
        Never fakes status or reset times.
        """
        pass


class BaseLLMAdapter(BaseAIProvider):
    """Adapter interface for Text & Script generation models."""
    type: str = "LLM"

    @abstractmethod
    def generate_script(self, user_profile, prompt: str, history_topics: List[str] = None) -> Dict[str, Any]:
        """Generates structured video metadata (title, hook, script, caption, hashtags)."""
        pass

    @abstractmethod
    def generate_scenes(self, script: str) -> List[Dict[str, str]]:
        """Breaks down a video script into visual scene descriptions."""
        pass


class BaseVideoAdapter(BaseAIProvider):
    """Adapter interface for Video generation models (e.g. Veo, Sora, Runway)."""
    type: str = "VIDEO"

    @abstractmethod
    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        """
        Generates moving video clip(s) for the provided scene breakdowns.
        Returns the output MP4 file path on success.
        If provider is not configured or unavailable, raises ProviderNotAvailableException.
        """
        pass


class BaseTTSAdapter(BaseAIProvider):
    """Adapter interface for Speech / Audio generation."""
    type: str = "TTS"

    @abstractmethod
    def generate_audio(self, text: str, output_path: str, language: str = "Russian") -> str:
        """Generates audio voiceover file."""
        pass


class ProviderException(Exception):
    """Base exception for provider errors."""
    code: str = "PROVIDER_ERROR"


class ProviderNotConfiguredException(ProviderException):
    code: str = "NOT_CONFIGURED"


class QuotaExceededException(ProviderException):
    code: str = "QUOTA_EXCEEDED"


class AuthException(ProviderException):
    code: str = "AUTH_ERROR"


class RateLimitedException(ProviderException):
    code: str = "RATE_LIMITED"
