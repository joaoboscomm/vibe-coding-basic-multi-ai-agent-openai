"""
Escalation Agent - Handles complex issues requiring human intervention.
"""
import logging
from typing import Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from apps.agents.base import BaseAgent
from apps.agents.prompts import ESCALATION_AGENT_PROMPT, TOOL_USE_INSTRUCTIONS
from apps.agents.tools import create_support_ticket

logger = logging.getLogger(__name__)


class EscalationAgent(BaseAgent):
    """
    Escalation Agent that handles complex issues requiring human intervention.
    Creates support tickets and ensures proper documentation of issues.
    """
    
    AGENT_TYPE = 'escalation'
    SYSTEM_PROMPT = ESCALATION_AGENT_PROMPT + "\n\n" + TOOL_USE_INSTRUCTIONS

    def __init__(
        self,
        conversation_id: UUID,
        customer_id: Optional[UUID] = None,
        customer_email: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(conversation_id, customer_id, correlation_id)
        self.customer_email = customer_email

    def get_tools(self) -> list:
        """Return Escalation agent tools."""
        return [create_support_ticket]

    def process(self, user_message: str) -> dict:
        """
        Process escalation requests and create support tickets.
        
        Args:
            user_message: The user's issue description
            
        Returns:
            Dictionary containing the response and metadata
        """
        # Add customer context
        context_parts = []
        if self.customer_email:
            context_parts.append(f"Customer Email: {self.customer_email}")
        context_parts.append(f"Conversation ID: {self.conversation_id}")
        
        context_message = f"[{', '.join(context_parts)}]\n\n{user_message}"
        
        messages = self.build_messages(context_message)
        tools = self.get_tools()
        tools_used = []
        
        # Invoke with tools
        response = self.invoke_with_tools(messages, tools)
        
        # Process tool calls
        if response.get('tool_calls'):
            for tool_call in response['tool_calls']:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})
                
                # Add conversation_id if not present
                if tool_name == 'create_support_ticket':
                    if 'conversation_id' not in tool_args:
                        tool_args['conversation_id'] = str(self.conversation_id)
                
                logger.debug(
                    f"Escalation agent calling tool: {tool_name}",
                    extra={
                        'correlation_id': self.correlation_id,
                        'tool_args': tool_args,
                    }
                )
                
                # Execute the tool
                if tool_name == 'create_support_ticket':
                    tool_result = create_support_ticket.invoke(tool_args)
                    tools_used.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_preview': str(tool_result)[:200],
                    })
                    
                    # Add tool result to messages
                    messages.append(AIMessage(
                        content=response['content'],
                        tool_calls=[tool_call]
                    ))
                    messages.append(ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call.get('id', 'tool_call_1')
                    ))
            
            # Get final response with tool results
            final_response = self.invoke_llm(messages)
            
            # Update conversation status to escalated
            self.memory.update_conversation_status('escalated')
        else:
            final_response = response['content']
        
        return {
            'content': final_response,
            'tools_used': tools_used,
            'agent_type': self.AGENT_TYPE,
        }

    def escalate(
        self,
        customer_email: str,
        issue_description: str,
        category: str = 'other',
    ) -> str:
        """
        Directly escalate an issue and create a ticket.
        
        Args:
            customer_email: Customer's email address
            issue_description: Description of the issue
            category: Issue category
            
        Returns:
            Escalation confirmation message
        """
        self.customer_email = customer_email
        result = self.execute(
            f"Please create a support ticket for this issue:\n\n"
            f"Category: {category}\n"
            f"Issue: {issue_description}"
        )
        return result['content']

