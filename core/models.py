from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telegram_chat_id = models.CharField(max_length=64, blank=True, null=True, help_text="Telegram Chat ID for bot notifications and manual delivery fallback.")
    openai_api_key = models.CharField(max_length=255, blank=True, null=True)
    preferred_llm = models.CharField(max_length=64, default='default_llm')
    preferred_image_gen = models.CharField(max_length=64, default='pollinations')
    preferred_tts = models.CharField(max_length=64, default='default_tts')

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
    script = models.TextField(blank=True, null=True)
    caption = models.TextField(blank=True, null=True)
    hashtags = models.CharField(max_length=255, blank=True, null=True)
    media_file_path = models.CharField(max_length=512, blank=True, null=True)
    audio_file_path = models.CharField(max_length=512, blank=True, null=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='DRAFT')
    scheduled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True, null=True)

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
