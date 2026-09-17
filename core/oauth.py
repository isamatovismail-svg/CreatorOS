import os
import urllib.parse
import requests
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_google_oauth_config() -> Dict[str, str]:
    """Returns Google OAuth credentials from environment variables."""
    return {
        'client_id': os.getenv('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET', ''),
        'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI', 'http://127.0.0.1:8000/auth/google/callback/'),
    }

def is_google_oauth_configured() -> bool:
    """Checks whether Google OAuth client ID and secret are configured in environment."""
    config = get_google_oauth_config()
    return bool(config['client_id'] and config['client_secret'])

def get_google_auth_url(state: str, prompt_select: bool = False) -> str:
    """Generates secure Google OAuth authorization URL."""
    config = get_google_oauth_config()
    params = {
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline',
        'state': state,
    }
    if prompt_select:
        params['prompt'] = 'select_account'
    
    return f"{GOOGLE_AUTH_ENDPOINT}?{urllib.parse.urlencode(params)}"

def exchange_code_for_tokens(code: str) -> Optional[Dict[str, Any]]:
    """Exchanges authorization code for Google access and refresh tokens."""
    config = get_google_oauth_config()
    data = {
        'code': code,
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'redirect_uri': config['redirect_uri'],
        'grant_type': 'authorization_code',
    }
    try:
        response = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Google token exchange failed: HTTP {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Google token exchange exception: {e}")
        return None

def get_google_user_info(access_token: str) -> Optional[Dict[str, Any]]:
    """Fetches user profile information from Google userinfo endpoint using access_token."""
    headers = {'Authorization': f'Bearer {access_token}'}
    try:
        response = requests.get(GOOGLE_USERINFO_ENDPOINT, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        logger.error(f"Google userinfo request failed: HTTP {response.status_code}")
        return None
    except Exception as e:
        logger.error(f"Google userinfo exception: {e}")
        return None
