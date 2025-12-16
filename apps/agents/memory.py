"""
Conversation memory management with sliding window context.
"""
import logging
from typing import Optional
from uuid import UUID

from django.conf import settings

from apps.core.models import Conversation, Message

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Manages conversation memory with a sliding window context.
    Stores messages in PostgreSQL and retrieves the last N messages for context.
    """
    
    WINDOW_SIZE = getattr(settings, 'CONTEXT_WINDOW_SIZE', 15)

    def __init__(self, conversation_id: UUID):
        self.conversation_id = conversation_id
        self._conversation: Optional[Conversation] = None

    @property
    def conversation(self) -> Conversation:
        """Get or create the conversation instance."""
        if self._conversation is None:
            self._conversation, created = Conversation.objects.get_or_create(
                id=self.conversation_id,
                defaults={'status': 'active'}
            )
            if created:
                logger.info(f"Created new conversation: {self.conversation_id}")
        return self._conversation

    def get_context(self) -> list[dict]:
        """
        Returns the last WINDOW_SIZE messages for context.
        
        Returns:
            List of message dictionaries with role and content.
        """
        messages = Message.objects.filter(
            conversation_id=self.conversation_id
        ).order_by('-created_at')[:self.WINDOW_SIZE]
        
        # Reverse to get chronological order
        messages = list(messages)[::-1]
        
        context = []
        for msg in messages:
            context.append({
                'role': msg.role,
                'content': msg.content,
            })
            
        logger.debug(
            f"Retrieved {len(context)} messages for conversation {self.conversation_id}"
        )
        return context

    def get_langchain_messages(self) -> list:
        """
        Returns messages in LangChain message format.
        
        Returns:
            List of LangChain message objects.
        """
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
        
        context = self.get_context()
        lc_messages = []
        
        for msg in context:
            if msg['role'] == 'user':
                lc_messages.append(HumanMessage(content=msg['content']))
            elif msg['role'] == 'assistant':
                lc_messages.append(AIMessage(content=msg['content']))
            elif msg['role'] == 'system':
                lc_messages.append(SystemMessage(content=msg['content']))
                
        return lc_messages

    def add_message(
        self,
        role: str,
        content: str,
        agent_type: str = '',
        tool_calls: list = None,
        metadata: dict = None
    ) -> Message:
        """
        Add a new message to the conversation.
        
        Args:
            role: Message role (user, assistant, system, tool)
            content: Message content
            agent_type: Type of agent that generated the message
            tool_calls: List of tool calls made
            metadata: Additional metadata
            
        Returns:
            The created Message instance.
        """
        message = Message.objects.create(
            conversation=self.conversation,
            role=role,
            content=content,
            agent_type=agent_type,
            tool_calls=tool_calls or [],
            metadata=metadata or {}
        )
        
        logger.debug(
            f"Added {role} message to conversation {self.conversation_id}"
        )
        return message

    def add_user_message(self, content: str, metadata: dict = None) -> Message:
        """Add a user message to the conversation."""
        return self.add_message(
            role='user',
            content=content,
            metadata=metadata
        )

    def add_assistant_message(
        self,
        content: str,
        agent_type: str = '',
        tool_calls: list = None,
        metadata: dict = None
    ) -> Message:
        """Add an assistant message to the conversation."""
        return self.add_message(
            role='assistant',
            content=content,
            agent_type=agent_type,
            tool_calls=tool_calls,
            metadata=metadata
        )

    def get_message_count(self) -> int:
        """Get the total number of messages in the conversation."""
        return Message.objects.filter(
            conversation_id=self.conversation_id
        ).count()

    def clear(self):
        """Clear all messages in the conversation."""
        deleted_count, _ = Message.objects.filter(
            conversation_id=self.conversation_id
        ).delete()
        logger.info(
            f"Cleared {deleted_count} messages from conversation {self.conversation_id}"
        )

    def update_conversation_status(self, status: str):
        """Update the conversation status."""
        self.conversation.status = status
        self.conversation.save(update_fields=['status', 'updated_at'])

    def get_summary(self) -> dict:
        """Get a summary of the conversation."""
        return {
            'conversation_id': str(self.conversation_id),
            'status': self.conversation.status,
            'message_count': self.get_message_count(),
            'created_at': self.conversation.created_at.isoformat(),
            'updated_at': self.conversation.updated_at.isoformat(),
        }

