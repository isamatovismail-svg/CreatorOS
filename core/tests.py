import os
import shutil
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.management import call_command
from core.models import ContentPost, ContentTopic, UserProfile, SystemLog
from services.ai_provider.ai_manager import AIProviderManager
from services.ai_provider.adapters.default_llm import DefaultLLMProvider
from services.pipeline.service import create_and_generate_post
from services.video.ffmpeg_renderer import FFmpegVideoRenderer
from bot.fallback_manager import TelegramFallbackManager
from bot.bot_runner import CreatorOSBotHandler


class UserAuthAndIsolationTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='creator_one', password='password123')
        self.user2 = User.objects.create_user(username='creator_two', password='password123')

        self.post1 = ContentPost.objects.create(
            user=self.user1,
            title='User 1 Secret Video',
            script='Script 1',
            status='READY_MANUAL'
        )
        self.post2 = ContentPost.objects.create(
            user=self.user2,
            title='User 2 Secret Video',
            script='Script 2',
            status='READY_MANUAL'
        )

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_dashboard_access(self):
        self.client.login(username='creator_one', password='password123')
        response = self.client.get(reverse('core:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User 1 Secret Video')
        self.assertNotContains(response, 'User 2 Secret Video')

    def test_cross_user_isolation_returns_404(self):
        self.client.login(username='creator_one', password='password123')
        url_for_user2_post = reverse('core:post_detail', kwargs={'post_id': self.post2.id})
        response = self.client.get(url_for_user2_post)
        self.assertEqual(response.status_code, 404)


class StructuredAIEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ai_test_user', password='password123')
        self.profile = UserProfile.objects.create(
            user=self.user,
            language='Russian',
            niche='AI and technology',
            duration_seconds=30
        )

    def test_structured_content_fallback_generation(self):
        llm = DefaultLLMProvider()
        res = llm.generate_structured_content(user_profile=self.profile, user_idea='3 AI Productivity Tools')
        
        self.assertIsInstance(res, dict)
        self.assertIn('topic', res)
        self.assertIn('hook', res)
        self.assertIn('script', res)
        self.assertIn('caption', res)
        self.assertEqual(res['duration_seconds'], 30)

    def test_concept_expansion_for_short_idea(self):
        llm = DefaultLLMProvider()
        expanded = llm.expand_concept('dog tips')
        self.assertIn('Dog Tips', expanded)

    def test_topic_duplicate_prevention(self):
        llm = DefaultLLMProvider()
        history = [
            "How AI is Revolutionizing Everyday Productivity in 2026",
            "Top 3 Free AI Tools You Need to Try Today"
        ]
        topic_dict = llm.select_topic(niche="AI and technology", recent_topics=history)
        self.assertNotIn(topic_dict['topic'].lower(), [t.lower() for t in history])


class EndToEndPipelineVideoTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='video_creator', password='password123')
        self.profile = UserProfile.objects.create(user=self.user, duration_seconds=3)

    def test_create_and_generate_post_renders_real_mp4(self):
        post = create_and_generate_post(user=self.user, idea='Test Vertical Video', mode='user_idea')
        
        self.assertEqual(post.status, 'READY_MANUAL')
        self.assertIsNotNone(post.video_file_path)
        self.assertTrue(os.path.exists(post.video_file_path))
        self.assertGreater(os.path.getsize(post.video_file_path), 1024)


class TelegramBotIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tg_creator', password='password123')
        self.profile = UserProfile.objects.create(
            user=self.user,
            duration_seconds=3,
            telegram_linking_code='TB1234',
            telegram_linking_code_expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        self.handler = CreatorOSBotHandler()

    def test_telegram_code_linking(self):
        reply = self.handler.handle_command('88776655', '/start TB1234')
        self.assertIn('Account Linked Successfully', reply)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.telegram_chat_id, '88776655')
        self.assertIsNone(self.profile.telegram_linking_code)

    def test_bot_create_command(self):
        self.profile.telegram_chat_id = '88776655'
        self.profile.save()
        reply = self.handler.handle_command('88776655', '/create AI Coding Hacks', self.profile)
        self.assertIn('rendered and delivered', reply)
        self.assertTrue(ContentPost.objects.filter(user=self.user, idea__icontains='AI Coding Hacks').exists())


class DailyGeneratorCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='daily_creator', password='password123')
        self.profile = UserProfile.objects.create(user=self.user, duration_seconds=3, daily_enabled=True)

    def test_daily_generator_idempotency(self):
        # First execution: Generates daily content
        call_command('generate_daily_content')
        self.assertEqual(ContentPost.objects.filter(user=self.user).count(), 1)

        # Second execution on same date: Skips generation (Idempotent)
        call_command('generate_daily_content')
        self.assertEqual(ContentPost.objects.filter(user=self.user).count(), 1)



class CreatorOSDoctorCommandTests(TestCase):
    def test_doctor_command_execution(self):
        call_command('doctor')


class SecurityPathTraversalTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='security_user', password='password123')
        self.post = ContentPost.objects.create(
            user=self.user,
            title='Security Test',
            media_file_path='/etc/passwd'
        )

    def test_path_traversal_returns_forbidden(self):
        self.client.login(username='security_user', password='password123')
        url = reverse('core:download_media', kwargs={'post_id': self.post.id, 'file_type': 'image'})
        response = self.client.get(url)
        self.assertIn(response.status_code, [403, 404])


class Phase2NewFeaturesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='phase2_user', password='password123')
        self.profile = UserProfile.objects.create(user=self.user)

    def test_google_oauth_login_redirect(self):
        response = self.client.get(reverse('core:google_login'))
        # Should redirect to Google or settings if not configured
        self.assertEqual(response.status_code, 302)

    def test_connected_accounts_creation_and_disconnection(self):
        from core.models import AIProviderAccount
        account = AIProviderAccount.objects.create(
            user=self.user,
            provider='google',
            external_account_id='testuser@gmail.com',
            status='ACTIVE'
        )
        self.assertEqual(account.masked_identifier(), 't•••@gmail.com')

        # Test disconnect via post endpoint
        self.client.login(username='phase2_user', password='password123')
        disconnect_url = reverse('core:disconnect_account', kwargs={'account_id': account.id})
        res = self.client.post(disconnect_url)
        self.assertEqual(res.status_code, 302)
        self.assertFalse(AIProviderAccount.objects.filter(id=account.id).exists())

    def test_ai_provider_router_free_first_selection(self):
        from services.ai.router import AIProviderRouter
        router = AIProviderRouter(user_profile=self.profile)
        provider = router.select_video_provider()
        self.assertEqual(provider.provider_id, 'local')

    def test_video_validator_with_nonexistent_file(self):
        from services.video.validator import validate_video_file, VideoValidationError
        with self.assertRaises(VideoValidationError):
            validate_video_file('/tmp/non_existent_video_file.mp4')

