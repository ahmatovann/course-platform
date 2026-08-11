from django.contrib import admin
from django.urls import path, include
from django.urls import re_path

from .media_views import serve_media

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.accounts.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/admin/', include('apps.admin_panel.urls')),
    path('api/chats/', include('apps.chats.urls')),
    path('api/news/', include('apps.schedule.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    re_path(r'^media/(?P<path>.*)$', serve_media),
]
