import os
import sys
import time
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import UserProfile, SystemLog
from bot.bot_runner import CreatorOSBotHandler

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Runs the CreatorOS Telegram Bot service listener and command processor.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run bot check once for testing and exit.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🤖 Starting CreatorOS Telegram Bot Worker..."))

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            self.stdout.write(self.style.WARNING("⚠️ TELEGRAM_BOT_TOKEN env variable not set. Running in Mock/Simulated Bot mode."))

        # Fetch or create demo profile for worker context
        user, _ = User.objects.get_or_create(username='demo_creator')
        profile, _ = UserProfile.objects.get_or_create(user=user)

        handler = CreatorOSBotHandler()

        # Simulated test run
        if options['once']:
            self.stdout.write(self.style.SUCCESS("Processing test bot command '/start'..."))
            response = handler.handle_command(
                chat_id=profile.telegram_chat_id or "123456789",
                command_text="/start",
                user_profile=profile
            )
            self.stdout.write(f"Bot Output:\n{response}")
            SystemLog.log_event("run_bot", "Ran single test bot pass successfully.")
            return

        self.stdout.write(self.style.SUCCESS("✓ Bot service worker is active. Listening for updates... Press Ctrl+C to stop."))

        try:
            if bot_token:
                import urllib.request
                import json

                offset = 0
                while True:
                    url = f"https://api.telegram.org/bot{bot_token}/getUpdates?offset={offset}&timeout=10"
                    try:
                        req = urllib.request.Request(url)
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            for update in data.get("result", []):
                                offset = update["update_id"] + 1
                                message = update.get("message", {})
                                text = message.get("text", "")
                                chat = message.get("chat", {})
                                chat_id = str(chat.get("id", ""))

                                if text and chat_id:
                                    reply = handler.handle_command(chat_id, text, profile)
                                    # Send reply
                                    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                                    payload = json.dumps({"chat_id": chat_id, "text": reply, "parse_mode": "HTML"}).encode("utf-8")
                                    req_send = urllib.request.Request(send_url, data=payload, headers={"Content-Type": "application/json"})
                                    urllib.request.urlopen(req_send, timeout=5)
                    except Exception as e:
                        logger.error(f"Bot poll loop error: {e}")
                    time.sleep(2)
            else:
                # Mock idle worker loop
                while True:
                    time.sleep(5)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\n🛑 Telegram Bot Worker stopped gracefully."))
