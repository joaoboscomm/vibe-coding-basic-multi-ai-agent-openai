"""
Celery tasks for async message processing.
"""
import logging
import uuid

from celery import shared_task
from django.conf import settings

from apps.agents.orchestrator import AgentOrchestrator
from apps.core.models import Conversation
from apps.support.models import Customer

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_chat_message(
    self,
    conversation_id: str,
    message: str,
    customer_email: str = None,
    correlation_id: str = None,
):
    """
    Async task to process a chat message through the multi-agent system.
    
    Args:
        conversation_id: UUID of the conversation
        message: User's message content
        customer_email: Optional customer email for account lookups
        correlation_id: Request correlation ID for tracing
        
    Returns:
        Dictionary with the agent's response
    """
    correlation_id = correlation_id or str(uuid.uuid4())
    
    logger.info(
        f"Processing chat message for conversation {conversation_id}",
        extra={
            'correlation_id': correlation_id,
            'task_id': self.request.id,
        }
    )
    
    try:
        # Get customer ID if email provided
        customer_id = None
        if customer_email:
            try:
                customer = Customer.objects.get(email=customer_email.lower().strip())
                customer_id = customer.id
            except Customer.DoesNotExist:
                logger.warning(
                    f"Customer not found: {customer_email}",
                    extra={'correlation_id': correlation_id}
                )
        
        # Create orchestrator and process message
        orchestrator = AgentOrchestrator(
            conversation_id=uuid.UUID(conversation_id),
            customer_id=customer_id,
            customer_email=customer_email,
            correlation_id=correlation_id,
        )
        
        result = orchestrator.process_message(message)
        
        logger.info(
            f"Chat message processed successfully by {result['agent_type']} agent",
            extra={
                'correlation_id': correlation_id,
                'agent_type': result['agent_type'],
                'conversation_id': conversation_id,
            }
        )
        
        return {
            'success': True,
            'content': result['content'],
            'agent_type': result['agent_type'],
            'route': result['route'],
            'routing_confidence': result['routing_confidence'],
            'tools_used': result['tools_used'],
            'conversation_id': conversation_id,
        }
        
    except Exception as e:
        logger.error(
            f"Failed to process chat message: {e}",
            extra={
                'correlation_id': correlation_id,
                'conversation_id': conversation_id,
            },
            exc_info=True
        )
        
        # Retry on certain errors
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)
        
        return {
            'success': False,
            'error': str(e),
            'conversation_id': conversation_id,
        }


@shared_task
def generate_embeddings_for_documents(document_ids: list[str]):
    """
    Async task to generate embeddings for knowledge base documents.
    
    Args:
        document_ids: List of document UUIDs to process
    """
    from rag.embeddings import get_embeddings_manager
    from apps.core.models import KnowledgeDocument
    
    embeddings_manager = get_embeddings_manager()
    
    for doc_id in document_ids:
        try:
            document = KnowledgeDocument.objects.get(id=doc_id)
            
            if document.embedding is None:
                text_to_embed = f"{document.title}\n\n{document.content}"
                document.embedding = embeddings_manager.embed_text(text_to_embed)
                document.save(update_fields=['embedding', 'updated_at'])
                
                logger.info(f"Generated embedding for document: {doc_id}")
                
        except KnowledgeDocument.DoesNotExist:
            logger.warning(f"Document not found: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to generate embedding for {doc_id}: {e}")


@shared_task
def cleanup_old_conversations(days_old: int = 30):
    """
    Cleanup conversations older than specified days.
    Soft-deletes by setting status to 'closed'.
    
    Args:
        days_old: Number of days after which to cleanup
    """
    from datetime import timedelta
    from django.utils import timezone
    
    cutoff_date = timezone.now() - timedelta(days=days_old)
    
    updated = Conversation.objects.filter(
        status='active',
        updated_at__lt=cutoff_date
    ).update(status='closed')
    
    logger.info(f"Closed {updated} old conversations")
    return updated


@shared_task
def sync_customer_conversation_data():
    """
    Periodic task to sync customer data with conversations.
    Links orphaned conversations to customers based on metadata.
    """
    from apps.core.models import Conversation
    
    # Find conversations with customer_id in metadata but not linked
    conversations = Conversation.objects.filter(
        customer_id__isnull=True,
        metadata__has_key='customer_email'
    )
    
    linked_count = 0
    for conv in conversations:
        email = conv.metadata.get('customer_email')
        if email:
            try:
                customer = Customer.objects.get(email=email.lower().strip())
                conv.customer_id = customer.id
                conv.save(update_fields=['customer_id', 'updated_at'])
                linked_count += 1
            except Customer.DoesNotExist:
                pass
    
    logger.info(f"Linked {linked_count} conversations to customers")
    return linked_count

