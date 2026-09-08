import logging
from typing import Dict, Any
from core.models import UserProfile, ContentTopic, ContentPost
from services.pipeline.generator import ContentPipelineGenerator
from bot.fallback_manager import TelegramFallbackManager

logger = logging.getLogger(__name__)

class CreatorOSBotHandler:
    """
    Handles interactive Telegram Bot requests & command routing.
    Commands: /start, /generate, /topics, /status
    """

    def handle_command(self, chat_id: str, command_text: str, user_profile: UserProfile) -> str:
        parts = command_text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/start":
            user_profile.telegram_chat_id = chat_id
            user_profile.save()
            return (
                "👋 Welcome to <b>CreatorOS Bot</b>!\n\n"
                "Your Telegram account has been linked successfully.\n"
                "Available commands:\n"
                "• <code>/generate &lt;topic&gt;</code> - Trigger AI video & content generation\n"
                "• <code>/topics</code> - View your active content topics\n"
                "• <code>/status</code> - Check pipeline & post statuses"
            )

        elif cmd == "/generate":
            if not args:
                return "⚠️ Please specify a topic or prompt! Example: <code>/generate AI Productivity Hacks</code>"

            # Create post
            topic, _ = ContentTopic.objects.get_or_create(user=user_profile.user, title=args[:50])
            post = ContentPost.objects.create(
                user=user_profile.user,
                topic=topic,
                title=f"Content: {args}",
                target_platform='all'
            )

            # Trigger pipeline generator
            generator = ContentPipelineGenerator(
                llm_provider=user_profile.preferred_llm,
                image_provider=user_profile.preferred_image_gen,
                tts_provider=user_profile.preferred_tts
            )
            generator.generate_post_content(post, user_api_key=user_profile.openai_api_key)

            # Send Telegram fallback delivery package
            fallback_mgr = TelegramFallbackManager()
            fallback_mgr.send_post_fallback(post)

            return f"🚀 Post generation completed for '<b>{args}</b>'! Check your Telegram package above."

        elif cmd == "/topics":
            topics = ContentTopic.objects.filter(user=user_profile.user)
            if not topics.exists():
                return "📌 No topics found. Create topics in Web Dashboard or generate with <code>/generate &lt;topic&gt;</code>!"
            topic_list = "\n".join([f"• {t.title} ({t.tone})" for t in topics])
            return f"📚 <b>Your Active Content Topics:</b>\n\n{topic_list}"

        elif cmd == "/status":
            posts = ContentPost.objects.filter(user=user_profile.user).order_by('-created_at')[:5]
            if not posts.exists():
                return "ℹ️ No recent posts found."
            post_status_lines = "\n".join([f"• #{p.id} {p.title} - <b>{p.get_status_display()}</b>" for p in posts])
            return f"📊 <b>Recent Post Statuses:</b>\n\n{post_status_lines}"

        return "❓ Unknown command. Use /start to see available options."
