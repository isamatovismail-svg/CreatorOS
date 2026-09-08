from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import ContentPost, ContentTopic, UserProfile, SystemLog
from services.ai_provider.ai_manager import AIProviderManager
from services.pipeline.generator import ContentPipelineGenerator
from bot.fallback_manager import TelegramFallbackManager
from bot.bot_runner import CreatorOSBotHandler

class IndexViewTests(TestCase):
    def test_index_view_status_code(self):
        url = reverse('core:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_index_view_uses_correct_template(self):
        url = reverse('core:index')
        response = self.client.get(url)
        self.assertTemplateUsed(response, 'core/index.html')
        self.assertTemplateUsed(response, 'base.html')
        self.assertContains(response, 'Welcome to CreatorOS')


class AIProviderTests(TestCase):
    def test_ai_provider_manager_retrieval(self):
        llm = AIProviderManager.get_llm('default_llm')
        self.assertIsNotNone(llm)
        self.assertEqual(llm.provider_name, 'default_llm')

        image_gen = AIProviderManager.get_image('pollinations')
        self.assertIsNotNone(image_gen)

        tts = AIProviderManager.get_tts('default_tts')
        self.assertIsNotNone(tts)

    def test_byok_key_resolution(self):
        user = User.objects.create_user(username='byok_user', password='password123')
        profile = UserProfile.objects.create(user=user, openai_api_key='sk-proj-12345678901234567890')
        provider, key = AIProviderManager.resolve_llm_for_user(profile)
        self.assertEqual(key, 'sk-proj-12345678901234567890')
        self.assertEqual(profile.masked_openai_key, 'sk-p••••••••7890')

    def test_pipeline_generator_execution(self):
        user = User.objects.create_user(username='testcreator', password='password123')
        topic = ContentTopic.objects.create(user=user, title='AI Automation Trends')
        post = ContentPost.objects.create(
            user=user,
            topic=topic,
            title='AI Automation Trends Overview',
            target_platform='youtube'
        )

        pipeline = ContentPipelineGenerator()
        updated_post = pipeline.generate_post_content(post)

        self.assertEqual(updated_post.status, 'READY_MANUAL')
        self.assertIsNotNone(updated_post.script)
        self.assertIsNotNone(updated_post.caption)
        self.assertIsNotNone(updated_post.media_file_path)


class TelegramBotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='telegram_user', password='password123')
        self.profile = UserProfile.objects.create(user=self.user, telegram_chat_id='12345678')
        self.handler = CreatorOSBotHandler()

    def test_start_command(self):
        reply = self.handler.handle_command('99999', '/start', self.profile)
        self.assertIn('Welcome to', reply)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.telegram_chat_id, '99999')

    def test_generate_command(self):
        reply = self.handler.handle_command('12345678', '/generate SaaS Marketing', self.profile)
        self.assertIn('Post generation completed', reply)
        self.assertTrue(ContentPost.objects.filter(user=self.user, title__icontains='SaaS Marketing').exists())

    def test_fallback_manager_delivery(self):
        post = ContentPost.objects.create(
            user=self.user,
            title='Fallback Test Post',
            caption='Test caption',
            hashtags='#test'
        )
        fallback_mgr = TelegramFallbackManager()
        result = fallback_mgr.send_post_fallback(post)
        self.assertTrue(result)
        post.refresh_from_db()
        self.assertEqual(post.status, 'READY_MANUAL')


class PostDetailViewTests(TestCase):
    def setUp(self):
        self.user, _ = User.objects.get_or_create(username='demo_creator')
        self.post = ContentPost.objects.create(
            user=self.user,
            title='Detail View Post',
            script='Original Script',
            caption='Original Caption'
        )

    def test_post_detail_view(self):
        url = reverse('core:post_detail', kwargs={'post_id': self.post.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detail View Post')

    def test_post_delete(self):
        url = reverse('core:delete_post', kwargs={'post_id': self.post.id})
        response = self.client.get(url)
        self.assertRedirects(response, reverse('core:index'))
        self.assertFalse(ContentPost.objects.filter(id=self.post.id).exists())


class SaaSPageNavigationTests(TestCase):
    def test_planner_page(self):
        response = self.client.get(reverse('core:planner'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Content Planner')

    def test_ai_generator_page(self):
        response = self.client.get(reverse('core:ai_generator'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'AI Studio')

    def test_analytics_page(self):
        response = self.client.get(reverse('core:analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Analytics')

    def test_assets_page(self):
        response = self.client.get(reverse('core:assets'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Assets Library')

    def test_settings_page(self):
        response = self.client.get(reverse('core:settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Settings')
