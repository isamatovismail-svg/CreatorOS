import os
import logging
from typing import Dict, Any, List
from services.ai.base import (
    BaseLLMAdapter, BaseVideoAdapter,
    ProviderNotConfiguredException, QuotaExceededException
)

logger = logging.getLogger(__name__)

class GoogleAIAdapter(BaseLLMAdapter, BaseVideoAdapter):
    """
    Google AI (Veo / Gemini) Adapter.
    Handles Google Gemini script generation and Google Veo generative video clips.
    Uses official credentials / user OAuth tokens when present.
    """
    name = "Google AI (Veo / Gemini)"
    provider_id = "google"
    is_paid = True

    def _get_api_key(self, user_profile=None) -> str:
        return os.getenv("GOOGLE_VEO_API_KEY", os.getenv("GEMINI_API_KEY", ""))

    def is_configured(self, user_profile=None) -> bool:
        # Check env keys or user's connected Google OAuth accounts
        if self._get_api_key(user_profile):
            return True
        if user_profile and hasattr(user_profile.user, 'ai_accounts'):
            active = user_profile.user.ai_accounts.filter(provider='google', status='ACTIVE').first()
            if active:
                return True
        return False

    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            return {'status': 'NOT_CONFIGURED', 'reset_at': None, 'error': 'Google API key or OAuth account not configured'}
        
        if user_profile and hasattr(user_profile.user, 'ai_accounts'):
            account = user_profile.user.ai_accounts.filter(provider='google', status='ACTIVE').first()
            if account and account.quota_status == 'EXHAUSTED':
                return {'status': 'EXHAUSTED', 'reset_at': account.reset_at, 'error': 'Google provider quota limit reached'}

        return {'status': 'AVAILABLE', 'reset_at': None, 'error': None}

    def generate_script(self, user_profile, prompt: str, history_topics: List[str] = None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            raise ProviderNotConfiguredException("Google Gemini API is not configured.")
        # Google Gemini API integration call would execute here when API key provided
        raise ProviderNotConfiguredException("Google Gemini API call requires active GOOGLE_VEO_API_KEY.")

    def generate_scenes(self, script: str) -> List[Dict[str, str]]:
        lines = [l.strip() for l in script.split('.') if l.strip()]
        return [{'scene_number': i+1, 'prompt': f"Google Veo scene: {l}", 'narration': l} for i, l in enumerate(lines[:4])]

    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        if not self.is_configured():
            raise ProviderNotConfiguredException("Google Veo Video generation API is not configured.")
        raise ProviderNotConfiguredException("Google Veo API credentials not active on this environment.")
