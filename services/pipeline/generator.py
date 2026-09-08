import os
import logging
from typing import Dict, Any, Optional
from django.conf import settings
from services.ai_provider.ai_manager import AIProviderManager
from core.models import ContentPost, SystemLog

logger = logging.getLogger(__name__)

class ContentPipelineGenerator:
    """
    End-to-End Content Generation Pipeline.
    Orchestrates LLM script generation, TTS voice generation, visual background image synthesis,
    and automatic caption/hashtag formatting.
    """

    def __init__(self, llm_provider: str = 'default_llm', image_provider: str = 'pollinations', tts_provider: str = 'default_tts'):
        self.llm = AIProviderManager.get_llm(llm_provider)
        self.image_gen = AIProviderManager.get_image(image_provider)
        self.tts = AIProviderManager.get_tts(tts_provider)

    def generate_post_content(
        self,
        post: ContentPost,
        user_api_key: Optional[str] = None
    ) -> ContentPost:
        """
        Executes full generation flow for a ContentPost model instance.
        """
        try:
            post.status = 'GENERATING'
            post.save()

            topic_title = post.topic.title if post.topic else post.title
            target_platform = post.get_target_platform_display()

            # 1. Generate Script & Caption via LLM
            prompt = f"Create an engaging short video script and caption for {target_platform} about: '{topic_title}'."
            raw_text = self.llm.generate_text(
                prompt=prompt,
                api_key=user_api_key,
                topic=topic_title
            )

            post.script = raw_text
            post.caption = f"🔥 {topic_title}\n\nCheck out our latest insights on {topic_title}! What are your thoughts?"
            post.hashtags = f"#{topic_title.replace(' ', '')} #CreatorOS #Shorts #Reels #AI"

            # 2. Output directory setup
            media_dir = os.path.join(settings.BASE_DIR, 'media', 'posts', str(post.id))
            os.makedirs(media_dir, exist_ok=True)

            # 3. Generate Visual Image Background
            image_path = os.path.join(media_dir, 'background.jpg')
            self.image_gen.generate_image(
                prompt=f"Cinematic futuristic aesthetic of {topic_title}, 8k resolution, vertical 9:16",
                output_path=image_path,
                width=1080,
                height=1920
            )
            post.media_file_path = image_path

            # 4. Generate Voiceover TTS Audio
            audio_path = os.path.join(media_dir, 'voiceover.mp3')
            self.tts.generate_audio(
                text=post.script[:200], # First 200 chars for short clip
                output_path=audio_path
            )
            post.audio_file_path = audio_path

            # 5. Set status to READY_MANUAL (ready for Telegram bot delivery / manual upload fallback)
            post.status = 'READY_MANUAL'
            post.save()

            SystemLog.objects.create(
                user=post.user,
                level='INFO',
                module='PipelineGenerator',
                message=f"Successfully generated assets for post ID #{post.id} ({post.title})"
            )

        except Exception as e:
            logger.error(f"Pipeline generation failed for post #{post.id}: {e}")
            post.status = 'FAILED'
            post.error_message = str(e)
            post.save()

            SystemLog.objects.create(
                user=post.user,
                level='ERROR',
                module='PipelineGenerator',
                message=f"Pipeline failed for post ID #{post.id}: {e}"
            )

        return post
