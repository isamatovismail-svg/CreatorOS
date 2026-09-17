import os
import random
import string
import logging
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from .models import ContentPost, ContentTopic, SocialAccount, UserProfile, SystemLog
from services.pipeline.service import create_and_generate_post

logger = logging.getLogger(__name__)

def register_view(request):
    """
    Registers a new user account and creates an associated UserProfile.
    """
    if request.user.is_authenticated:
        return redirect('core:index')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, f"Welcome to CreatorOS, {user.username}! Your workspace is ready.")
            return redirect('core:index')
    else:
        form = UserCreationForm()

    return render(request, 'registration/register.html', {'form': form})


@login_required
def index(request):
    """
    Renders the CreatorOS Dashboard with live user database metrics and post creation.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_draft':
            title = request.POST.get('title', '').strip()
            target_platform = request.POST.get('target_platform', 'all')

            if title:
                post = create_and_generate_post(
                    user=request.user,
                    idea=title,
                    mode='user_idea',
                    target_platform=target_platform
                )

                if post.telegram_delivery_status == 'SENT':
                    messages.success(request, f"Post '{post.title}' generated and delivered to Telegram!")
                else:
                    messages.success(request, f"Post '{post.title}' generated! Check your video in History or Telegram.")

                return redirect('core:index')

    posts = ContentPost.objects.filter(user=request.user).order_by('-created_at')[:10]
    total_posts = ContentPost.objects.filter(user=request.user).count()
    ready_manual = ContentPost.objects.filter(user=request.user, status='READY_MANUAL').count()
    published = ContentPost.objects.filter(user=request.user, status='PUBLISHED').count()

    context = {
        'title': 'CreatorOS - Content Workspace',
        'active_tab': 'dashboard',
        'profile': profile,
        'posts': posts,
        'stats': {
            'total_posts': total_posts,
            'ready_manual': ready_manual,
            'published': published,
            'scheduled': ready_manual + published,
        }
    }
    return render(request, 'core/index.html', context)


@login_required
def post_detail(request, post_id):
    """
    Renders detailed view for a single post asset package.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    post = get_object_or_404(ContentPost, id=post_id, user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_edits':
            post.script = request.POST.get('script', post.script)
            post.caption = request.POST.get('caption', post.caption)
            post.hashtags = request.POST.get('hashtags', post.hashtags)
            post.save()
            messages.success(request, "Post content updated successfully!")
            return redirect('core:post_detail', post_id=post.id)

    context = {
        'title': f"{post.title} - CreatorOS",
        'post': post,
        'profile': profile,
    }
    return render(request, 'core/post_detail.html', context)


@login_required
def regenerate_post(request, post_id):
    """
    Re-triggers the AI generation pipeline for a specific post.
    """
    post = get_object_or_404(ContentPost, id=post_id, user=request.user)

    post = create_and_generate_post(
        user=request.user,
        idea=post.idea or post.title,
        mode='user_idea',
        target_platform=post.target_platform
    )

    messages.success(request, f"Post '{post.title}' regenerated successfully!")
    return redirect('core:post_detail', post_id=post.id)


@login_required
def delete_post(request, post_id):
    """
    Deletes a post instance safely.
    """
    if request.method == 'POST' or True: # Allow form submit
        post = get_object_or_404(ContentPost, id=post_id, user=request.user)
        title = post.title
        post.delete()
        messages.success(request, f"Post '{title}' deleted.")
    return redirect('core:index')


@login_required
def planner_view(request):
    """
    Content Planner & History view.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    posts = ContentPost.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'title': 'Content Planner - CreatorOS',
        'active_tab': 'planner',
        'profile': profile,
        'posts': posts,
    }
    return render(request, 'core/planner.html', context)


@login_required
def ai_generator_view(request):
    """
    Standalone AI Studio for custom script & prompt generation.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        prompt = request.POST.get('prompt', '').strip()
        if prompt:
            post = create_and_generate_post(request.user, idea=prompt, mode='user_idea')
            messages.success(request, f"AI Post '{post.title}' generated successfully!")
            return redirect('core:post_detail', post_id=post.id)

    context = {
        'title': 'AI Studio Generator - CreatorOS',
        'active_tab': 'ai_generator',
        'profile': profile,
    }
    return render(request, 'core/ai_generator.html', context)


@login_required
def analytics_view(request):
    """
    Analytics & Performance Overview.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    total_posts = ContentPost.objects.filter(user=request.user).count()
    ready_manual = ContentPost.objects.filter(user=request.user, status='READY_MANUAL').count()
    published = ContentPost.objects.filter(user=request.user, status='PUBLISHED').count()

    context = {
        'title': 'Analytics - CreatorOS',
        'active_tab': 'analytics',
        'profile': profile,
        'stats': {
            'total_posts': total_posts,
            'ready_manual': ready_manual,
            'published': published,
            'efficiency': '100%',
        }
    }
    return render(request, 'core/analytics.html', context)


@login_required
def assets_library_view(request):
    """
    Assets Library showing generated vertical MP4 videos, MP3 audio, and images.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    posts = ContentPost.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'title': 'Assets Library - CreatorOS',
        'active_tab': 'assets',
        'profile': profile,
        'posts': posts,
    }
    return render(request, 'core/assets.html', context)


@login_required
def settings_view(request):
    """
    Dedicated Settings, Preferences, BYOK Keys & Telegram Linking Page.
    """
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'generate_code':
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            profile.telegram_linking_code = code
            profile.telegram_linking_code_expires_at = timezone.now() + timezone.timedelta(minutes=15)
            profile.save()
            messages.success(request, f"Linking Code Generated: {code} (Valid for 15 minutes)")
            return redirect('core:settings')

        elif action == 'save_preferences':
            profile.language = request.POST.get('language', profile.language)
            profile.niche = request.POST.get('niche', profile.niche)
            profile.target_audience = request.POST.get('target_audience', profile.target_audience)
            profile.style = request.POST.get('style', profile.style)
            
            try:
                profile.duration_seconds = int(request.POST.get('duration_seconds', profile.duration_seconds))
            except ValueError:
                pass

            profile.daily_enabled = request.POST.get('daily_enabled') == 'on'
            profile.daily_time = request.POST.get('daily_time', profile.daily_time)
            profile.timezone = request.POST.get('timezone', profile.timezone)
            profile.allow_paid_generation = request.POST.get('allow_paid_generation') == 'on'
            profile.preferred_providers = request.POST.get('preferred_providers', profile.preferred_providers).strip()

            api_key = request.POST.get('openai_api_key', '').strip()
            if api_key:
                profile.openai_api_key = api_key

            profile.save()
            messages.success(request, "Content preferences and settings updated successfully!")
            return redirect('core:settings')

    from .models import AIProviderAccount
    from services.ai.router import AIProviderRouter

    connected_accounts = AIProviderAccount.objects.filter(user=request.user)
    router = AIProviderRouter(user_profile=profile)
    providers_status = router.get_all_providers_status()

    context = {
        'title': 'Settings & Preferences - CreatorOS',
        'active_tab': 'settings',
        'profile': profile,
        'connected_accounts': connected_accounts,
        'providers_status': providers_status,
        'logs': SystemLog.objects.filter(user=request.user).order_by('-created_at')[:10],
    }
    return render(request, 'core/settings.html', context)


# ==============================================================================
# GOOGLE OAUTH & CONNECTED ACCOUNTS VIEWS
# ==============================================================================

import secrets
from .oauth import (
    get_google_auth_url,
    exchange_code_for_tokens,
    get_google_user_info,
    is_google_oauth_configured
)

def google_login(request):
    """
    Initiates Google OAuth 2.0 flow for login or adding a connected Google account.
    Never requests or stores Google passwords.
    """
    state = secrets.token_urlsafe(16)
    request.session['oauth_state'] = state
    
    if request.user.is_authenticated and request.GET.get('action') == 'connect':
        request.session['oauth_action'] = 'connect'
    else:
        request.session['oauth_action'] = 'login'

    if not is_google_oauth_configured():
        messages.error(
            request, 
            "Google OAuth is not configured on this server. "
            "Please configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env."
        )
        return redirect('core:settings' if request.user.is_authenticated else 'login')

    auth_url = get_google_auth_url(state, prompt_select=True)
    return redirect(auth_url)


def google_callback(request):
    """
    Handles Google OAuth 2.0 callback, verifies CSRF state, exchanges tokens,
    creates/logs in user or links connected Google account.
    """
    stored_state = request.session.get('oauth_state')
    received_state = request.GET.get('state')
    code = request.GET.get('code')
    oauth_action = request.session.get('oauth_action', 'login')

    if not stored_state or stored_state != received_state:
        messages.error(request, "Authentication failed: Invalid OAuth state parameter.")
        return redirect('login')

    if not code:
        messages.error(request, "Authentication canceled or authorization code missing.")
        return redirect('login')

    tokens = exchange_code_for_tokens(code)
    if not tokens or 'access_token' not in tokens:
        messages.error(request, "Failed to obtain access tokens from Google.")
        return redirect('login')

    user_info = get_google_user_info(tokens['access_token'])
    if not user_info or 'email' not in user_info:
        messages.error(request, "Failed to retrieve user profile information from Google.")
        return redirect('login')

    email = user_info['email']
    google_sub = user_info.get('sub', email)

    if oauth_action == 'connect' and request.user.is_authenticated:
        # Link additional Google Account under user's profile
        from .models import AIProviderAccount
        account, created = AIProviderAccount.objects.get_or_create(
            user=request.user,
            provider='google',
            external_account_id=email,
            defaults={
                'status': 'ACTIVE',
                'quota_status': 'AVAILABLE',
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
            }
        )
        if not created:
            account.access_token = tokens.get('access_token')
            if tokens.get('refresh_token'):
                account.refresh_token = tokens.get('refresh_token')
            account.status = 'ACTIVE'
            account.save()

        messages.success(request, f"Successfully connected Google Account: {email}")
        return redirect('core:settings')

    else:
        # User Authentication (Login or Auto-Registration via Google OAuth)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create user with unguessable random password; user authenticates via OAuth
            random_password = User.objects.make_random_password()
            user = User.objects.create_user(
                username=username,
                email=email,
                password=random_password
            )
            UserProfile.objects.create(user=user)

        from .models import AIProviderAccount
        AIProviderAccount.objects.update_or_create(
            user=user,
            provider='google',
            external_account_id=email,
            defaults={
                'status': 'ACTIVE',
                'quota_status': 'AVAILABLE',
                'access_token': tokens.get('access_token'),
                'refresh_token': tokens.get('refresh_token'),
            }
        )

        login(request, user)
        messages.success(request, f"Welcome back, {user.username}! Signed in via Google.")
        return redirect('core:index')


@login_required
def disconnect_account(request, account_id):
    """
    POST endpoint to safely remove/disconnect a connected AI provider account.
    Enforces strict user ownership verification.
    """
    if request.method == 'POST':
        from .models import AIProviderAccount
        account = get_object_or_404(AIProviderAccount, id=account_id, user=request.user)
        email = account.external_account_id or account.get_provider_display()
        account.delete()
        messages.success(request, f"Disconnected account '{email}'.")
    return redirect('core:settings')


@login_required
def download_media(request, post_id, file_type):
    """
    Secure file streaming endpoint for downloading generated MP4 videos, MP3 audio, or background images.
    Strictly protects against path traversal vulnerabilities.
    """
    post = get_object_or_404(ContentPost, id=post_id, user=request.user)

    if file_type == 'video':
        file_path = post.video_file_path or post.media_file_path
    elif file_type == 'audio':
        file_path = post.audio_file_path
    else:
        file_path = post.media_file_path

    if not file_path or not os.path.exists(file_path):
        raise Http404("Requested media asset file not found on server.")

    # Strict path traversal validation
    real_file_path = os.path.realpath(file_path)
    base_media_dir = os.path.realpath(os.path.join(settings.BASE_DIR, 'media'))

    if not real_file_path.startswith(base_media_dir):
        return HttpResponseForbidden("Access Denied: Path traversal detected.")

    filename = os.path.basename(real_file_path)
    content_type = 'video/mp4' if file_type == 'video' else ('audio/mpeg' if file_type == 'audio' else 'image/jpeg')

    return FileResponse(
        open(real_file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type
    )

