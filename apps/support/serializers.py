"""
Serializers for support API endpoints.
"""
from rest_framework import serializers

from apps.core.models import Conversation, Message, KnowledgeDocument
from apps.support.models import Customer, Subscription, Invoice, SupportTicket


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    
    class Meta:
        model = Message
        fields = [
            'id', 'role', 'content', 'agent_type', 
            'tool_calls', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""
    messages = MessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_id', 'title', 'status', 
            'metadata', 'created_at', 'updated_at',
            'messages', 'message_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for conversation lists."""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'customer_id', 'title', 'status',
            'created_at', 'updated_at', 'message_count', 'last_message'
        ]
    
    def get_message_count(self, obj):
        return obj.messages.count()
    
    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100] + '...' if len(last_msg.content) > 100 else last_msg.content,
                'created_at': last_msg.created_at,
            }
        return None


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request."""
    message = serializers.CharField(max_length=10000)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    customer_email = serializers.EmailField(required=False, allow_null=True)


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response."""
    task_id = serializers.CharField()
    conversation_id = serializers.UUIDField()
    status = serializers.CharField()
    message = serializers.CharField(required=False)


class TaskStatusSerializer(serializers.Serializer):
    """Serializer for task status response."""
    task_id = serializers.CharField()
    status = serializers.CharField()
    result = serializers.DictField(required=False)
    error = serializers.CharField(required=False)


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model."""
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = Customer
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'company_name', 'phone', 'is_active', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for Subscription model."""
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    
    class Meta:
        model = Subscription
        fields = [
            'id', 'customer', 'customer_email', 'plan', 'status',
            'billing_cycle', 'price', 'start_date', 'end_date',
            'trial_end_date', 'seats', 'features', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Invoice model."""
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'customer', 'customer_email', 'subscription',
            'invoice_number', 'status', 'amount', 'tax', 'total',
            'currency', 'due_date', 'paid_date', 'description',
            'line_items', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    """Serializer for SupportTicket model."""
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'customer', 'customer_email', 'conversation_id',
            'subject', 'description', 'category', 'priority', 'status',
            'assigned_to', 'resolution', 'resolved_at', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """Serializer for KnowledgeDocument model."""
    
    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'content', 'category', 
            'is_active', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class KnowledgeSearchSerializer(serializers.Serializer):
    """Serializer for knowledge base search request."""
    query = serializers.CharField(max_length=1000)
    category = serializers.ChoiceField(
        choices=['faq', 'documentation', 'policy', 'troubleshooting'],
        required=False,
        allow_null=True
    )
    top_k = serializers.IntegerField(min_value=1, max_value=20, default=5)

