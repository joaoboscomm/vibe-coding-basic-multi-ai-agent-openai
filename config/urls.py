"""
URL configuration for customer support system.
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='chat.html'), name='chat'),
    path('admin/', admin.site.urls),
    path('api/', include('apps.support.urls')),
    path('api/health/', include('apps.core.urls')),
]

