import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from core.models import UserProfile, ContentPost
from services.pipeline.service import create_and_generate_post

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Idempotent daily automated video content generator for all active users."

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='Run daily generation specifically for a username.'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass idempotency check and force generation.'
        )

    def handle(self, *args, **options):
        target_username = options.get('user')
        force = options.get('force', False)
        today = timezone.now().date()

        self.stdout.write(self.style.SUCCESS(f"Starting CreatorOS Daily Content Generator for date: {today}"))

        profiles = UserProfile.objects.filter(daily_enabled=True)
        if target_username:
            profiles = profiles.filter(user__username=target_username)

        count_generated = 0
        count_skipped = 0
        count_failed = 0

        for profile in profiles:
            user = profile.user
            self.stdout.write(f"Checking user '{user.username}'...")

            # Idempotency check: Has content already been generated today?
            already_generated = ContentPost.objects.filter(
                user=user,
                created_at__date=today
            ).exists()

            if already_generated and not force:
                self.stdout.write(self.style.NOTICE(
                    f"  -> SKIPPED: User '{user.username}' already has content generated for {today}."
                ))
                count_skipped += 1
                continue

            try:
                with transaction.atomic():
                    self.stdout.write(f"  -> GENERATING daily vertical video for '{user.username}'...")
                    post = create_and_generate_post(user=user, idea=None, mode='auto')
                    if post.status == 'READY_MANUAL':
                        self.stdout.write(self.style.SUCCESS(
                            f"  -> SUCCESS: Post #{post.id} ('{post.title}') rendered to MP4 & queued."
                        ))
                        count_generated += 1
                    else:
                        self.stdout.write(self.style.ERROR(
                            f"  -> FAILED: Post #{post.id} generation returned status '{post.status}' ({post.error_message})."
                        ))
                        count_failed += 1
            except Exception as e:
                logger.error(f"Daily generation error for user '{user.username}': {e}")
                self.stdout.write(self.style.ERROR(f"  -> ERROR: {e}"))
                count_failed += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDaily Generation Complete! Total: Generated={count_generated}, Skipped={count_skipped}, Failed={count_failed}"
        ))
