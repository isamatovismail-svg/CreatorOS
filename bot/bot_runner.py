import logging
from typing import Dict, Any, Optional
from django.utils import timezone
from core.models import UserProfile, ContentPost
from services.pipeline.service import create_and_generate_post

logger = logging.getLogger(__name__)

class CreatorOSBotHandler:
    """
    Handles interactive Telegram Bot requests & command routing.
    Commands: /start [CODE], /help, /profile, /settings, /create, /daily, /today, /history, /status
    """

    def handle_command(self, chat_id: str, command_text: str, user_profile: Optional[UserProfile] = None) -> str:
        parts = command_text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Handle account linking via /start CODE
        if cmd == "/start" and args and len(args) == 6 and args.isalnum():
            linking_code = args.strip().upper()
            try:
                target_profile = UserProfile.objects.get(
                    telegram_linking_code=linking_code,
                    telegram_linking_code_expires_at__gt=timezone.now()
                )
                target_profile.telegram_chat_id = chat_id
                target_profile.telegram_linking_code = None
                target_profile.telegram_linking_code_expires_at = None
                target_profile.save()
                return (
                    f"🎉 <b>Account Linked Successfully!</b>\n\n"
                    f"Welcome, <b>{target_profile.user.username}</b>! Your Telegram account is now synced with CreatorOS.\n"
                    f"All generated 9:16 vertical videos and post packages will be sent directly here.\n\n"
                    f"Try sending <code>/create</code> or <code>/help</code> to get started!"
                )
            except UserProfile.DoesNotExist:
                return (
                    "⚠️ <b>Invalid or Expired Linking Code!</b>\n\n"
                    "Please generate a fresh code in your CreatorOS Web Dashboard (Settings -> Link Telegram)."
                )

        # If user profile is not linked yet
        if not user_profile or not user_profile.telegram_chat_id:
            return (
                "👋 <b>Welcome to CreatorOS Bot!</b>\n\n"
                "Your Telegram account is not linked to a CreatorOS web user yet.\n\n"
                "<b>How to link:</b>\n"
                "1. Log in to your CreatorOS Web Dashboard.\n"
                "2. Go to <b>Settings</b> -> <b>Link Telegram Account</b>.\n"
                "3. Click <b>Generate Code</b> and send <code>/start &lt;CODE&gt;</code> here!"
            )

        user = user_profile.user

        if cmd in ["/start", "/help"]:
            return (
                f"👋 <b>CreatorOS AI Content Assistant</b> (User: <i>{user.username}</i>)\n\n"
                "Available commands:\n"
                "• <code>/create &lt;idea&gt;</code> - Generate video from your idea or topic\n"
                "• <code>/daily</code> - Generate today's automated content video\n"
                "• <code>/today</code> - Check today's generated posts\n"
                "• <code>/history</code> - View recent content history\n"
                "• <code>/profile</code> - View your content preferences\n"
                "• <code>/settings</code> - View account & Telegram status\n"
                "• <code>/status</code> - View current post delivery status"
            )

        elif cmd == "/profile":
            return (
                f"👤 <b>Content Profile Settings for {user.username}:</b>\n\n"
                f"🌐 <b>Language:</b> {user_profile.language}\n"
                f"🎯 <b>Niche:</b> {user_profile.niche}\n"
                f"👥 <b>Target Audience:</b> {user_profile.target_audience}\n"
                f"🎨 <b>Style:</b> {user_profile.style}\n"
                f"⏱️ <b>Duration:</b> {user_profile.duration_seconds}s\n"
                f"⏰ <b>Daily Generation Time:</b> {user_profile.daily_time} ({user_profile.timezone})"
            )

        elif cmd == "/settings":
            link_status = "Linked ✅" if user_profile.telegram_chat_id else "Not Linked ❌"
            byok_status = "Configured (BYOK) 🔑" if user_profile.openai_api_key else "Default Freemium Engine ⚡"
            return (
                f"⚙️ <b>CreatorOS Account Settings:</b>\n\n"
                f"• <b>User:</b> {user.username}\n"
                f"• <b>Telegram Chat ID:</b> {user_profile.telegram_chat_id}\n"
                f"• <b>Link Status:</b> {link_status}\n"
                f"• <b>AI Provider:</b> {byok_status}"
            )

        elif cmd == "/create":
            if not args:
                # Prompt user with choice
                return (
                    "🎬 <b>Create New Short Video:</b>\n\n"
                    "To generate with a specific topic/idea:\n"
                    "👉 <code>/create 5 AI Productivity Tools</code>\n\n"
                    "To let AI select the optimal topic for your niche:\n"
                    "👉 <code>/daily</code>"
                )
            
            post = create_and_generate_post(user, idea=args, mode='user_idea')
            return f"🚀 Post #{post.id} ('<b>{post.title}</b>') rendered and delivered!"

        elif cmd == "/daily":
            post = create_and_generate_post(user, idea=None, mode='auto')
            return f"🌟 Daily video post #{post.id} ('<b>{post.title}</b>') rendered and delivered!"

        elif cmd in ["/today", "/history"]:
            posts = ContentPost.objects.filter(user=user).order_by('-created_at')[:5]
            if not posts.exists():
                return "ℹ️ No recent posts found. Use <code>/create</code> or <code>/daily</code> to generate your first video!"
            
            lines = []
            for p in posts:
                status_icon = "✅" if p.status == 'READY_MANUAL' else ("⏳" if p.status == 'GENERATING' else "❌")
                lines.append(f"• #{p.id} {status_icon} <b>{p.title}</b> ({p.created_at.strftime('%H:%M')})")
            
            return f"📚 <b>Recent Post History:</b>\n\n" + "\n".join(lines)

        elif cmd == "/status":
            posts = ContentPost.objects.filter(user=user).order_by('-created_at')[:5]
            if not posts.exists():
                return "ℹ️ No active posts."
            lines = [f"• #{p.id} {p.title} - Status: <b>{p.get_status_display()}</b> (Telegram: {p.get_telegram_delivery_status_display()})" for p in posts]
            return f"📊 <b>Post Statuses:</b>\n\n" + "\n".join(lines)

        return "❓ Unknown command. Send <code>/help</code> to see available commands."

