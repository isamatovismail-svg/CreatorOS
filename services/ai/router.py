import logging
from typing import Dict, Any, List, Optional
from services.ai.registry import ProviderRegistry
from services.ai.base import BaseAIProvider, ProviderNotConfiguredException, QuotaExceededException

logger = logging.getLogger(__name__)

class AIProviderRouter:
    """
    Intelligent AI Provider Selection Router for CreatorOS.
    Implements Free-First routing logic, user preferences, quota checks, and fault tolerance.
    """

    def __init__(self, user_profile=None):
        self.user_profile = user_profile
        self.allow_paid = getattr(user_profile, 'allow_paid_generation', False) if user_profile else False
        
        pref_str = getattr(user_profile, 'preferred_providers', 'local,google,openai') if user_profile else 'local,google,openai'
        self.preferred_order = [p.strip() for p in pref_str.split(',') if p.strip()]
        if 'local' not in self.preferred_order:
            self.preferred_order.append('local')

    def get_all_providers_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Gathers real-time configuration & quota status for all registered providers.
        Used by Settings & Dashboard UI. Never exposes raw API keys!
        """
        all_providers = ProviderRegistry.list_all()
        status_dict = {}

        for provider_id, provider in all_providers.items():
            configured = provider.is_configured(self.user_profile)
            quota_info = provider.check_quota(self.user_profile)
            
            status_dict[provider_id] = {
                'name': provider.name,
                'provider_id': provider_id,
                'type': getattr(provider, 'type', 'AI Engine'),
                'is_paid': getattr(provider, 'is_paid', False),
                'configured': configured,
                'status': quota_info.get('status', 'NOT_CONFIGURED'),
                'reset_at': quota_info.get('reset_at'),
                'error': quota_info.get('error'),
            }

        return status_dict

    def select_video_provider(self) -> BaseAIProvider:
        """
        Selects the optimal Video Provider based on Free-First rules, quota, and configuration.
        Precedence:
        1. User-authorized available video provider (if paid allowed or free)
        2. Configured free/local provider
        3. Local fallback engine (always available)
        """
        all_providers = ProviderRegistry.list_all()

        for provider_id in self.preferred_order:
            provider = all_providers.get(provider_id)
            if not provider or provider_id == 'local':
                continue

            if provider.is_paid and not self.allow_paid:
                logger.info(f"Skipping paid provider '{provider.name}' (allow_paid_generation=False)")
                continue

            if not provider.is_configured(self.user_profile):
                logger.info(f"Skipping provider '{provider.name}' (Not configured)")
                continue

            quota_info = provider.check_quota(self.user_profile)
            if quota_info.get('status') == 'AVAILABLE':
                logger.info(f"Selected active video provider: {provider.name}")
                return provider

        # Default fallback to Local Engine
        local_provider = all_providers.get('local')
        logger.info(f"Using Local Fallback Engine for video generation.")
        return local_provider

    def select_llm_provider(self) -> BaseAIProvider:

        """
        Selects LLM provider for script generation.
        """
        all_providers = ProviderRegistry.list_all()

        for provider_id in self.preferred_order:
            provider = all_providers.get(provider_id)
            if not provider or provider_id == 'local':
                continue

            if provider.is_paid and not self.allow_paid:
                continue

            if provider.is_configured(self.user_profile):
                quota_info = provider.check_quota(self.user_profile)
                if quota_info.get('status') == 'AVAILABLE':
                    return provider

        return all_providers.get('local')
