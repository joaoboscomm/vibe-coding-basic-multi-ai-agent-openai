"""
API views for customer support chat system.
"""
import logging
import uuid

from celery.result import AsyncResult
from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.models import Conversation, Message, KnowledgeDocument
from apps.support.models import Customer, Subscription, Invoice, SupportTicket
from apps.support.serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    TaskStatusSerializer,
    ConversationSerializer,
    ConversationListSerializer,
    MessageSerializer,
    CustomerSerializer,
    SubscriptionSerializer,
    InvoiceSerializer,
    SupportTicketSerializer,
    KnowledgeDocumentSerializer,
    KnowledgeSearchSerializer,
)
from apps.support.tasks import process_chat_message
from rag.knowledge_base import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class ChatView(APIView):
    """
    Main chat endpoint for customer support interactions.
    """

    def post(self, request):
        """
        Send a message and start async processing.
        
        Request body:
        - message: The user's message
        - conversation_id: Optional existing conversation UUID
        - customer_email: Optional customer email for account lookups
        
        Returns:
        - task_id: Celery task ID for status polling
        - conversation_id: The conversation UUID
        - status: 'processing'
        """
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        message = data['message']
        conversation_id = data.get('conversation_id')
        customer_email = data.get('customer_email')
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = uuid.uuid4()
        
        # Get correlation ID from request
        correlation_id = getattr(request, 'correlation_id', str(uuid.uuid4()))
        
        logger.info(
            f"Chat request received for conversation {conversation_id}",
            extra={
                'correlation_id': correlation_id,
                'has_customer_email': bool(customer_email),
            }
        )
        
        # Queue the message processing task
        task = process_chat_message.delay(
            conversation_id=str(conversation_id),
            message=message,
            customer_email=customer_email,
            correlation_id=correlation_id,
        )
        
        response_serializer = ChatResponseSerializer(data={
            'task_id': task.id,
            'conversation_id': str(conversation_id),
            'status': 'processing',
            'message': 'Your message is being processed',
        })
        response_serializer.is_valid()
        
        return Response(
            response_serializer.data,
            status=status.HTTP_202_ACCEPTED
        )


class ChatStatusView(APIView):
    """
    Check the status of an async chat processing task.
    """

    def get(self, request, task_id):
        """
        Get the status and result of a chat processing task.
        
        Returns:
        - status: 'pending', 'processing', 'completed', 'failed'
        - result: The agent's response (if completed)
        - error: Error message (if failed)
        """
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.status.lower(),
        }
        
        if task_result.ready():
            if task_result.successful():
                result = task_result.result
                response_data['status'] = 'completed'
                response_data['result'] = result
            else:
                response_data['status'] = 'failed'
                response_data['error'] = str(task_result.result)
        elif task_result.status == 'PENDING':
            response_data['status'] = 'pending'
        else:
            response_data['status'] = 'processing'
        
        return Response(response_data)


class ChatSyncView(APIView):
    """
    Synchronous chat endpoint for testing (not recommended for production).
    """

    def post(self, request):
        """
        Process a chat message synchronously.
        Only use this for testing - production should use async endpoint.
        """
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        message = data['message']
        conversation_id = data.get('conversation_id') or uuid.uuid4()
        customer_email = data.get('customer_email')
        
        correlation_id = getattr(request, 'correlation_id', str(uuid.uuid4()))
        
        # Process synchronously
        from apps.agents.orchestrator import AgentOrchestrator
        from apps.support.models import Customer
        
        customer_id = None
        if customer_email:
            try:
                customer = Customer.objects.get(email=customer_email.lower().strip())
                customer_id = customer.id
            except Customer.DoesNotExist:
                pass
        
        orchestrator = AgentOrchestrator(
            conversation_id=conversation_id,
            customer_id=customer_id,
            customer_email=customer_email,
            correlation_id=correlation_id,
        )
        
        result = orchestrator.process_message(message)
        
        return Response({
            'success': True,
            'content': result['content'],
            'agent_type': result['agent_type'],
            'route': result['route'],
            'routing_confidence': result['routing_confidence'],
            'tools_used': result['tools_used'],
            'conversation_id': str(conversation_id),
        })


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    """
    queryset = Conversation.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        return ConversationSerializer

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a conversation."""
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a conversation."""
        conversation = self.get_object()
        conversation.status = 'closed'
        conversation.save(update_fields=['status', 'updated_at'])
        return Response({'status': 'closed'})


class CustomerViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing customers.
    """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def subscriptions(self, request, pk=None):
        """Get customer's subscriptions."""
        customer = self.get_object()
        subscriptions = customer.subscriptions.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def invoices(self, request, pk=None):
        """Get customer's invoices."""
        customer = self.get_object()
        invoices = customer.invoices.all()
        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """Get customer's support tickets."""
        customer = self.get_object()
        tickets = customer.tickets.all()
        serializer = SupportTicketSerializer(tickets, many=True)
        return Response(serializer.data)


class SubscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing subscriptions.
    """
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing invoices.
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support tickets.
    """
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer


class KnowledgeBaseView(APIView):
    """
    Knowledge base management endpoints.
    """

    def get(self, request):
        """Get all knowledge base documents."""
        category = request.query_params.get('category')
        queryset = KnowledgeDocument.objects.filter(is_active=True)
        
        if category:
            queryset = queryset.filter(category=category)
        
        serializer = KnowledgeDocumentSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Add a new document to the knowledge base."""
        serializer = KnowledgeDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        kb_manager = KnowledgeBaseManager()
        document = kb_manager.add_document(
            title=serializer.validated_data['title'],
            content=serializer.validated_data['content'],
            category=serializer.validated_data.get('category', 'faq'),
            metadata=serializer.validated_data.get('metadata', {}),
        )
        
        return Response(
            KnowledgeDocumentSerializer(document).data,
            status=status.HTTP_201_CREATED
        )


class KnowledgeSearchView(APIView):
    """
    Knowledge base search endpoint.
    """

    def post(self, request):
        """Search the knowledge base."""
        serializer = KnowledgeSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        kb_manager = KnowledgeBaseManager()
        results = kb_manager.search(
            query=serializer.validated_data['query'],
            top_k=serializer.validated_data.get('top_k', 5),
            category=serializer.validated_data.get('category'),
        )
        
        return Response({
            'query': serializer.validated_data['query'],
            'results': results,
            'count': len(results),
        })

