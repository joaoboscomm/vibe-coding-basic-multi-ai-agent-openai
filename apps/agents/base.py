"""
Base agent class with CO-STAR framework and common functionality.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import UUID

from django.conf import settings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from apps.core.middleware import AgentTracingMiddleware
from apps.agents.memory import ConversationMemory

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the multi-agent system.
    Provides common functionality including:
    - LLM initialization with configurable parameters
    - Conversation memory management
    - Execution tracing and logging
    - CO-STAR framework prompting
    """
    
    # To be overridden by subclasses
    AGENT_TYPE: str = 'base'
    SYSTEM_PROMPT: str = ''

    def __init__(
        self,
        conversation_id: UUID,
        customer_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
    ):
        self.conversation_id = conversation_id
        self.customer_id = customer_id
        self.correlation_id = correlation_id or ''
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
        )
        
        # Initialize memory
        self.memory = ConversationMemory(conversation_id)
        
        # Link customer to conversation if provided
        if customer_id:
            self.memory.conversation.customer_id = customer_id
            self.memory.conversation.save(update_fields=['customer_id'])

    def get_tools(self) -> list:
        """
        Return the tools available to this agent.
        Override in subclasses to provide agent-specific tools.
        """
        return []

    def build_messages(self, user_message: str) -> list:
        """
        Build the message list for the LLM including system prompt,
        conversation history, and the new user message.
        """
        messages = []
        
        # Add system prompt
        if self.SYSTEM_PROMPT:
            messages.append(SystemMessage(content=self.SYSTEM_PROMPT))
        
        # Add conversation history
        messages.extend(self.memory.get_langchain_messages())
        
        # Add new user message
        messages.append(HumanMessage(content=user_message))
        
        return messages

    @abstractmethod
    def process(self, user_message: str) -> dict:
        """
        Process the user message and return a response.
        Must be implemented by subclasses.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing the response and metadata
        """
        pass

    def execute(self, user_message: str) -> dict:
        """
        Execute the agent with tracing and error handling.
        This is the main entry point for agent execution.
        
        Args:
            user_message: The user's input message
            
        Returns:
            Dictionary containing the response and metadata
        """
        start_time = time.time()
        success = True
        tools_used = []
        response_content = ''
        
        # Trace agent start
        AgentTracingMiddleware.trace_agent_call(
            agent_type=self.AGENT_TYPE,
            conversation_id=str(self.conversation_id),
            correlation_id=self.correlation_id,
            input_message=user_message,
        )
        
        try:
            # Process the message
            result = self.process(user_message)
            response_content = result.get('content', '')
            tools_used = result.get('tools_used', [])
            
            # Save assistant response to memory
            self.memory.add_assistant_message(
                content=response_content,
                agent_type=self.AGENT_TYPE,
                tool_calls=tools_used,
                metadata={
                    'correlation_id': self.correlation_id,
                }
            )
            
            return result
            
        except Exception as e:
            success = False
            logger.error(
                f"Agent execution failed: {e}",
                extra={
                    'correlation_id': self.correlation_id,
                    'agent_type': self.AGENT_TYPE,
                    'conversation_id': str(self.conversation_id),
                },
                exc_info=True
            )
            raise
            
        finally:
            duration_ms = (time.time() - start_time) * 1000
            AgentTracingMiddleware.trace_agent_result(
                agent_type=self.AGENT_TYPE,
                conversation_id=str(self.conversation_id),
                correlation_id=self.correlation_id,
                output_message=response_content,
                duration_ms=duration_ms,
                success=success,
                tools_used=tools_used,
            )

    def invoke_llm(self, messages: list) -> str:
        """
        Invoke the LLM with the given messages.
        
        Args:
            messages: List of LangChain message objects
            
        Returns:
            The LLM response content as a string
        """
        response = self.llm.invoke(messages)
        return response.content

    def invoke_with_tools(self, messages: list, tools: list) -> dict:
        """
        Invoke the LLM with tools bound.
        
        Args:
            messages: List of LangChain message objects
            tools: List of tool functions
            
        Returns:
            Dictionary with response content and any tool calls
        """
        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
            response = llm_with_tools.invoke(messages)
        else:
            response = self.llm.invoke(messages)
            
        return {
            'content': response.content,
            'tool_calls': getattr(response, 'tool_calls', []),
        }

