import os
import sys
import time
import signal
import subprocess
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Unified CreatorOS Launcher: Runs Django web server, Telegram Bot worker, and Daily Content Scheduler concurrently in one command.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=str,
            default='8000',
            help='Port for Django web server (default: 8000).'
        )
        parser.add_argument(
            '--no-bot',
            action='store_true',
            help='Disable background Telegram bot worker.'
        )
        parser.add_argument(
            '--no-scheduler',
            action='store_true',
            help='Disable background daily content scheduler.'
        )
        parser.add_argument(
            '--ssl',
            action='store_true',
            help='Enable HTTPS development server (runsslserver).'
        )

    def handle(self, *args, **options):
        port = options.get('port', '8000')
        no_bot = options.get('no_bot', False)
        no_scheduler = options.get('no_scheduler', False)
        use_ssl = options.get('ssl', False)
        python_exec = sys.executable

        self.stdout.write(self.style.MIGRATE_HEADING("=============================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("   🚀 Launching CreatorOS Unified Services    "))
        self.stdout.write(self.style.MIGRATE_HEADING("=============================================="))

        processes = []

        def shutdown_all(signum=None, frame=None):
            self.stdout.write(self.style.WARNING("\n🛑 Stopping all CreatorOS unified services..."))
            for name, proc in processes:
                if proc and proc.poll() is None:
                    self.stdout.write(f"  └─ Terminating {name} (PID: {proc.pid})...")
                    try:
                        proc.terminate()
                        proc.wait(timeout=5)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
            self.stdout.write(self.style.SUCCESS("✅ All CreatorOS services stopped gracefully."))
            sys.exit(0)

        # Register signal handlers for clean SIGINT / SIGTERM shutdown
        signal.signal(signal.SIGINT, shutdown_all)
        signal.signal(signal.SIGTERM, shutdown_all)

        try:
            # 1. Launch Django Web Server process
            server_cmd_name = "runsslserver" if use_ssl else "runserver"
            scheme = "https" if use_ssl else "http"
            web_cmd = [python_exec, "manage.py", server_cmd_name, port]
            self.stdout.write(self.style.SUCCESS(f"[1/3] Starting Web Server on {scheme}://127.0.0.1:{port}/..."))
            web_proc = subprocess.Popen(web_cmd)
            processes.append(("Django Web Server", web_proc))


            # 2. Launch Telegram Bot Worker process
            if not no_bot:
                bot_cmd = [python_exec, "manage.py", "run_bot"]
                self.stdout.write(self.style.SUCCESS("[2/3] Starting Telegram Bot Listener..."))
                bot_proc = subprocess.Popen(bot_cmd)
                processes.append(("Telegram Bot Worker", bot_proc))
            else:
                self.stdout.write(self.style.NOTICE("[2/3] Telegram Bot Worker: Skipped (--no-bot)"))

            # 3. Launch Daily Content Scheduler Loop process
            if not no_scheduler:
                sched_cmd = [python_exec, "manage.py", "generate_daily_content"]
                self.stdout.write(self.style.SUCCESS("[3/3] Executing Initial Daily Content Scheduler..."))
                sched_proc = subprocess.Popen(sched_cmd)
                processes.append(("Daily Content Scheduler", sched_proc))
            else:
                self.stdout.write(self.style.NOTICE("[3/3] Daily Content Scheduler: Skipped (--no-scheduler)"))

            self.stdout.write(self.style.MIGRATE_HEADING("\n----------------------------------------------"))
            self.stdout.write(self.style.SUCCESS("✅ CreatorOS Unified Launcher is running!"))
            self.stdout.write(self.style.SUCCESS("Press Ctrl+C to stop all services."))
            self.stdout.write(self.style.MIGRATE_HEADING("----------------------------------------------\n"))

            # Monitor processes loop
            scheduler_last_run = time.time()
            scheduler_interval_sec = 300  # Check daily content every 5 minutes in background loop

            while True:
                time.sleep(2)

                # Check process statuses
                for name, proc in list(processes):
                    status = proc.poll()
                    if status is not None and status != 0:
                        self.stdout.write(self.style.ERROR(
                            f"⚠️ Process '{name}' (PID: {proc.pid}) exited unexpectedly with code {status}!"
                        ))

                # Periodic background daily content check
                if not no_scheduler and (time.time() - scheduler_last_run >= scheduler_interval_sec):
                    scheduler_last_run = time.time()
                    self.stdout.write(self.style.SUCCESS("⏰ Running periodic daily content check..."))
                    sched_cmd = [python_exec, "manage.py", "generate_daily_content"]
                    subprocess.Popen(sched_cmd)

        except Exception as e:
            logger.error(f"Unified launcher error: {e}")
            shutdown_all()
