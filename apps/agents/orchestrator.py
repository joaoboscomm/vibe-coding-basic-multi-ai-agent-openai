"""
Agent Orchestrator - Coordinates the multi-agent system.
"""
import logging
from typing import Optional
from uuid import UUID

from apps.agents.router import RouterAgent
from apps.agents.faq import FAQAgent
from apps.agents.order import OrderAgent
from apps.agents.escalation import EscalationAgent
from apps.agents.memory import ConversationMemory

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the multi-agent customer support system.
    Routes incoming messages to appropriate specialized agents
    and manages conversation flow.
    """
    
    def __init__(
        self,
        conversation_id: UUID,
        customer_id: Optional[UUID] = None,
        customer_email: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        self.conversation_id = conversation_id
        self.customer_id = customer_id
        self.customer_email = customer_email
        self.correlation_id = correlation_id or ''
        
        # Initialize memory
        self.memory = ConversationMemory(conversation_id)
        
        # Initialize router
        self.router = RouterAgent(
            conversation_id=conversation_id,
            customer_id=customer_id,
            correlation_id=correlation_id,
        )
        
        # Agent registry
        self._agents = {
            'faq': FAQAgent,
            'order': OrderAgent,
            'escalation': EscalationAgent,
        }

    def _get_agent(self, agent_type: str):
        """Get an instance of the specified agent type."""
        agent_class = self._agents.get(agent_type)
        
        if not agent_class:
            logger.warning(f"Unknown agent type: {agent_type}, defaulting to FAQ")
            agent_class = FAQAgent
        
        # Create agent with appropriate parameters
        if agent_type in ['order', 'escalation']:
            return agent_class(
                conversation_id=self.conversation_id,
                customer_id=self.customer_id,
                customer_email=self.customer_email,
                correlation_id=self.correlation_id,
            )
        else:
            return agent_class(
                conversation_id=self.conversation_id,
                customer_id=self.customer_id,
                correlation_id=self.correlation_id,
            )

    def process_message(self, user_message: str) -> dict:
        """
        Process a user message through the multi-agent system.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing:
            - content: The response message
            - agent_type: The agent that handled the request
            - route: The routing decision
            - tools_used: List of tools used
        """
        logger.info(
            f"Processing message in conversation {self.conversation_id}",
            extra={'correlation_id': self.correlation_id}
        )
        
        # Save user message to memory
        self.memory.add_user_message(
            content=user_message,
            metadata={'correlation_id': self.correlation_id}
        )
        
        # Route the message
        routing_result = self.router.process(user_message)
        route = routing_result['route']
        
        logger.info(
            f"Routed to {route} agent (confidence: {routing_result['confidence']})",
            extra={
                'correlation_id': self.correlation_id,
                'route': route,
            }
        )
        
        # Get the appropriate agent and process
        agent = self._get_agent(route)
        result = agent.execute(user_message)
        
        return {
            'content': result['content'],
            'agent_type': route,
            'route': route,
            'routing_confidence': routing_result['confidence'],
            'routing_reasoning': routing_result['reasoning'],
            'tools_used': result.get('tools_used', []),
            'conversation_id': str(self.conversation_id),
        }

    def get_conversation_summary(self) -> dict:
        """Get a summary of the current conversation."""
        return self.memory.get_summary()

    def close_conversation(self):
        """Mark the conversation as closed."""
        self.memory.update_conversation_status('closed')
        logger.info(
            f"Conversation {self.conversation_id} closed",
            extra={'correlation_id': self.correlation_id}
        )

