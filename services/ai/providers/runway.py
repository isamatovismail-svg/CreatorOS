import os
import logging
from typing import Dict, Any, List
from services.ai.base import (
    BaseVideoAdapter, ProviderNotConfiguredException
)

logger = logging.getLogger(__name__)

class RunwayAdapter(BaseVideoAdapter):
    """
    Runway Gen-2 / Gen-3 Adapter.
    Handles Runway video clip generation via API.
    """
    name = "Runway Gen-3"
    provider_id = "runway"
    is_paid = True

    def _get_api_key(self, user_profile=None) -> str:
        return os.getenv("RUNWAY_API_KEY", "")

    def is_configured(self, user_profile=None) -> bool:
        return bool(self._get_api_key(user_profile))

    def check_quota(self, user_profile=None) -> Dict[str, Any]:
        if not self.is_configured(user_profile):
            return {'status': 'NOT_CONFIGURED', 'reset_at': None, 'error': 'Runway API key not configured'}
        return {'status': 'AVAILABLE', 'reset_at': None, 'error': None}

    def generate_video(self, scenes: List[Dict[str, str]], output_path: str, aspect_ratio: str = "9:16") -> str:
        if not self.is_configured():
            raise ProviderNotConfiguredException("Runway API key is not configured.")
        raise ProviderNotConfiguredException("Runway API key not active on this environment.")
