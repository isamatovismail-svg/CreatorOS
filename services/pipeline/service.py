import os
import logging
import time
from typing import Optional, Any
from django.conf import settings
from django.utils import timezone
from core.models import ContentPost, SystemLog, AIUsage
from services.ai.router import AIProviderRouter
from services.ai.base import QuotaExceededException
from services.video.validator import validate_video_file, VideoValidationError
from bot.fallback_manager import TelegramFallbackManager

logger = logging.getLogger(__name__)

def create_and_generate_post(
    user: Any,
    idea: Optional[str] = None,
    mode: str = 'user_idea',
    target_platform: str = 'all'
) -> ContentPost:
    """
    Unified Service Layer entry point for post creation and video pipeline execution.
    Shared identically by Web Dashboard, Scheduler, and Telegram Bot.
    """
    user_profile = getattr(user, 'profile', None)
    router = AIProviderRouter(user_profile=user_profile)

    # 1. Check daily video limit & idempotency if auto-scheduler
    if mode == 'daily_scheduler':
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        existing_today = ContentPost.objects.filter(
            user=user,
            created_at__gte=today_start,
            status__in=['READY_MANUAL', 'PUBLISHED']
        ).exists()
        if existing_today:
            logger.info(f"Daily generation skipped for {user.username}: already generated today.")
            return ContentPost.objects.filter(
                user=user,
                created_at__gte=today_start,
                status__in=['READY_MANUAL', 'PUBLISHED']
            ).first()

    # 2. Gather topic history for freshness
    history_topics = list(
        ContentPost.objects.filter(user=user)
        .exclude(topic__isnull=True)
        .values_list('topic__title', flat=True)[:10]
    )

    # 3. Select AI Provider via Router
    llm_provider = router.select_llm_provider()
    video_provider = router.select_video_provider()

    # 4. Generate structured content
    try:
        structured = llm_provider.generate_script(
            user_profile=user_profile,
            prompt=idea if mode == 'user_idea' else (idea or "Latest trends in AI technology"),
            history_topics=history_topics
        )
    except Exception as e:
        logger.warning(f"Primary LLM generation failed ({e}), using default fallback.")
        from services.ai_provider.adapters.default_llm import DefaultLLMProvider
        fallback_llm = DefaultLLMProvider()

        structured = fallback_llm.generate_structured_content(
            user_profile=user_profile,
            user_idea=idea if mode == 'user_idea' else None,
            history_topics=history_topics
        )

    # 5. Create ContentPost in DB
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
    start_time = time.time()

    try:
        # 6. Scene breakdown for video generation
        scenes = video_provider.generate_scenes(post.script)

        # 7. Render Video using selected Video Provider
        video_path = os.path.join(media_dir, 'video.mp4')
        video_provider.generate_video(
            scenes=scenes,
            output_path=video_path,
            aspect_ratio="9:16"
        )

        # 8. Real MP4 Video Validation
        validation_info = validate_video_file(video_path)

        post.video_file_path = video_path
        post.media_file_path = video_path
        post.audio_file_path = os.path.join(media_dir, 'voiceover.mp3')
        post.status = 'READY_MANUAL'
        post.completed_at = timezone.now()
        post.save()

        # Track Usage
        AIUsage.objects.create(
            user=user,
            provider=video_provider.provider_id,
            request_type='VIDEO',
            status='SUCCESS',
            duration_seconds=round(time.time() - start_time, 2)
        )

        SystemLog.objects.create(
            user=user,
            level='INFO',
            module='ContentService',
            message=f"Post #{post.id} ('{post.title}') rendered & validated successfully via {video_provider.name}."
        )

        # 9. Deliver to Telegram
        if user_profile and user_profile.telegram_chat_id:
            fallback_mgr = TelegramFallbackManager()
            fallback_mgr.send_post_fallback(post)

    except QuotaExceededException as qe:
        logger.warning(f"Quota exceeded during post #{post.id} generation: {qe}")
        post.status = 'WAITING_FOR_QUOTA'
        post.error_message = str(qe)
        post.save()

        AIUsage.objects.create(
            user=user,
            provider=video_provider.provider_id,
            request_type='VIDEO',
            status='WAITING_FOR_QUOTA',
            error_message=str(qe)
        )

    except (VideoValidationError, Exception) as e:
        logger.error(f"Pipeline error for post #{post.id}: {e}")
        post.status = 'FAILED'
        post.error_message = str(e)
        post.save()

        AIUsage.objects.create(
            user=user,
            provider=video_provider.provider_id,
            request_type='VIDEO',
            status='FAILED',
            error_message=str(e)
        )

        SystemLog.objects.create(
            user=user,
            level='ERROR',
            module='ContentService',
            message=f"Post #{post.id} generation failed: {e}"
        )

    return post

