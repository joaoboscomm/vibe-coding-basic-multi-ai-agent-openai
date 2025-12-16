"""
Admin configuration for core models.
"""
from django.contrib import admin

from .models import Conversation, Message, KnowledgeDocument


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer_id', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'customer_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'agent_type', 'created_at']
    list_filter = ['role', 'agent_type', 'created_at']
    search_fields = ['content']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['id', 'created_at', 'updated_at']

