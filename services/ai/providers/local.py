import os
import logging
from typing import Dict, Any, List
from services.ai.base import (
    BaseLLMAdapter, BaseVideoAdapter, BaseTTSAdapter, ProviderNotConfiguredException
)
from services.ai_provider.adapters.default_llm import DefaultLLMProvider
from services.ai_provider.adapters.default_tts import DefaultTTSProvider
from services.ai_provider.adapters.pollinations_image import PollinationsImageProvider
from services.video.ffmpeg_renderer import FFmpegVideoRenderer

logger = logging.getLogger(__name__)

class LocalFallbackAdapter(BaseLLMAdapter, BaseVideoAdapter, BaseTTSAdapter):
    """
    Local Fallback Engine Adapter.
    Uses free engines (gTTS, Pollinations image, local FFmpeg renderer, smart template LLM).
    Guaranteed available on all installations.
    """
    name = "Local Fallback Engine"
    provider_id = "local"
    is_paid = False

    def __init__(self):
        self._llm = DefaultLLMProvider()
        self._tts = DefaultTTSProvider()
        self._image_gen = PollinationsImageProvider()
        self._ffmpeg = FFmpegVideoRenderer()


    def is_configured(self, user_profile=None) -> bool:
        return True

    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        return {'status': 'AVAILABLE', 'reset_at': None, 'error': None}

    def generate_script(self, user_profile, prompt: str, history_topics: List[str] = None) -> Dict[str, Any]:
        api_key = getattr(user_profile, 'openai_api_key', None) if user_profile else None
        return self._llm.generate_structured_content(
            user_profile=user_profile,
            user_idea=prompt,
            history_topics=history_topics,
            api_key=api_key
        )

    def generate_scenes(self, script: str) -> List[Dict[str, str]]:
        """Splits script into 3-5 visual scenes for video generation."""
        lines = [line.strip() for line in script.split('.') if line.strip()]
        scenes = []
        for idx, line in enumerate(lines[:5], start=1):
            scenes.append({
                'scene_number': idx,
                'prompt': f"Cinematic scene {idx}: {line[:80]}",
                'narration': line
            })
        if not scenes:
            scenes.append({'scene_number': 1, 'prompt': 'Cinematic vertical background', 'narration': script[:100]})
        return scenes

    def generate_audio(self, text: str, output_path: str, language: str = "Russian") -> str:
        self._tts.generate_audio(text=text, output_path=output_path, language=language)
        return output_path

    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        """
        Renders video using Pollinations visual background + TTS audio + FFmpeg subtitles.
        Used as primary local fallback engine.
        """
        dir_path = os.path.dirname(output_path)
        image_path = os.path.join(dir_path, 'background.jpg')
        audio_path = os.path.join(dir_path, 'voiceover.mp3')

        # Combine narration
        full_text = " ".join([s.get('narration', '') for s in scenes])
        if not full_text:
            full_text = "CreatorOS Daily Video Update."

        # 1. Generate visual background
        prompt = scenes[0].get('prompt', 'Cinematic AI topic background') if scenes else 'Cinematic background'
        self._image_gen.generate_image(prompt=prompt, output_path=image_path, width=1080, height=1920)

        # 2. Generate voiceover audio
        self._tts.generate_audio(text=full_text, output_path=audio_path, language='Russian')

        # 3. Render MP4 video via FFmpeg
        self._ffmpeg.render_video(
            image_path=image_path,
            audio_path=audio_path,
            script_text=full_text,
            output_path=output_path,
            duration_seconds=45
        )
        return output_path
