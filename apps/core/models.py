"""
Core models for conversation history and knowledge documents.
"""
import uuid

from django.db import models
from pgvector.django import VectorField


class BaseModel(models.Model):
    """Abstract base model with common fields."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Conversation(BaseModel):
    """Stores chat sessions."""
    customer_id = models.UUIDField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('escalated', 'Escalated'),
        ],
        default='active'
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversation {self.id} - {self.status}"


class Message(BaseModel):
    """Individual messages within a conversation."""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
        ('tool', 'Tool'),
    ]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    agent_type = models.CharField(max_length=50, blank=True, default='')
    tool_calls = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class KnowledgeDocument(BaseModel):
    """RAG documents with vector embeddings for FAQ search."""
    title = models.CharField(max_length=255)
    content = models.TextField()
    category = models.CharField(
        max_length=50,
        choices=[
            ('faq', 'FAQ'),
            ('documentation', 'Documentation'),
            ('policy', 'Policy'),
            ('troubleshooting', 'Troubleshooting'),
        ],
        default='faq'
    )
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'knowledge_documents'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

