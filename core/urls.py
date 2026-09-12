from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register_view, name='register'),
    path('post/<int:post_id>/', views.post_detail, name='post_detail'),
    path('post/<int:post_id>/regenerate/', views.regenerate_post, name='regenerate_post'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/download/<str:file_type>/', views.download_media, name='download_media'),
    path('planner/', views.planner_view, name='planner'),
    path('ai-generator/', views.ai_generator_view, name='ai_generator'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('assets/', views.assets_library_view, name='assets'),
    path('settings/', views.settings_view, name='settings'),
]
