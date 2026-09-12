from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class BaseLLMProvider(ABC):
    """
    Abstract Base Class for Large Language Model (LLM) Providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generates text response from the given prompt.
        """
        pass


class BaseTTSProvider(ABC):
    """
    Abstract Base Class for Text-to-Speech (TTS) Providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_audio(
        self,
        text: str,
        output_path: str,
        voice: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generates speech audio from text and saves to output_path.
        Returns the absolute file path.
        """
        pass


class BaseImageProvider(ABC):
    """
    Abstract Base Class for Image & Visual Generator Providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1080,
        height: int = 1920,
        api_key: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generates image from prompt and saves to output_path.
        Returns the absolute file path.
        """
        pass


class BaseVideoProvider(ABC):
    """
    Abstract Base Class for Video Rendering & Generation Providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def render_video(
        self,
        image_path: str,
        audio_path: str,
        script_text: str,
        output_path: str,
        duration_seconds: int = 45,
        **kwargs
    ) -> str:
        """
        Renders a vertical 9:16 MP4 video from image, audio, and subtitles.
        Returns the absolute video file path.
        """
        pass


class BaseTopicProvider(ABC):
    """
    Abstract Base Class for Topic & Trend Selection Providers.
    """
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    def select_topic(
        self,
        niche: str,
        language: str = 'Russian',
        recent_topics: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Selects a fresh content topic using niche, history, and fallback chains.
        """
        pass
