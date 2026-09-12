from django.db import models
from django.contrib.auth.models import User
import secrets
from django.utils import timezone
import datetime

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Telegram Integration & Linking
    telegram_chat_id = models.CharField(max_length=64, blank=True, null=True, help_text="Telegram Chat ID for bot notifications and delivery.")
    telegram_linking_code = models.CharField(max_length=64, blank=True, null=True, unique=True)
    telegram_linking_code_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Content Preferences
    language = models.CharField(max_length=64, default='Russian')
    niche = models.CharField(max_length=255, default='AI and technology')
    target_audience = models.CharField(max_length=255, default='Beginners')
    style = models.CharField(max_length=255, default='Educational and engaging')
    duration_seconds = models.IntegerField(default=45)
    
    # Daily Schedule Settings
    daily_enabled = models.BooleanField(default=True)
    daily_time = models.TimeField(default=datetime.time(10, 0))
    timezone = models.CharField(max_length=64, default='Asia/Tashkent')
    daily_videos_per_day = models.IntegerField(default=1)
    
    # AI BYOK Provider Settings
    openai_api_key = models.CharField(max_length=255, blank=True, null=True)
    preferred_llm = models.CharField(max_length=64, default='default_llm')
    preferred_image_gen = models.CharField(max_length=64, default='pollinations')
    preferred_tts = models.CharField(max_length=64, default='default_tts')

    def generate_telegram_linking_code(self) -> str:
        """Generates a secure 6-digit short-lived linking code for Telegram account linking."""
        code = secrets.token_hex(3).upper() # 6 hex characters
        self.telegram_linking_code = code
        self.telegram_linking_code_expires_at = timezone.now() + datetime.timedelta(minutes=15)
        self.save()
        return code

    @property
    def masked_openai_key(self) -> str:
        """Returns a masked version of the API key for safe UI display."""
        if not self.openai_api_key:
            return "Not Configured (Using Free Fallback Engine)"
        if len(self.openai_api_key) <= 8:
            return "••••••••"
        return f"{self.openai_api_key[:4]}••••••••{self.openai_api_key[-4:]}"

    def __str__(self):
        return f"{self.user.username}'s Profile"


class SocialAccount(models.Model):
    PLATFORM_CHOICES = [
        ('youtube', 'YouTube'),
        ('instagram', 'Instagram'),
        ('tiktok', 'TikTok'),
        ('twitter', 'X / Twitter'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    platform = models.CharField(max_length=32, choices=PLATFORM_CHOICES)
    account_name = models.CharField(max_length=128)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.account_name} ({self.get_platform_display()})"


class ContentTopic(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    target_audience = models.CharField(max_length=255, blank=True, null=True)
    tone = models.CharField(max_length=64, default='Professional & Engaging')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ContentPost(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('GENERATING', 'Generating Assets'),
        ('READY_MANUAL', 'Ready for Manual Upload (Fallback)'),
        ('PUBLISHED', 'Published via API'),
        ('FAILED', 'Generation / Posting Failed'),
    ]

    TELEGRAM_STATUS_CHOICES = [
        ('NOT_SENT', 'Not Sent'),
        ('SENDING', 'Sending'),
        ('SENT', 'Sent to Telegram'),
        ('FAILED', 'Delivery Failed'),
    ]

    PLATFORM_CHOICES = [
        ('youtube', 'YouTube Shorts'),
        ('instagram', 'Instagram Reels'),
        ('tiktok', 'TikTok Video'),
        ('twitter', 'X / Twitter Post'),
        ('all', 'Multi-Platform'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    topic = models.ForeignKey(ContentTopic, on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    title = models.CharField(max_length=255)
    target_platform = models.CharField(max_length=32, choices=PLATFORM_CHOICES, default='all')
    
    # Structured Content Fields
    idea = models.TextField(blank=True, null=True)
    hook = models.TextField(blank=True, null=True)
    script = models.TextField(blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    hashtags = models.CharField(max_length=255, blank=True, null=True)
    promotion_tips = models.TextField(blank=True, null=True)
    recommended_publish_time = models.CharField(max_length=64, blank=True, null=True)
    target_audience = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=64, default='Russian')
    duration_seconds = models.IntegerField(default=45)
    ai_prompt_used = models.TextField(blank=True, null=True)
    
    # Media File Assets
    media_file_path = models.CharField(max_length=512, blank=True, null=True)
    audio_file_path = models.CharField(max_length=512, blank=True, null=True)
    video_file_path = models.CharField(max_length=512, blank=True, null=True)
    
    # Pipeline & Telegram Status Tracking
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='DRAFT')
    telegram_delivery_status = models.CharField(max_length=32, choices=TELEGRAM_STATUS_CHOICES, default='NOT_SENT')
    telegram_message_id = models.CharField(max_length=64, blank=True, null=True)
    telegram_sent_at = models.DateTimeField(blank=True, null=True)
    
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        constraints = [
            # Ensure unique daily generation per user per date when auto-generated
            models.UniqueConstraint(fields=['user', 'scheduled_at'], name='unique_user_daily_scheduled_post')
        ]

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class SystemLog(models.Model):
    LEVEL_CHOICES = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default='INFO')
    module = models.CharField(max_length=64)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def log_event(cls, module: str, message: str, level: str = 'INFO', user=None):
        """Helper method to record system audit logs cleanly."""
        return cls.objects.create(user=user, level=level, module=module, message=message)

    def __str__(self):
        return f"[{self.level}] {self.module} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
