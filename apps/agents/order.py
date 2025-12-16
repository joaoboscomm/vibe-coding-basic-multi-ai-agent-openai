"""
Order Agent - Handles subscription, billing, and account inquiries.
"""
import logging
from typing import Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from apps.agents.base import BaseAgent
from apps.agents.prompts import ORDER_AGENT_PROMPT, TOOL_USE_INSTRUCTIONS
from apps.agents.tools import get_customer_info, get_subscription_details, get_invoices

logger = logging.getLogger(__name__)


class OrderAgent(BaseAgent):
    """
    Order Agent that handles subscription, billing, and account-related inquiries.
    Has access to customer data, subscription details, and invoice history.
    """
    
    AGENT_TYPE = 'order'
    SYSTEM_PROMPT = ORDER_AGENT_PROMPT + "\n\n" + TOOL_USE_INSTRUCTIONS

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
        """Return Order agent tools."""
        return [get_customer_info, get_subscription_details, get_invoices]

    def process(self, user_message: str) -> dict:
        """
        Process account/billing related queries.
        
        Args:
            user_message: The user's question about their account
            
        Returns:
            Dictionary containing the response and metadata
        """
        # If we have customer email, add it to context
        context_message = user_message
        if self.customer_email:
            context_message = f"[Customer Email: {self.customer_email}]\n\n{user_message}"
        
        messages = self.build_messages(context_message)
        tools = self.get_tools()
        tools_used = []
        
        # Invoke with tools
        response = self.invoke_with_tools(messages, tools)
        
        # Process any tool calls
        if response.get('tool_calls'):
            for tool_call in response['tool_calls']:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})
                
                logger.debug(
                    f"Order agent calling tool: {tool_name}",
                    extra={
                        'correlation_id': self.correlation_id,
                        'tool_args': tool_args,
                    }
                )
                
                # Execute the appropriate tool
                tool_result = None
                if tool_name == 'get_customer_info':
                    tool_result = get_customer_info.invoke(tool_args)
                elif tool_name == 'get_subscription_details':
                    tool_result = get_subscription_details.invoke(tool_args)
                elif tool_name == 'get_invoices':
                    tool_result = get_invoices.invoke(tool_args)
                
                if tool_result:
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
        else:
            final_response = response['content']
        
        return {
            'content': final_response,
            'tools_used': tools_used,
            'agent_type': self.AGENT_TYPE,
        }

    def lookup_account(self, customer_email: str) -> str:
        """
        Look up complete account information.
        
        Args:
            customer_email: Customer's email address
            
        Returns:
            Formatted account information
        """
        self.customer_email = customer_email
        result = self.execute(f"Please look up the account information for {customer_email}")
        return result['content']

