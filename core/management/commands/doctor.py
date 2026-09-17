import os
import sys
import subprocess
import logging
import urllib.request
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "CreatorOS Doctor Diagnostic Command: Audits system dependencies, FFmpeg, DB, Media, AI, TTS, and Telegram."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=========================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("   CreatorOS v0.1 System Diagnostics Doctor"))
        self.stdout.write(self.style.MIGRATE_HEADING("=========================================="))

        checks_passed = 0
        checks_failed = 0
        checks_warned = 0

        def report(status: str, title: str, details: str = ""):
            nonlocal checks_passed, checks_failed, checks_warned
            if status == "PASS":
                checks_passed += 1
                symbol = self.style.SUCCESS("[ PASS ]")
            elif status == "WARN":
                checks_warned += 1
                symbol = self.style.WARNING("[ WARN ]")
            else:
                checks_failed += 1
                symbol = self.style.ERROR("[ FAIL ]")

            self.stdout.write(f"{symbol} {title}")
            if details:
                self.stdout.write(f"         └─ {details}")

        # 1. Django Framework Check
        try:
            from django.core.management import call_command
            call_command('check', verbosity=0)
            report("PASS", "Django Configuration & Settings", "No system check issues identified.")
        except Exception as e:
            report("FAIL", "Django Configuration & Settings", f"Check failed: {e}")

        # 2. Database Connection
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
            report("PASS", "Database Connection", f"Connected to {connection.vendor} database.")
        except Exception as e:
            report("FAIL", "Database Connection", f"Database error: {e}")

        # 3. Media Directory Writability
        try:
            media_dir = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
            os.makedirs(media_dir, exist_ok=True)
            test_file = os.path.join(media_dir, '.doctor_write_test')
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            report("PASS", "Media Storage Directory", f"Writable at '{media_dir}'")
        except Exception as e:
            report("FAIL", "Media Storage Directory", f"Directory write error: {e}")

        # 4. FFmpeg Video Renderer Executable
        try:
            res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "FFmpeg installed"
                report("PASS", "FFmpeg Video Renderer Executable", first_line)
            else:
                report("FAIL", "FFmpeg Video Renderer Executable", "FFmpeg returned error exit code.")
        except FileNotFoundError:
            report("FAIL", "FFmpeg Video Renderer Executable", "FFmpeg executable not found in PATH! Install ffmpeg.")
        except Exception as e:
            report("FAIL", "FFmpeg Video Renderer Executable", f"FFmpeg check error: {e}")

        # 5. FFprobe Audio Duration Analyzer
        try:
            res = subprocess.run(["ffprobe", "-version"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                report("PASS", "FFprobe Audio Inspector", "FFprobe is installed and functional.")
            else:
                report("WARN", "FFprobe Audio Inspector", "FFprobe returned non-zero code.")
        except FileNotFoundError:
            report("WARN", "FFprobe Audio Inspector", "FFprobe executable not found. Fallback durations will be used.")

        # 6. gTTS (Text-to-Speech Engine)
        try:
            from gtts import gTTS
            report("PASS", "gTTS Speech Engine", "gTTS Python library available.")
        except ImportError:
            report("FAIL", "gTTS Speech Engine", "gTTS package not installed in python environment!")

        # 7. Pollinations Image Engine
        try:
            from services.ai_provider.adapters.pollinations_image import PollinationsImageProvider
            provider = PollinationsImageProvider()
            report("PASS", "Pollinations Image Engine", f"Provider '{provider.provider_name}' initialized.")
        except Exception as e:
            report("WARN", "Pollinations Image Engine", f"Provider error: {e}")

        # 8. Default LLM Structured Engine
        try:
            from services.ai_provider.adapters.default_llm import DefaultLLMProvider
            llm = DefaultLLMProvider()
            test_topic = llm.select_topic("AI and technology")
            report("PASS", "Structured AI Script Generator", f"Engine active. Sample topic: '{test_topic['topic']}'")
        except Exception as e:
            report("FAIL", "Structured AI Script Generator", f"Engine failed: {e}")

        # 9. Google OAuth Configuration
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if client_id and client_secret:
            masked_client = client_id[:6] + "••••••••" if len(client_id) > 10 else "Configured"
            report("PASS", "Google OAuth Configuration", f"Client ID: {masked_client}")
        else:
            report("WARN", "Google OAuth Configuration", "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not configured in .env (Google OAuth disabled).")

        # 10. OpenAI API Key Configuration
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and len(openai_key) > 8:
            masked_key = openai_key[:4] + "••••••••" + openai_key[-4:]
            report("PASS", "OpenAI API Key", f"Key configured: {masked_key}")
        else:
            report("WARN", "OpenAI API Key", "OPENAI_API_KEY not configured in .env (using local fallback engine).")

        # 11. AI Video Providers Registration
        try:
            from services.ai.registry import ProviderRegistry
            providers = ProviderRegistry.list_all()
            prov_names = [p.name for p in providers.values()]
            report("PASS", "AI Video Providers Registered", f"{len(providers)} providers active: {', '.join(prov_names)}")
        except Exception as e:
            report("FAIL", "AI Video Providers Registered", f"Registry failure: {e}")

        # 12. Telegram Bot Integration
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token or "your_bot_token" in bot_token or bot_token == "MOCK_BOT_TOKEN":
            report("WARN", "Telegram Bot Token", "TELEGRAM_BOT_TOKEN is not set in environment or is using mock value.")
        else:
            try:
                url = f"https://api.telegram.org/bot{bot_token}/getMe"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    bot_name = data.get("result", {}).get("username", "UnknownBot")
                    report("PASS", "Telegram Bot API", f"Connected as @{bot_name}")
            except Exception as e:
                report("WARN", "Telegram Bot API", f"API connection check failed: {e}")

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING("\n------------------------------------------"))
        self.stdout.write(f"Diagnostic Summary: {checks_passed} PASS, {checks_warned} WARN, {checks_failed} FAIL")
        self.stdout.write(self.style.MIGRATE_HEADING("------------------------------------------\n"))

        if checks_failed > 0:
            self.stdout.write(self.style.ERROR("❌ System has failing critical components. Fix issues above."))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("✅ CreatorOS System Health Doctor checks completed successfully!"))

