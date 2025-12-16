"""
Router Agent - Analyzes user intent and routes to specialized agents.
"""
import json
import logging
from typing import Optional
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage

from apps.agents.base import BaseAgent
from apps.agents.prompts import ROUTER_AGENT_PROMPT

logger = logging.getLogger(__name__)


class RouterAgent(BaseAgent):
    """
    Router Agent that analyzes incoming queries and routes them
    to the appropriate specialized agent.
    
    Routes to:
    - FAQ Agent: General questions, how-to, features, documentation
    - Order Agent: Subscriptions, billing, account, payments
    - Escalation Agent: Complex issues, complaints, human intervention needed
    """
    
    AGENT_TYPE = 'router'
    SYSTEM_PROMPT = ROUTER_AGENT_PROMPT

    def __init__(
        self,
        conversation_id: UUID,
        customer_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(conversation_id, customer_id, correlation_id)

    def process(self, user_message: str) -> dict:
        """
        Analyze the user message and determine routing.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing routing decision and metadata
        """
        messages = self.build_messages(user_message)
        
        response_text = self.invoke_llm(messages)
        
        # Try to parse JSON response
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                routing_decision = json.loads(json_str)
            else:
                # Fallback: try to determine route from text
                routing_decision = self._fallback_routing(response_text, user_message)
                
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse router response as JSON: {response_text[:100]}",
                extra={'correlation_id': self.correlation_id}
            )
            routing_decision = self._fallback_routing(response_text, user_message)
        
        # Validate and normalize route
        route = routing_decision.get('route', 'faq').lower()
        if route not in ['faq', 'order', 'escalation']:
            route = 'faq'  # Default to FAQ
            
        result = {
            'content': response_text,
            'route': route,
            'confidence': routing_decision.get('confidence', 0.8),
            'reasoning': routing_decision.get('reasoning', ''),
            'summary': routing_decision.get('summary', user_message[:100]),
            'tools_used': [],
        }
        
        logger.info(
            f"Router decision: {route} (confidence: {result['confidence']})",
            extra={
                'correlation_id': self.correlation_id,
                'route': route,
                'confidence': result['confidence'],
            }
        )
        
        return result

    def _fallback_routing(self, response_text: str, user_message: str) -> dict:
        """
        Fallback routing based on keyword analysis when JSON parsing fails.
        """
        text_lower = (response_text + user_message).lower()
        
        # Escalation indicators
        escalation_keywords = [
            'escalation', 'human', 'complex', 'complaint', 'frustrated',
            'angry', 'urgent', 'emergency', 'manager', 'supervisor'
        ]
        if any(kw in text_lower for kw in escalation_keywords):
            return {
                'route': 'escalation',
                'confidence': 0.7,
                'reasoning': 'Detected escalation keywords',
                'summary': user_message[:100],
            }
        
        # Order/billing indicators
        order_keywords = [
            'subscription', 'billing', 'invoice', 'payment', 'charge',
            'plan', 'upgrade', 'downgrade', 'cancel', 'refund', 'account',
            'price', 'cost', 'fee', 'renew'
        ]
        if any(kw in text_lower for kw in order_keywords):
            return {
                'route': 'order',
                'confidence': 0.75,
                'reasoning': 'Detected billing/subscription keywords',
                'summary': user_message[:100],
            }
        
        # Default to FAQ
        return {
            'route': 'faq',
            'confidence': 0.6,
            'reasoning': 'Default routing to FAQ',
            'summary': user_message[:100],
        }

    def route(self, user_message: str) -> str:
        """
        Convenience method to just get the route.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Route name: 'faq', 'order', or 'escalation'
        """
        result = self.execute(user_message)
        return result['route']

