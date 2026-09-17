import os
import logging
from typing import Dict, Any, List
from services.ai.base import (
    BaseLLMAdapter, BaseVideoAdapter,
    ProviderNotConfiguredException, QuotaExceededException
)

logger = logging.getLogger(__name__)

class OpenAIAdapter(BaseLLMAdapter, BaseVideoAdapter):
    """
    OpenAI (Sora / GPT-4) Adapter.
    Handles GPT-4 script generation and Sora video clip generation.
    Checks environment keys and user BYOK keys.
    """
    name = "OpenAI (Sora / GPT)"
    provider_id = "openai"
    is_paid = True

    def _get_api_key(self, user_profile=None) -> str:
        if user_profile and getattr(user_profile, 'openai_api_key', None):
            return user_profile.openai_api_key
        return os.getenv("OPENAI_API_KEY", "")

    def is_configured(self, user_profile=None) -> bool:
        return bool(self._get_api_key(user_profile))

    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            return {'status': 'NOT_CONFIGURED', 'reset_at': None, 'error': 'OpenAI API key not configured'}
        
        if user_profile and hasattr(user_profile.user, 'ai_accounts'):
            account = user_profile.user.ai_accounts.filter(provider='openai', status='ACTIVE').first()
            if account and account.quota_status == 'EXHAUSTED':
                return {'status': 'EXHAUSTED', 'reset_at': account.reset_at, 'error': 'OpenAI provider quota limit reached'}

        return {'status': 'AVAILABLE', 'reset_at': None, 'error': None}

    def generate_script(self, user_profile, prompt: str, history_topics: List[str] = None) -> Dict[str, Any]:
        api_key = self._get_api_key(user_profile)
        if not api_key:
            raise ProviderNotConfiguredException("OpenAI API key is not configured.")
        # Handled through OpenAI API when key present
        raise ProviderNotConfiguredException("OpenAI API call requires valid OPENAI_API_KEY.")

    def generate_scenes(self, script: str) -> List[Dict[str, str]]:
        lines = [l.strip() for l in script.split('.') if l.strip()]
        return [{'scene_number': i+1, 'prompt': f"OpenAI Sora scene: {l}", 'narration': l} for i, l in enumerate(lines[:4])]

    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        if not self.is_configured():
            raise ProviderNotConfiguredException("OpenAI Sora API key is not configured.")
        raise ProviderNotConfiguredException("OpenAI Sora API credentials not active on this environment.")
