import os
import logging
from typing import Optional, Any
from django.conf import settings
from django.utils import timezone
from core.models import ContentPost, SystemLog
from services.ai_provider.ai_manager import AIProviderManager
from services.video.ffmpeg_renderer import FFmpegVideoRenderer
from bot.fallback_manager import TelegramFallbackManager

logger = logging.getLogger(__name__)

def create_and_generate_post(
    user: Any,
    idea: Optional[str] = None,
    mode: str = 'user_idea',
    target_platform: str = 'all'
) -> ContentPost:
    """
    Unified entry point for post creation and generation.
    Shared identically by Web Dashboard and Telegram Bot.
    """
    user_profile = getattr(user, 'profile', None)
    
    # 1. Gather history topics for duplicate prevention
    history_topics = list(
        ContentPost.objects.filter(user=user)
        .exclude(topic__isnull=True)
        .values_list('topic__title', flat=True)[:10]
    )

    # 2. Get LLM Provider & BYOK key
    llm_provider, api_key = AIProviderManager.resolve_llm_for_user(user_profile)
    
    # 3. Generate structured content
    structured = llm_provider.generate_structured_content(
        user_profile=user_profile,
        user_idea=idea if mode == 'user_idea' else None,
        history_topics=history_topics,
        api_key=api_key
    )

    # 4. Create ContentPost in DB
    post = ContentPost.objects.create(
        user=user,
        title=structured.get("title", f"Video: {structured.get('topic', 'Daily Insight')}"),
        idea=structured.get("idea", idea or ""),
        hook=structured.get("hook", ""),
        script=structured.get("script", ""),
        caption=structured.get("caption", ""),
        hashtags=structured.get("hashtags", ""),
        promotion_tips=structured.get("promotion_tips", ""),
        recommended_publish_time=structured.get("recommended_publish_time", "18:00"),
        target_audience=structured.get("target_audience", "General"),
        language=structured.get("language", "Russian"),
        duration_seconds=structured.get("duration_seconds", 45),
        ai_prompt_used=structured.get("ai_prompt_used", ""),
        target_platform=target_platform,
        status='GENERATING'
    )

    media_dir = os.path.join(settings.BASE_DIR, 'media', 'posts', str(post.id))
    os.makedirs(media_dir, exist_ok=True)

    try:
        # 5. Visual background image generation
        image_gen = AIProviderManager.get_image(
            getattr(user_profile, 'preferred_image_gen', 'pollinations')
        )
        image_path = os.path.join(media_dir, 'background.jpg')
        image_prompt = f"Cinematic vertical 9:16 background visual for {structured.get('topic')}, high quality, 8k"
        image_gen.generate_image(
            prompt=image_prompt,
            output_path=image_path,
            width=1080,
            height=1920
        )
        post.media_file_path = image_path

        # 6. Audio TTS voiceover generation
        tts_gen = AIProviderManager.get_tts(
            getattr(user_profile, 'preferred_tts', 'default_tts')
        )
        audio_path = os.path.join(media_dir, 'voiceover.mp3')
        tts_text = f"{post.hook} {post.script}"
        tts_gen.generate_audio(
            text=tts_text,
            output_path=audio_path,
            language=post.language
        )
        post.audio_file_path = audio_path

        # 7. Render Real FFmpeg MP4 Video with Subtitles
        video_renderer = FFmpegVideoRenderer()
        video_path = os.path.join(media_dir, 'video.mp4')
        video_renderer.render_video(
            image_path=image_path,
            audio_path=audio_path,
            script_text=post.script,
            output_path=video_path,
            duration_seconds=post.duration_seconds
        )
        
        post.video_file_path = video_path
        post.media_file_path = video_path
        post.status = 'READY_MANUAL'
        post.completed_at = timezone.now()
        post.save()

        SystemLog.objects.create(
            user=user,
            level='INFO',
            module='ContentService',
            message=f"Post #{post.id} successfully rendered MP4 video."
        )

        # 8. Telegram delivery
        if user_profile and user_profile.telegram_chat_id:
            fallback_mgr = TelegramFallbackManager()
            fallback_mgr.send_post_fallback(post)

    except Exception as e:
        logger.error(f"Post creation pipeline error for post #{post.id}: {e}")
        post.status = 'FAILED'
        post.error_message = str(e)
        post.save()

        SystemLog.objects.create(
            user=user,
            level='ERROR',
            module='ContentService',
            message=f"Post #{post.id} generation failed: {e}"
        )

    return post
