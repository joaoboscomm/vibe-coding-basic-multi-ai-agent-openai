"""
Custom middleware for request logging and tracing.
"""
import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware:
    """
    Middleware that adds a correlation ID to each request for tracing.
    The correlation ID is either extracted from the request header or generated.
    """
    CORRELATION_ID_HEADER = 'X-Correlation-ID'

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            self.CORRELATION_ID_HEADER,
            str(uuid.uuid4())
        )

        # Attach to request for use in views and other middleware
        request.correlation_id = correlation_id

        # Process request
        response = self.get_response(request)

        # Add correlation ID to response headers
        response[self.CORRELATION_ID_HEADER] = correlation_id

        return response


class RequestLoggingMiddleware:
    """
    Middleware that logs request and response information with timing metrics.
    """

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Start timing
        start_time = time.time()

        # Get correlation ID
        correlation_id = getattr(request, 'correlation_id', 'unknown')

        # Log request
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'method': request.method,
                    'path': request.path,
                    'query_params': dict(request.GET),
                    'user_agent': request.headers.get('User-Agent', ''),
                    'remote_addr': self._get_client_ip(request),
                }
            }
        )

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log response
        log_method = logger.info if response.status_code < 400 else logger.warning
        log_method(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration_ms, 2),
                }
            }
        )

        return response

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP from request headers."""
        x_forwarded_for = request.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


class AgentTracingMiddleware:
    """
    Middleware for tracing agent execution.
    This is called programmatically rather than through HTTP middleware.
    """
    
    @staticmethod
    def trace_agent_call(
        agent_type: str,
        conversation_id: str,
        correlation_id: str,
        input_message: str,
    ):
        """Log the start of an agent execution."""
        logger.info(
            f"Agent execution started: {agent_type}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'agent_type': agent_type,
                    'conversation_id': conversation_id,
                    'input_length': len(input_message),
                }
            }
        )

    @staticmethod
    def trace_agent_result(
        agent_type: str,
        conversation_id: str,
        correlation_id: str,
        output_message: str,
        duration_ms: float,
        success: bool,
        tools_used: list[str] = None,
    ):
        """Log the completion of an agent execution."""
        log_method = logger.info if success else logger.error
        log_method(
            f"Agent execution completed: {agent_type}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'agent_type': agent_type,
                    'conversation_id': conversation_id,
                    'output_length': len(output_message),
                    'duration_ms': round(duration_ms, 2),
                    'success': success,
                    'tools_used': tools_used or [],
                }
            }
        )

    @staticmethod
    def trace_tool_call(
        tool_name: str,
        agent_type: str,
        correlation_id: str,
        input_data: dict,
    ):
        """Log a tool invocation."""
        logger.debug(
            f"Tool called: {tool_name} by {agent_type}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'tool_name': tool_name,
                    'agent_type': agent_type,
                    'input_keys': list(input_data.keys()),
                }
            }
        )

    @staticmethod
    def trace_tool_result(
        tool_name: str,
        correlation_id: str,
        duration_ms: float,
        success: bool,
    ):
        """Log a tool execution result."""
        log_method = logger.debug if success else logger.warning
        log_method(
            f"Tool completed: {tool_name}",
            extra={
                'correlation_id': correlation_id,
                'extra_data': {
                    'tool_name': tool_name,
                    'duration_ms': round(duration_ms, 2),
                    'success': success,
                }
            }
        )

