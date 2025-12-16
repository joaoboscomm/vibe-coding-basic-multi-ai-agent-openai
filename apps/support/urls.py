"""
URL configuration for support API.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.support.views import (
    ChatView,
    ChatStatusView,
    ChatSyncView,
    ConversationViewSet,
    CustomerViewSet,
    SubscriptionViewSet,
    InvoiceViewSet,
    SupportTicketViewSet,
    KnowledgeBaseView,
    KnowledgeSearchView,
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'tickets', SupportTicketViewSet, basename='ticket')

urlpatterns = [
    # Chat endpoints
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/sync/', ChatSyncView.as_view(), name='chat-sync'),
    path('chat/status/<str:task_id>/', ChatStatusView.as_view(), name='chat-status'),
    
    # Knowledge base endpoints
    path('knowledge/', KnowledgeBaseView.as_view(), name='knowledge-base'),
    path('knowledge/search/', KnowledgeSearchView.as_view(), name='knowledge-search'),
    
    # ViewSet routes
    path('', include(router.urls)),
]

