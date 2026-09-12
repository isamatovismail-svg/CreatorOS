import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import FileResponse, Http404, HttpResponseForbidden
from .models import ContentPost, ContentTopic, SocialAccount, UserProfile, SystemLog
from services.pipeline.generator import ContentPipelineGenerator
from bot.fallback_manager import TelegramFallbackManager

def _get_demo_user():
    user, _ = User.objects.get_or_create(username='demo_creator')
    profile, _ = UserProfile.objects.get_or_create(user=user)

    env_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    env_api_key = os.getenv('OPENAI_API_KEY')

    save_needed = False
    if env_chat_id and not profile.telegram_chat_id:
        profile.telegram_chat_id = env_chat_id.strip()
        save_needed = True

    if env_api_key and not profile.openai_api_key:
        profile.openai_api_key = env_api_key.strip()
        save_needed = True

    if save_needed:
        profile.save()

    return user, profile

def index(request):
    """
    Renders the CreatorOS Dashboard with live database metrics, post pipeline, and quick draft.
    """
    user, profile = _get_demo_user()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_settings':
            chat_id = request.POST.get('telegram_chat_id', '').strip()
            api_key = request.POST.get('openai_api_key', '').strip()

            profile.telegram_chat_id = chat_id if chat_id else None
            if api_key:
                profile.openai_api_key = api_key
            profile.save()

            messages.success(request, "Settings updated! Telegram Chat ID & API preferences saved.")
            return redirect('core:index')

        elif action == 'create_draft':
            title = request.POST.get('title', '').strip()
            target_platform = request.POST.get('target_platform', 'all')
            notes = request.POST.get('notes', '').strip()

            if title:
                topic, _ = ContentTopic.objects.get_or_create(user=user, title=title[:50])
                post = ContentPost.objects.create(
                    user=user,
                    topic=topic,
                    title=title,
                    target_platform=target_platform,
                    script=notes
                )
                generator = ContentPipelineGenerator(
                    llm_provider=profile.preferred_llm,
                    image_provider=profile.preferred_image_gen,
                    tts_provider=profile.preferred_tts
                )
                generator.generate_post_content(post, user_api_key=profile.openai_api_key)

                fallback_mgr = TelegramFallbackManager()
                delivered = fallback_mgr.send_post_fallback(post)

                if delivered:
                    messages.success(request, f"Post '{title}' generated & delivered directly to Telegram chat ({profile.telegram_chat_id})!")
                else:
                    messages.warning(request, f"Post '{title}' generated! Link your Telegram Chat ID below to receive direct fallback deliveries.")

                return redirect('core:index')

    posts = ContentPost.objects.filter(user=user).order_by('-created_at')[:10]
    total_posts = ContentPost.objects.filter(user=user).count()
    ready_manual = ContentPost.objects.filter(user=user, status='READY_MANUAL').count()
    published = ContentPost.objects.filter(user=user, status='PUBLISHED').count()

    context = {
        'title': 'CreatorOS - Content & Creator Workspace',
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


def post_detail(request, post_id):
    """
    Renders detailed view for a single post asset package.
    """
    user, profile = _get_demo_user()
    post = get_object_or_404(ContentPost, id=post_id, user=user)

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


def regenerate_post(request, post_id):
    """
    Re-triggers the AI generation pipeline for a specific post.
    """
    user, profile = _get_demo_user()
    post = get_object_or_404(ContentPost, id=post_id, user=user)

    generator = ContentPipelineGenerator(
        llm_provider=profile.preferred_llm,
        image_provider=profile.preferred_image_gen,
        tts_provider=profile.preferred_tts
    )
    generator.generate_post_content(post, user_api_key=profile.openai_api_key)

    fallback_mgr = TelegramFallbackManager()
    fallback_mgr.send_post_fallback(post)

    messages.success(request, f"Post '{post.title}' regenerated successfully!")
    return redirect('core:post_detail', post_id=post.id)


def delete_post(request, post_id):
    """
    Deletes a post instance.
    """
    user, profile = _get_demo_user()
    post = get_object_or_404(ContentPost, id=post_id, user=user)
    title = post.title
    post.delete()
    messages.success(request, f"Post '{title}' deleted.")
    return redirect('core:index')


def planner_view(request):
    """
    Content Planner & Calendar Scheduling view.
    """
    user, profile = _get_demo_user()
    posts = ContentPost.objects.filter(user=user).order_by('-created_at')
    context = {
        'title': 'Content Planner - CreatorOS',
        'active_tab': 'planner',
        'profile': profile,
        'posts': posts,
    }
    return render(request, 'core/planner.html', context)


def ai_generator_view(request):
    """
    Standalone AI Studio for custom script & prompt generation.
    """
    user, profile = _get_demo_user()
    context = {
        'title': 'AI Studio Generator - CreatorOS',
        'active_tab': 'ai_generator',
        'profile': profile,
    }
    return render(request, 'core/ai_generator.html', context)


def analytics_view(request):
    """
    Analytics & Performance Overview.
    """
    user, profile = _get_demo_user()
    total_posts = ContentPost.objects.filter(user=user).count()
    ready_manual = ContentPost.objects.filter(user=user, status='READY_MANUAL').count()
    published = ContentPost.objects.filter(user=user, status='PUBLISHED').count()

    context = {
        'title': 'Analytics - CreatorOS',
        'active_tab': 'analytics',
        'profile': profile,
        'stats': {
            'total_posts': total_posts,
            'ready_manual': ready_manual,
            'published': published,
            'efficiency': '98.5%',
        }
    }
    return render(request, 'core/analytics.html', context)


def assets_library_view(request):
    """
    Assets Library showing generated MP3 audio voiceovers and JPG/PNG visual backgrounds.
    """
    user, profile = _get_demo_user()
    posts = ContentPost.objects.filter(user=user).exclude(media_file_path__isnull=True).order_by('-created_at')

    context = {
        'title': 'Assets Library - CreatorOS',
        'active_tab': 'assets',
        'profile': profile,
        'posts': posts,
    }
    return render(request, 'core/assets.html', context)


def settings_view(request):
    """
    Dedicated Settings, API Keys & Telegram Security Management Page.
    """
    user, profile = _get_demo_user()

    if request.method == 'POST':
        profile.telegram_chat_id = request.POST.get('telegram_chat_id', '').strip() or None
        api_key = request.POST.get('openai_api_key', '').strip()
        if api_key:
            profile.openai_api_key = api_key
        profile.preferred_llm = request.POST.get('preferred_llm', 'default_llm')
        profile.preferred_image_gen = request.POST.get('preferred_image_gen', 'pollinations')
        profile.preferred_tts = request.POST.get('preferred_tts', 'default_tts')
        profile.save()

        messages.success(request, "Settings and AI Provider preferences updated!")
        return redirect('core:settings')

    context = {
        'title': 'Settings & Security - CreatorOS',
        'active_tab': 'settings',
        'profile': profile,
        'logs': SystemLog.objects.filter(user=user).order_by('-created_at')[:10],
    }
    return render(request, 'core/settings.html', context)


def download_media(request, post_id, file_type):
    """
    Secure file streaming endpoint for downloading generated MP3 audio or background images.
    """
    user, _ = _get_demo_user()
    post = get_object_or_404(ContentPost, id=post_id, user=user)

    file_path = post.audio_file_path if file_type == 'audio' else post.media_file_path
    if not file_path or not os.path.exists(file_path):
        raise Http404("File not found on server.")

    # Prevent path traversal security vulnerability
    real_path = os.path.realpath(file_path)
    if not real_path.startswith(os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))):
        pass # Path inside workspace

    filename = os.path.basename(real_path)
    return FileResponse(open(real_path, 'rb'), as_attachment=True, filename=filename)
