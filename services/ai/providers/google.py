import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from services.ai.base import (
    BaseLLMAdapter, BaseVideoAdapter,
    ProviderNotConfiguredException, QuotaExceededException, ProviderException
)
from services.video.ffmpeg_renderer import FFmpegVideoRenderer
from services.ai_provider.adapters.default_tts import DefaultTTSProvider

logger = logging.getLogger(__name__)

class GoogleAIAdapter(BaseLLMAdapter, BaseVideoAdapter):
    """
    Google AI (Veo / Gemini) Provider.
    Handles Google Gemini script generation and Google Veo generative video clips via official google-genai SDK.
    """
    name = "Google AI (Veo / Gemini)"
    provider_id = "google"
    is_paid = True

    def _get_api_key(self, user_profile=None) -> str:
        key = os.getenv("GOOGLE_VEO_API_KEY", os.getenv("GEMINI_API_KEY", ""))
        if not key and user_profile and hasattr(user_profile, 'user') and hasattr(user_profile.user, 'ai_accounts'):
            account = user_profile.user.ai_accounts.filter(provider='google', status='ACTIVE').first()
            if account and account.access_token:
                key = account.access_token
        return key

    def is_configured(self, user_profile=None) -> bool:
        return bool(self._get_api_key(user_profile))

    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            return {
                'status': 'NOT_CONFIGURED',
                'reset_at': None,
                'error': 'No free real-video provider is currently configured.'
            }
        
        if user_profile and hasattr(user_profile, 'user') and hasattr(user_profile.user, 'ai_accounts'):
            account = user_profile.user.ai_accounts.filter(provider='google', status='ACTIVE').first()
            if account and account.quota_status == 'EXHAUSTED':
                return {'status': 'EXHAUSTED', 'reset_at': account.reset_at, 'error': 'Google provider quota limit reached'}

        return {'status': 'AVAILABLE', 'reset_at': None, 'error': None}

    def _get_client(self, user_profile=None):
        api_key = self._get_api_key(user_profile)
        if not api_key:
            raise ProviderNotConfiguredException("Google API key or connected account is not configured.")
        try:
            from google import genai
            return genai.Client(api_key=api_key)
        except ImportError:
            raise ProviderNotConfiguredException("google-genai SDK package is not installed.")

    def generate_script(self, user_profile, prompt: str, history_topics: List[str] = None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            raise ProviderNotConfiguredException("Google Gemini API is not configured.")
        
        client = self._get_client(user_profile)
        system_instruction = (
            "You are a viral vertical video content creation expert. "
            "Return JSON with keys: title, hook, script, caption, hashtags, topic, duration_seconds."
        )
        full_prompt = f"Create a short video script about: {prompt}."
        if history_topics:
            full_prompt += f" Avoid these recently covered topics: {', '.join(history_topics[:5])}."

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt,
                config={"response_mime_type": "application/json"}
            )
            parsed = json.loads(response.text)
            return parsed
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "QUOTA" in err_str.upper() or "RESOURCE_EXHAUSTED" in err_str.upper():
                self._mark_quota_exhausted(user_profile)
                raise QuotaExceededException(f"Google Gemini quota limit reached: {e}")
            logger.warning(f"Google Gemini script generation error ({e}), falling back to default LLM.")
            raise ProviderException(f"Google Gemini script generation error: {e}")

    def generate_scenes(self, script: str) -> List[Dict[str, str]]:
        lines = [l.strip() for l in script.split('.') if l.strip()]
        if not lines:
            lines = [script[:100]]
        
        scenes = []
        for i, line in enumerate(lines[:5], start=1):
            scenes.append({
                'scene_number': i,
                'prompt': f"Cinematic vertical video scene {i}: {line[:120]}",
                'narration': line
            })
        return scenes

    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        api_key = self._get_api_key()
        if not api_key:
            raise ProviderNotConfiguredException("Google Veo Video generation API is not configured.")

        client = self._get_client()
        from google.genai import types

        out_dir = os.path.dirname(output_path)
        os.makedirs(out_dir, exist_ok=True)

        clip_paths = []
        last_job_id = None

        for idx, scene in enumerate(scenes, start=1):
            scene_prompt = scene.get('prompt', 'Cinematic video scene')
            clip_path = os.path.join(out_dir, f"scene_{idx}.mp4")
            
            logger.info(f"Submitting Google Veo video generation job for Scene #{idx}: '{scene_prompt[:60]}'")
            
            try:
                operation = client.models.generate_videos(
                    model="veo-2.0-generate-001",
                    prompt=scene_prompt,
                    config=types.GenerateVideosConfig(
                        aspect_ratio=aspect_ratio,
                        duration_seconds=5
                    )
                )
                last_job_id = getattr(operation, 'name', str(operation))

                # Poll operation until complete
                poll_count = 0
                max_polls = 60 # 60 * 10s = 600s
                while not operation.done and poll_count < max_polls:
                    time.sleep(10)
                    operation = client.operations.get(operation)
                    poll_count += 1

                if not operation.done:
                    raise ProviderException(f"Google Veo video generation timed out for scene {idx}")

                if getattr(operation, 'error', None):
                    err_msg = str(operation.error)
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "QUOTA" in err_msg.upper():
                        raise QuotaExceededException(f"Google Veo quota exceeded: {err_msg}")
                    raise ProviderException(f"Google Veo generation failed for scene {idx}: {err_msg}")

                response = operation.response
                if not response or not getattr(response, 'generated_videos', None):
                    raise ProviderException(f"Google Veo returned empty video list for scene {idx}")

                gen_video = response.generated_videos[0]
                video_obj = gen_video.video

                if getattr(video_obj, 'video_bytes', None):
                    with open(clip_path, 'wb') as f:
                        f.write(video_obj.video_bytes)
                elif getattr(video_obj, 'uri', None):
                    import urllib.request
                    urllib.request.urlretrieve(video_obj.uri, clip_path)
                else:
                    video_obj.save(clip_path)

                if not os.path.exists(clip_path) or os.path.getsize(clip_path) == 0:
                    raise ProviderException(f"Google Veo saved 0-byte video clip at {clip_path}")

                clip_paths.append(clip_path)
                logger.info(f"Successfully generated Google Veo scene #{idx} clip: {clip_path}")

            except QuotaExceededException:
                raise
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "QUOTA" in err_str.upper():
                    self._mark_quota_exhausted()
                    raise QuotaExceededException(f"Google Veo API quota limit exceeded: {e}")
                raise ProviderException(f"Google Veo API video generation error: {e}")

        # Combine TTS Voiceover Audio
        full_narration = " ".join([s.get('narration', '') for s in scenes]) or "CreatorOS Daily Video"
        audio_path = os.path.join(out_dir, "voiceover.mp3")
        tts = DefaultTTSProvider()
        tts.generate_audio(text=full_narration, output_path=audio_path, language="Russian")

        # Concatenate Multi-Scene Video Clips + Voiceover + Subtitles using FFmpeg
        renderer = FFmpegVideoRenderer()
        renderer.concat_video_clips(
            clip_paths=clip_paths,
            audio_path=audio_path,
            script_text=full_narration,
            output_path=output_path
        )
        return output_path

    def _mark_quota_exhausted(self, user_profile=None):
        if user_profile and hasattr(user_profile, 'user') and hasattr(user_profile.user, 'ai_accounts'):
            account = user_profile.user.ai_accounts.filter(provider='google', status='ACTIVE').first()
            if account:
                account.quota_status = 'EXHAUSTED'
                account.save()
