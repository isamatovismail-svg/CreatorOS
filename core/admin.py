from django.contrib import admin
from .models import UserProfile, SocialAccount, ContentTopic, ContentPost, SystemLog

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'telegram_chat_id', 'preferred_llm', 'preferred_image_gen', 'preferred_tts')

@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ('account_name', 'user', 'platform', 'is_active', 'token_expires_at')
    list_filter = ('platform', 'is_active')

@admin.register(ContentTopic)
class ContentTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'tone', 'created_at')

@admin.register(ContentPost)
class ContentPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'target_platform', 'status', 'scheduled_at', 'created_at')
    list_filter = ('status', 'target_platform')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'module', 'message', 'created_at')
    list_filter = ('level', 'module')
