"""
FAQ Agent - Handles knowledge-based questions using RAG.
"""
import logging
from typing import Optional
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from apps.agents.base import BaseAgent
from apps.agents.prompts import FAQ_AGENT_PROMPT, TOOL_USE_INSTRUCTIONS
from apps.agents.tools import search_knowledge_base

logger = logging.getLogger(__name__)


class FAQAgent(BaseAgent):
    """
    FAQ Agent that answers questions using the knowledge base.
    Uses RAG (Retrieval Augmented Generation) with pgvector for
    semantic search of documentation and FAQs.
    """
    
    AGENT_TYPE = 'faq'
    SYSTEM_PROMPT = FAQ_AGENT_PROMPT + "\n\n" + TOOL_USE_INSTRUCTIONS

    def __init__(
        self,
        conversation_id: UUID,
        customer_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(conversation_id, customer_id, correlation_id)

    def get_tools(self) -> list:
        """Return FAQ agent tools."""
        return [search_knowledge_base]

    def process(self, user_message: str) -> dict:
        """
        Process the user message using RAG to find relevant knowledge.
        
        Args:
            user_message: The user's question
            
        Returns:
            Dictionary containing the response and metadata
        """
        messages = self.build_messages(user_message)
        tools = self.get_tools()
        tools_used = []
        
        # First, invoke with tools
        response = self.invoke_with_tools(messages, tools)
        
        # Check if there are tool calls
        if response.get('tool_calls'):
            for tool_call in response['tool_calls']:
                tool_name = tool_call.get('name', '')
                tool_args = tool_call.get('args', {})
                
                logger.debug(
                    f"FAQ agent calling tool: {tool_name}",
                    extra={
                        'correlation_id': self.correlation_id,
                        'tool_args': tool_args,
                    }
                )
                
                # Execute the tool
                if tool_name == 'search_knowledge_base':
                    tool_result = search_knowledge_base.invoke(tool_args)
                    tools_used.append({
                        'name': tool_name,
                        'args': tool_args,
                        'result_preview': str(tool_result)[:200],
                    })
                    
                    # Add tool result to messages and get final response
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
            # No tool calls, use direct response
            final_response = response['content']
        
        return {
            'content': final_response,
            'tools_used': tools_used,
            'agent_type': self.AGENT_TYPE,
        }

    def search_and_respond(self, query: str) -> str:
        """
        Convenience method to search knowledge base and generate response.
        
        Args:
            query: The user's question
            
        Returns:
            The generated response
        """
        result = self.execute(query)
        return result['content']

